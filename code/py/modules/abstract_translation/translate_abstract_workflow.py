"""
Abstract Translation ワークフロー

論文のAbstract部分を日本語に翻訳し、YAMLヘッダーに統合する機能
"""

import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from modules.ai_tagging.claude_api_client import ClaudeAPIClient  # 共通APIクライアント使用
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError
from modules.shared.utils import read_yaml_header, update_yaml_header


class TranslateAbstractWorkflow:
    """AI要約翻訳ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        TranslateAbstractWorkflow の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('TranslateAbstractWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
        # 翻訳設定の取得
        self.config = config_manager.get_config_value("ai_generation.translate_abstract", {})
        self.batch_size = self.config.get("batch_size", 3)
        self.parallel_processing = self.config.get("parallel_processing", True)
        
        self.logger.info("TranslateAbstractWorkflow initialized successfully")
    
    def process_papers(self, clippings_dir: str, target_papers: Optional[List[str]] = None,
                      batch_size: Optional[int] = None, parallel: Optional[bool] = None) -> Dict[str, Any]:
        """
        論文の一括要約翻訳処理
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（Noneで全論文）
            batch_size: バッチサイズ（Noneでデフォルト）
            parallel: 並列処理フラグ（Noneでデフォルト）
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Starting abstract translation for papers in {clippings_dir}")
            
            # 設定のオーバーライド
            if batch_size is not None:
                self.batch_size = batch_size
            if parallel is not None:
                self.parallel_processing = parallel
            
            # 対象論文の決定
            paper_files = self._get_target_papers(clippings_dir, target_papers)
            
            if not paper_files:
                return {
                    'success': True,
                    'processed_papers': 0,
                    'paper_results': [],
                    'message': 'No papers to process'
                }
            
            self.logger.info(f"Processing {len(paper_files)} papers for abstract translation")
            
            # バッチ処理実行
            if self.parallel_processing and len(paper_files) > 1:
                results = self._process_papers_parallel(paper_files)
            else:
                results = self._process_papers_sequential(paper_files)
            
            # 結果集計
            processed_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            skipped_count = len([r for r in results if r.get('skipped', False)])
            
            self.logger.info(f"Abstract translation completed: {processed_count} processed, {failed_count} failed, {skipped_count} skipped")
            
            return {
                'success': failed_count == 0,
                'processed_papers': processed_count,
                'failed_papers': failed_count,
                'skipped_papers': skipped_count,
                'paper_results': results
            }
            
        except Exception as e:
            self.logger.error(f"Abstract translation process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_papers': 0,
                'paper_results': []
            }
    
    def translate_abstract_single(self, paper_file: str) -> str:
        """
        単一論文の要約翻訳
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            日本語翻訳
        """
        try:
            # 論文内容の読み込み
            with open(paper_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Abstract部分の抽出
            abstract = self.extract_abstract(content)
            
            if not abstract:
                raise ObsClippingsError("No abstract found in paper")
            
            # Claude APIで翻訳
            translation = self.claude_client.translate_abstract_single(abstract)
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Abstract translation failed for {paper_file}: {e}")
            raise
    
    def extract_abstract(self, paper_content: str) -> str:
        """
        論文からabstract部分を抽出
        
        Args:
            paper_content: 論文の全内容
            
        Returns:
            抽出されたabstract内容
        """
        try:
            # YAMLヘッダー部分を除去
            lines = paper_content.split('\n')
            content_start = 0
            
            # YAML frontmatterをスキップ
            if lines and lines[0].strip() == '---':
                yaml_end = False
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == '---':
                        content_start = i + 1
                        yaml_end = True
                        break
                if not yaml_end:
                    content_start = 0
            
            # コンテンツ部分を結合
            content_lines = lines[content_start:]
            content = '\n'.join(content_lines)
            
            # Abstract セクションを検索
            abstract_patterns = [
                r'##\s*Abstract\s*\n(.*?)(?=\n##|\n#|\Z)',
                r'#\s*Abstract\s*\n(.*?)(?=\n##|\n#|\Z)',
                r'Abstract\s*\n(.*?)(?=\n##|\n#|\Z)',
                r'ABSTRACT\s*\n(.*?)(?=\n##|\n#|\Z)'
            ]
            
            for pattern in abstract_patterns:
                match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract = match.group(1).strip()
                    # 空行や余分な改行を削除
                    abstract = re.sub(r'\n\s*\n', '\n', abstract)
                    return abstract.strip()
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Failed to extract abstract: {e}")
            return ""
    
    def process_single_paper(self, paper_file: str) -> Dict[str, Any]:
        """
        単一論文の処理（翻訳 + YAMLヘッダー更新）
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Processing abstract translation for {paper_file}")
            
            # 既存翻訳の確認
            if self._has_existing_translation(paper_file):
                return {
                    'success': True,
                    'skipped': True,
                    'reason': 'Already translated',
                    'paper_file': paper_file
                }
            
            # 翻訳実行
            japanese_abstract = self.translate_abstract_single(paper_file)
            
            if not japanese_abstract:
                return {
                    'success': False,
                    'error': 'No translation generated',
                    'paper_file': paper_file
                }
            
            # 翻訳品質検証
            with open(paper_file, 'r', encoding='utf-8') as f:
                content = f.read()
            original_abstract = self.extract_abstract(content)
            
            if not self.validate_translation_quality(japanese_abstract, original_abstract):
                self.logger.warning(f"Translation quality validation failed for {paper_file}")
            
            # YAMLヘッダー更新
            self._update_paper_translation(paper_file, japanese_abstract)
            
            self.logger.info(f"Translated abstract for {os.path.basename(paper_file)}")
            
            return {
                'success': True,
                'japanese_abstract': japanese_abstract,
                'paper_file': paper_file
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process {paper_file}: {e}")
            return {
                'success': False,
                'error': str(e),
                'paper_file': paper_file
            }
    
    def validate_translation_quality(self, translation: str, original: str) -> bool:
        """
        翻訳品質の検証
        
        Args:
            translation: 日本語翻訳
            original: 元の英語abstract
            
        Returns:
            True if品質OK, False otherwise
        """
        try:
            # 基本的な品質チェック
            if not translation or len(translation.strip()) < 10:
                return False
            
            # 長さ比較（極端に短い翻訳を検出）
            if len(translation) < len(original) * 0.3:
                return False
            
            # 日本語文字の存在確認
            if not re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', translation):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _get_target_papers(self, clippings_dir: str, target_papers: Optional[List[str]]) -> List[str]:
        """
        対象論文ファイルのリストを取得
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト
            
        Returns:
            論文ファイルパスのリスト
        """
        paper_files = []
        
        if target_papers:
            # 指定された論文のみ
            for paper_key in target_papers:
                paper_dir = os.path.join(clippings_dir, paper_key)
                paper_file = os.path.join(paper_dir, f"{paper_key}.md")
                
                if os.path.exists(paper_file):
                    paper_files.append(paper_file)
                else:
                    self.logger.warning(f"Paper file not found: {paper_file}")
        else:
            # 全論文を対象
            for item in os.listdir(clippings_dir):
                item_path = os.path.join(clippings_dir, item)
                if os.path.isdir(item_path):
                    paper_file = os.path.join(item_path, f"{item}.md")
                    if os.path.exists(paper_file):
                        paper_files.append(paper_file)
        
        return paper_files
    
    def _process_papers_parallel(self, paper_files: List[str]) -> List[Dict[str, Any]]:
        """
        論文の並列処理
        
        Args:
            paper_files: 論文ファイルパスのリスト
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # 並列実行のためのfutureを作成
            future_to_file = {
                executor.submit(self.process_single_paper, paper_file): paper_file 
                for paper_file in paper_files
            }
            
            # 結果の収集
            for future in as_completed(future_to_file):
                paper_file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Parallel processing failed for {paper_file}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'paper_file': paper_file
                    })
        
        return results
    
    def _process_papers_sequential(self, paper_files: List[str]) -> List[Dict[str, Any]]:
        """
        論文の順次処理
        
        Args:
            paper_files: 論文ファイルパスのリスト
            
        Returns:
            処理結果のリスト
        """
        results = []
        
        for paper_file in paper_files:
            result = self.process_single_paper(paper_file)
            results.append(result)
        
        return results
    
    def _has_existing_translation(self, paper_file: str) -> bool:
        """
        論文に既存の翻訳があるかチェック
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            True if既存翻訳あり, False otherwise
        """
        try:
            yaml_header, _ = read_yaml_header(paper_file)
            abstract_japanese = yaml_header.get('abstract_japanese', '')
            return len(abstract_japanese.strip()) > 0
        except Exception:
            return False
    
    def _update_paper_translation(self, paper_file: str, japanese_abstract: str) -> None:
        """
        論文ファイルのYAMLヘッダーに翻訳を追加
        
        Args:
            paper_file: 論文ファイルパス
            japanese_abstract: 日本語翻訳
        """
        try:
            yaml_header, content = read_yaml_header(paper_file)
            
            # 翻訳を追加（YAML multiline string形式）
            yaml_header['abstract_japanese'] = japanese_abstract
            
            # YAMLヘッダーを更新
            update_yaml_header(paper_file, yaml_header, content)
            
            self.logger.debug(f"Updated YAML header with Japanese abstract for {paper_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_file}: {e}")
            raise 