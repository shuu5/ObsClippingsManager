"""
落合フォーマット要約生成ワークフロー

学術論文の内容を6つの構造化された質問に答える形で要約し、
研究者向けのA4一枚程度の簡潔な論文理解を提供する機能。
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..shared.config_manager import ConfigManager
from ..shared.logger import IntegratedLogger
from ..shared.exceptions import ObsClippingsError
from ..shared.utils import read_yaml_header, update_yaml_header
from ..ai_tagging.claude_api_client import ClaudeAPIClient
from .data_structures import OchiaiFormat, create_ochiai_format_from_json_response


class OchiaiFormatWorkflow:
    """落合フォーマット要約生成ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('OchiaiFormatWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
        # 設定値の取得
        self.batch_size = config_manager.get('ochiai_format.batch_size', 3)
        self.parallel_processing = config_manager.get('ochiai_format.parallel_processing', True)
        self.retry_attempts = config_manager.get('ochiai_format.retry_attempts', 3)
        self.request_delay = config_manager.get('ochiai_format.request_delay', 1.0)
        self.max_content_length = config_manager.get('ochiai_format.max_content_length', 10000)
        self.enable_section_integration = config_manager.get('ochiai_format.enable_section_integration', True)
        self.model = config_manager.get('ochiai_format.model', 'claude-3-5-haiku-20241022')
        
        self.logger.info("OchiaiFormatWorkflow initialized successfully")
    
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None, 
                      batch_size: int = None, parallel: bool = None) -> Dict[str, Any]:
        """
        論文の一括落合フォーマット要約処理
        
        Args:
            clippings_dir: Clippingsディレクトリパス
            target_papers: 対象論文リスト（Noneで全論文）
            batch_size: バッチサイズ（Noneでデフォルト）
            parallel: 並列処理フラグ（Noneでデフォルト）
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Starting Ochiai format generation for papers in {clippings_dir}")
            
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
            
            self.logger.info(f"Processing {len(paper_files)} papers for Ochiai format generation")
            
            # バッチ処理実行
            if self.parallel_processing and len(paper_files) > 1:
                results = self._process_papers_parallel(paper_files)
            else:
                results = self._process_papers_sequential(paper_files)
            
            # 結果集計
            processed_count = len([r for r in results if r['success']])
            failed_count = len([r for r in results if not r['success']])
            
            self.logger.info(f"Ochiai format generation completed: {processed_count} processed, {failed_count} failed")
            
            return {
                'success': failed_count == 0,
                'processed_papers': processed_count,
                'failed_papers': failed_count,
                'paper_results': results,
                'statistics': {
                    'total_papers': len(paper_files),
                    'successful': processed_count,
                    'failed': failed_count
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ochiai format generation process failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processed_papers': 0,
                'paper_results': []
            }
    
    def generate_ochiai_summary_single(self, paper_path: str) -> OchiaiFormat:
        """
        単一論文の落合フォーマット要約生成
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            生成された落合フォーマット要約
        """
        try:
            self.logger.info(f"Generating Ochiai format summary for {paper_path}")
            
            # 論文内容の抽出
            paper_content = self.extract_paper_content(paper_path)
            
            # プロンプトの作成
            if self.enable_section_integration and self._has_section_structure(paper_path):
                prompt = self._create_section_based_prompt(paper_content)
            else:
                prompt = self._create_basic_prompt(paper_content)
            
            # Claude APIでの要約生成
            response = self._generate_summary_with_claude(prompt)
            
            # JSON レスポンスの解析
            ochiai_format = self._parse_claude_response(response)
            
            # 品質検証
            if not self.validate_ochiai_format(ochiai_format):
                self.logger.warning(f"Generated summary quality validation failed for {paper_path}")
            
            self.logger.info(f"Ochiai format summary generated successfully for {os.path.basename(paper_path)}")
            return ochiai_format
            
        except Exception as e:
            self.logger.error(f"Failed to generate Ochiai format summary for {paper_path}: {e}")
            raise ObsClippingsError(f"Failed to generate Ochiai format summary: {e}")
    
    def extract_paper_content(self, paper_path: str) -> Dict[str, str]:
        """
        論文内容の抽出（セクション分割機能と連携可能）
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            論文内容辞書
        """
        try:
            yaml_header, markdown_body = read_yaml_header(paper_path)
            
            # 基本論文情報の抽出
            paper_content = {
                'title': yaml_header.get('title', 'Unknown Title'),
                'authors': yaml_header.get('author', 'Unknown Authors'),
                'journal': yaml_header.get('journal', 'Unknown Journal'),
                'year': yaml_header.get('year', 'Unknown Year'),
                'full_content': markdown_body
            }
            
            # セクション分割機能との連携
            if self.enable_section_integration and 'paper_structure' in yaml_header:
                section_content = self._extract_section_content(yaml_header['paper_structure'], markdown_body)
                paper_content.update(section_content)
            
            # 内容長制限の適用
            paper_content = self._apply_content_length_limit(paper_content)
            
            return paper_content
            
        except Exception as e:
            self.logger.error(f"Failed to extract paper content from {paper_path}: {e}")
            raise ObsClippingsError(f"Failed to extract paper content: {e}")
    
    def update_yaml_with_ochiai(self, paper_path: str, ochiai: OchiaiFormat) -> bool:
        """
        YAMLヘッダーに落合フォーマットを記録
        
        Args:
            paper_path: 論文ファイルパス
            ochiai: 落合フォーマット要約
            
        Returns:
            更新成功フラグ
        """
        try:
            # YAMLヘッダーの抽出と更新
            yaml_header, markdown_body = read_yaml_header(paper_path)
            
            # 落合フォーマット要約をYAML形式に変換
            yaml_header['ochiai_format'] = ochiai.to_dict()
            
            # 処理状態を更新
            if 'processing_status' not in yaml_header:
                yaml_header['processing_status'] = {}
            yaml_header['processing_status']['ochiai_format'] = 'completed'
            
            # ワークフローバージョンを記録
            yaml_header['workflow_version'] = '3.2'
            
            # ファイルに書き戻し
            update_yaml_header(paper_path, yaml_header, markdown_body)
            
            self.logger.info(f"Updated YAML header with Ochiai format for {paper_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_path}: {e}")
            return False
    
    def validate_ochiai_format(self, ochiai: OchiaiFormat) -> bool:
        """
        生成された要約の品質検証
        
        Args:
            ochiai: 落合フォーマット要約
            
        Returns:
            品質検証結果
        """
        return ochiai.is_valid()
    
    def process_single_paper(self, paper_path: str) -> Dict[str, Any]:
        """
        単一論文の処理
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            処理結果辞書
        """
        try:
            self.logger.info(f"Processing Ochiai format for {paper_path}")
            
            # 既に処理済みかチェック
            if self._is_already_processed(paper_path):
                self.logger.info(f"Ochiai format already completed for {paper_path}")
                return {
                    'success': True,
                    'paper_path': paper_path,
                    'skipped': True,
                    'reason': 'already_processed'
                }
            
            # 要約生成
            ochiai_format = self.generate_ochiai_summary_single(paper_path)
            
            # YAML更新
            success = self.update_yaml_with_ochiai(paper_path, ochiai_format)
            
            if success:
                stats = ochiai_format.get_summary_statistics()
                self.logger.info(f"Ochiai format completed for {os.path.basename(paper_path)}")
                return {
                    'success': True,
                    'paper_path': paper_path,
                    'summary_statistics': stats,
                    'valid': ochiai_format.is_valid()
                }
            else:
                return {
                    'success': False,
                    'paper_path': paper_path,
                    'error': 'Failed to update YAML header'
                }
                
        except Exception as e:
            self.logger.error(f"Ochiai format generation failed for {paper_path}: {e}")
            return {
                'success': False,
                'paper_path': paper_path,
                'error': str(e)
            }
    
    def _has_section_structure(self, paper_path: str) -> bool:
        """
        論文がセクション構造情報を持っているかチェック
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            セクション構造の有無
        """
        try:
            yaml_header, _ = read_yaml_header(paper_path)
            return 'paper_structure' in yaml_header
            
        except Exception:
            return False
    
    def _extract_section_content(self, paper_structure: Dict[str, Any], markdown_body: str) -> Dict[str, str]:
        """
        セクション構造からコンテンツを抽出
        
        Args:
            paper_structure: セクション構造情報
            markdown_body: Markdown本文
            
        Returns:
            セクション別コンテンツ辞書
        """
        lines = markdown_body.split('\n')
        section_content = {}
        
        sections = paper_structure.get('sections', [])
        
        for section in sections:
            section_type = section.get('section_type', 'unknown')
            start_line = section.get('start_line', 1) - 1  # 0-indexed
            end_line = section.get('end_line', len(lines))
            
            if section_type in ['abstract', 'introduction', 'methods', 'results', 'discussion']:
                content = '\n'.join(lines[start_line:end_line]).strip()
                section_content[f"{section_type}_content"] = content
        
        # 参考文献リストの抽出（セクション構造から）
        references_section = next(
            (s for s in sections if s.get('section_type') == 'references'), 
            None
        )
        if references_section:
            start_line = references_section.get('start_line', 1) - 1
            end_line = references_section.get('end_line', len(lines))
            references_content = '\n'.join(lines[start_line:end_line]).strip()
            section_content['references_list'] = references_content
        
        return section_content
    
    def _apply_content_length_limit(self, paper_content: Dict[str, str]) -> Dict[str, str]:
        """
        内容長制限の適用
        
        Args:
            paper_content: 論文内容辞書
            
        Returns:
            制限適用後の論文内容辞書
        """
        limited_content = paper_content.copy()
        
        # 全体内容の制限
        if 'full_content' in limited_content:
            content = limited_content['full_content']
            if len(content) > self.max_content_length:
                limited_content['full_content'] = content[:self.max_content_length] + "..."
                self.logger.warning(f"Content truncated to {self.max_content_length} characters")
        
        # セクション別内容の制限（それぞれ最大2000文字）
        section_keys = ['abstract_content', 'introduction_content', 'methods_content', 
                       'results_content', 'discussion_content', 'references_list']
        
        for key in section_keys:
            if key in limited_content:
                content = limited_content[key]
                if len(content) > 2000:
                    limited_content[key] = content[:2000] + "..."
        
        return limited_content
    
    def _create_section_based_prompt(self, paper_content: Dict[str, str]) -> str:
        """
        セクション分割機能連携版プロンプトの作成
        
        Args:
            paper_content: 論文内容辞書
            
        Returns:
            プロンプト文字列
        """
        prompt = f"""以下の学術論文の各セクション内容を、落合フォーマットの6つの質問に答える形で要約してください。

