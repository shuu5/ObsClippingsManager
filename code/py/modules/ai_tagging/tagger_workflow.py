"""
Tagger ワークフロー

論文内容からAIタグを生成し、YAMLヘッダーに統合する機能
"""

import os
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .claude_api_client import ClaudeAPIClient
from modules.shared.config_manager import ConfigManager
from modules.shared.logger import IntegratedLogger
from modules.shared.exceptions import ObsClippingsError
from modules.shared.utils import read_yaml_header, update_yaml_header


class TaggerWorkflow:
    """AI論文タグ生成ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        TaggerWorkflow の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ管理オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('TaggerWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
        # タグ生成設定の取得
        self.config = config_manager.get_config_value("ai_generation.tagger", {})
        self.batch_size = self.config.get("batch_size", 5)
        self.parallel_processing = self.config.get("parallel_processing", True)
        
        self.logger.info("TaggerWorkflow initialized successfully")
    
    def process_papers(self, clippings_dir: str, target_papers: Optional[List[str]] = None,
                      batch_size: Optional[int] = None, parallel: Optional[bool] = None) -> Dict[str, Any]:
        """
        論文の一括タグ生成処理
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（Noneで全論文）
            batch_size: バッチサイズ（Noneでデフォルト）
            parallel: 並列処理フラグ（Noneでデフォルト）
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Starting tag generation for papers in {clippings_dir}")
            
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
            
            self.logger.info(f"Processing {len(paper_files)} papers for tag generation")
            
            # バッチ処理実行
            if self.parallel_processing and len(paper_files) > 1:
                results = self._process_papers_parallel(paper_files)
            else:
                results = self._process_papers_sequential(paper_files)
            
            # 結果集計
            processed_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            
            self.logger.info(f"Tag generation completed: {processed_count} processed, {failed_count} failed")
            
            return {
                'success': failed_count == 0,
                'processed_papers': processed_count,
                'failed_papers': failed_count,
                'paper_results': results
            }
            
        except Exception as e:
            self.logger.error(f"Tag generation process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_papers': 0,
                'paper_results': []
            }
    
    def generate_tags_single(self, paper_file: str) -> List[str]:
        """
        単一論文のタグ生成
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            生成されたタグリスト
        """
        try:
            # 論文内容の読み込み
            with open(paper_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Claude APIでタグ生成
            tags = self.claude_client.generate_tags_single(content)
            
            return tags
            
        except Exception as e:
            self.logger.error(f"Tag generation failed for {paper_file}: {e}")
            raise
    
    def process_single_paper(self, paper_file: str) -> Dict[str, Any]:
        """
        単一論文の処理（タグ生成 + YAMLヘッダー更新）
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Processing tags for {paper_file}")
            
            # 既存タグの確認
            if self._has_existing_tags(paper_file):
                return {
                    'success': True,
                    'skipped': True,
                    'reason': 'Already has tags',
                    'paper_file': paper_file
                }
            
            # タグ生成
            tags = self.generate_tags_single(paper_file)
            
            if not tags:
                return {
                    'success': False,
                    'error': 'No tags generated',
                    'paper_file': paper_file
                }
            
            # YAMLヘッダー更新
            self._update_paper_tags(paper_file, tags)
            
            self.logger.info(f"Generated {len(tags)} tags for {os.path.basename(paper_file)}")
            
            return {
                'success': True,
                'tags': tags,
                'tag_count': len(tags),
                'paper_file': paper_file
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process {paper_file}: {e}")
            return {
                'success': False,
                'error': str(e),
                'paper_file': paper_file
            }
    
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
    
    def _has_existing_tags(self, paper_file: str) -> bool:
        """
        論文に既存のタグがあるかチェック
        
        Args:
            paper_file: 論文ファイルパス
            
        Returns:
            True if既存タグあり, False otherwise
        """
        try:
            yaml_header, _ = read_yaml_header(paper_file)
            tags = yaml_header.get('tags', [])
            return len(tags) > 0
        except Exception:
            return False
    
    def _update_paper_tags(self, paper_file: str, tags: List[str]) -> None:
        """
        論文ファイルのYAMLヘッダーにタグを追加
        
        Args:
            paper_file: 論文ファイルパス
            tags: 追加するタグリスト
        """
        try:
            yaml_header, content = read_yaml_header(paper_file)
            
            # タグを追加
            yaml_header['tags'] = tags
            
            # YAMLヘッダーを更新
            update_yaml_header(paper_file, yaml_header, content)
            
            self.logger.debug(f"Updated YAML header with {len(tags)} tags for {paper_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_file}: {e}")
            raise 