【論文情報】
タイトル: {paper_content.get('title', 'Unknown')}
著者: {paper_content.get('authors', 'Unknown')}
ジャーナル: {paper_content.get('journal', 'Unknown')}

【セクション別内容】
Abstract: {paper_content.get('abstract_content', '情報なし')}
Introduction: {paper_content.get('introduction_content', '情報なし')}
Methods: {paper_content.get('methods_content', '情報なし')}
Results: {paper_content.get('results_content', '情報なし')}
Discussion: {paper_content.get('discussion_content', '情報なし')}
References: {paper_content.get('references_list', '情報なし')}

【要約ルール】
1. 各項目3-5文程度で簡潔に
2. 具体的で実用的な内容
3. 学術的で自然な日本語
4. 「次に読むべき論文」は参考文献から3本選出

JSON形式で回答してください：
{{
  "what_is_this": "...",
  "what_is_superior": "...",
  "technical_key": "...",
  "validation_method": "...",
  "discussion_points": "...",
  "next_papers": "..."
}}"""
        
        return prompt
    
    def _create_basic_prompt(self, paper_content: Dict[str, str]) -> str:
        """
        基本プロンプトの作成
        
        Args:
            paper_content: 論文内容辞書
            
        Returns:
            プロンプト文字列
        """
        prompt = f"""以下の学術論文の内容を、落合フォーマットの6つの質問に答える形で要約してください。

【論文情報】
タイトル: {paper_content.get('title', 'Unknown')}
著者: {paper_content.get('authors', 'Unknown')}
ジャーナル: {paper_content.get('journal', 'Unknown')}

【論文内容】
{paper_content.get('full_content', '内容なし')}

【要約ルール】
1. 各項目3-5文程度で簡潔に
2. 具体的で実用的な内容
3. 学術的で自然な日本語
4. 「次に読むべき論文」は参考文献から3本選出

【落合フォーマット6項目】
1. どんなもの？
2. 先行研究と比べてどこがすごい？
3. 技術や手法のキモはどこ？
4. どうやって有効だと検証した？
5. 議論はある？
6. 次に読むべき論文は？

JSON形式で回答してください：
{{
  "what_is_this": "...",
  "what_is_superior": "...",
  "technical_key": "...",
  "validation_method": "...",
  "discussion_points": "...",
  "next_papers": "..."
}}"""
        
        return prompt
    
    def _generate_summary_with_claude(self, prompt: str) -> str:
        """
        Claude APIで要約生成
        
        Args:
            prompt: プロンプト文字列
            
        Returns:
            Claude APIの応答
        """
        try:
            response = self.claude_client.generate_summary(prompt, model=self.model)
            return response
            
        except Exception as e:
            self.logger.error(f"Claude API call failed: {e}")
            raise ObsClippingsError(f"Claude API call failed: {e}")
    
    def _parse_claude_response(self, response: str) -> OchiaiFormat:
        """
        Claude応答の解析
        
        Args:
            response: Claude API応答
            
        Returns:
            OchiaiFormatインスタンス
        """
        try:
            # JSONの抽出（コードブロックに囲まれている可能性がある）
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 直接JSONの場合
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            # JSON解析
            json_data = json.loads(json_str)
            
            # OchiaiFormat作成
            ochiai_format = create_ochiai_format_from_json_response(json_data)
            
            return ochiai_format
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse Claude response: {e}")
            self.logger.debug(f"Response content: {response}")
            raise ObsClippingsError(f"Failed to parse Claude response: {e}")
    
    def _is_already_processed(self, paper_path: str) -> bool:
        """
        落合フォーマット要約が既に生成済みかチェック
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            処理済みフラグ
        """
        try:
            yaml_header, _ = read_yaml_header(paper_path)
            
            processing_status = yaml_header.get('processing_status', {})
            return processing_status.get('ochiai_format') == 'completed'
            
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


def display_ochiai_format(paper_path: str) -> Optional[str]:
    """
    落合フォーマット要約の表示用ユーティリティ関数
    
    Args:
        paper_path: 論文ファイルパス
        
    Returns:
        フォーマット済み要約文字列または None
    """
    try:
        yaml_header, _ = read_yaml_header(paper_path)
        
        ochiai_data = yaml_header.get('ochiai_format', {})
        if not ochiai_data:
            return None
        
        ochiai = OchiaiFormat.from_dict(ochiai_data)
        return ochiai.format_for_display()
        
    except Exception:
        return None 