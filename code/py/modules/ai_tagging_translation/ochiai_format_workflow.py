"""
OchiaiFormatWorkflow - 落合フォーマット6項目要約生成

Claude 3.5 Haiku APIを使用して学術論文の落合フォーマット要約を自動生成します。

落合フォーマット6項目:
1. どんなもの？
2. 先行研究と比べてどこがすごい？
3. 技術や手法のキモはどこ？
4. どうやって有効だと検証した？
5. 議論はある？
6. 次に読むべき論文は？
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ..shared_modules.exceptions import ProcessingError, APIError
from ..status_management_yaml.status_manager import StatusManager
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor
from .claude_api_client import ClaudeAPIClient


class OchiaiFormatWorkflow:
    """落合フォーマット要約生成ワークフロー"""
    
    def __init__(self, config_manager, logger):
        """
        初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('OchiaiFormatWorkflow')
        self.claude_client = ClaudeAPIClient(config_manager, logger)
        
        # 設定値の取得
        ochiai_config = config_manager.config.get('ochiai_format', {})
        self.batch_size = ochiai_config.get('batch_size', 3)
        self.request_delay = ochiai_config.get('request_delay', 1.0)
        self.max_content_length = ochiai_config.get('max_content_length', 10000)
        
        self.logger.info(f"OchiaiFormatWorkflow initialized with batch_size={self.batch_size}")
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None) -> Dict[str, int]:
        """
        論文の一括落合フォーマット要約処理
        
        Args:
            input_dir: 処理対象ディレクトリ
            target_items: 処理対象ファイルリスト（Noneの場合は全ファイル）
            
        Returns:
            Dict[str, int]: 処理結果統計（processed, skipped, failed）
        """
        self.logger.info(f"Starting Ochiai format processing for directory: {input_dir}")
        
        # IntegratedLoggerインスタンスを取得
        integrated_logger = self.logger.parent if hasattr(self.logger, 'parent') else self.logger
        # IntegratedLoggerの適切なインスタンスを取得するための調整
        from ..shared_modules.integrated_logger import IntegratedLogger
        if not hasattr(integrated_logger, 'get_logger'):
            # IntegratedLoggerでない場合は新しく作成
            integrated_logger = IntegratedLogger(self.config_manager)
        
        status_manager = StatusManager(self.config_manager, integrated_logger)
        papers_needing_processing = status_manager.get_papers_needing_processing(
            input_dir, 'ochiai_format', target_items
        )
        
        processed = 0
        skipped = 0
        failed = 0
        
        if not papers_needing_processing:
            self.logger.info("No papers need Ochiai format processing")
            return {'processed': 0, 'skipped': 0, 'failed': 0}
        
        self.logger.info(f"Found {len(papers_needing_processing)} papers needing Ochiai format processing")
        
        # バッチサイズごとに処理
        for i in range(0, len(papers_needing_processing), self.batch_size):
            batch = papers_needing_processing[i:i + self.batch_size]
            self.logger.info(f"Processing batch {i//self.batch_size + 1}: {len(batch)} papers")
            
            for paper_path in batch:
                try:
                    self.logger.info(f"Generating Ochiai format for: {paper_path}")
                    ochiai_summary = self.generate_ochiai_summary_single(paper_path)
                    self.update_yaml_with_ochiai(paper_path, ochiai_summary)
                    
                    processed += 1
                    self.logger.info(f"Successfully generated Ochiai format for: {paper_path}")
                    
                    # ステータス更新をtry-catchで分離
                    try:
                        status_manager.update_status(input_dir, paper_path, 'ochiai_format', 'completed')
                    except Exception as status_error:
                        self.logger.warning(f"Failed to update status for {paper_path}: {status_error}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to generate Ochiai format for {paper_path}: {e}")
                    failed += 1
                    
                    # ステータス更新をtry-catchで分離
                    try:
                        status_manager.update_status(input_dir, paper_path, 'ochiai_format', 'failed')
                    except Exception as status_error:
                        self.logger.warning(f"Failed to update failed status for {paper_path}: {status_error}")
                
                # API制限対応のための遅延
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
        
        self.logger.info(f"Ochiai format processing completed: {processed} processed, {skipped} skipped, {failed} failed")
        return {'processed': processed, 'skipped': skipped, 'failed': failed}
    
    def generate_ochiai_summary_single(self, paper_path: str) -> Dict[str, Any]:
        """
        単一論文の落合フォーマット要約生成
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            Dict[str, Any]: 落合フォーマット要約データ
        """
        try:
            # 論文内容の抽出
            paper_content = self.extract_paper_content(paper_path)
            
            # コンテンツサイズチェック
            content_str = '\n'.join(paper_content) if isinstance(paper_content, list) else str(paper_content)
            if len(content_str) > self.max_content_length:
                content_str = content_str[:self.max_content_length] + "..."
                self.logger.warning(f"Content truncated to {self.max_content_length} characters for {paper_path}")
            
            # プロンプト構築
            prompt = self._build_ochiai_prompt(content_str)
            
            # Claude API呼び出し
            response = self.claude_client.send_request(prompt)
            
            # 応答解析
            ochiai_data = self._parse_ochiai_response(response)
            
            return ochiai_data
            
        except Exception as e:
            self.logger.error(f"Error generating Ochiai summary for {paper_path}: {e}")
            raise ProcessingError(f"Failed to generate Ochiai summary: {e}") from e
    
    def extract_paper_content(self, paper_path: str) -> Union[List[str], str]:
        """
        論文内容の抽出
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            Union[List[str], str]: 抽出された論文内容
        """
        yaml_header, content = self._load_paper_with_yaml(paper_path)
        
        # paper_structure が存在する場合は重要セクションを抽出
        if 'paper_structure' in yaml_header:
            return self._extract_important_sections(yaml_header, content)
        else:
            # セクション分割されていない場合は全文を使用
            return content
    
    def _load_paper_with_yaml(self, paper_path: str) -> tuple:
        """
        YAMLヘッダー付き論文ファイルの読み込み
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            tuple: (yaml_header, content)
        """
        try:
            # IntegratedLoggerインスタンスを取得
            integrated_logger = self.logger.parent if hasattr(self.logger, 'parent') else self.logger
            from ..shared_modules.integrated_logger import IntegratedLogger
            if not hasattr(integrated_logger, 'get_logger'):
                integrated_logger = IntegratedLogger(self.config_manager)
            
            yaml_processor = YAMLHeaderProcessor(self.config_manager, integrated_logger)
            yaml_content, _ = yaml_processor.parse_yaml_header(Path(paper_path))
            
            with open(paper_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # YAMLヘッダー除去
            content_lines = []
            in_yaml = False
            yaml_count = 0
            
            for line in lines:
                if line.strip() == '---':
                    yaml_count += 1
                    in_yaml = (yaml_count == 1)
                    continue
                
                if not in_yaml and yaml_count >= 2:
                    content_lines.append(line.rstrip())
            
            return yaml_content, content_lines
            
        except Exception as e:
            self.logger.error(f"Error loading paper {paper_path}: {e}")
            raise ProcessingError(f"Failed to load paper: {e}") from e
    
    def _extract_important_sections(self, yaml_header: Dict, content: List[str]) -> str:
        """
        重要セクションの抽出（paper_structure活用）
        
        Args:
            yaml_header: YAMLヘッダー情報
            content: 論文本文
            
        Returns:
            str: 抽出された重要セクション
        """
        paper_structure = yaml_header.get('paper_structure', {})
        sections = paper_structure.get('sections', [])
        
        important_sections = []
        
        # タイトル追加
        title = yaml_header.get('title', '')
        if title:
            if isinstance(title, list):
                title = ' - '.join(title)
            important_sections.append(f"# {title}")
        
        # 重要セクションの種類
        important_types = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']
        
        for section in sections:
            section_type = section.get('section_type', '').lower()
            if section_type in important_types:
                start_line = section.get('start_line', 0)
                end_line = section.get('end_line', len(content))
                
                # 相対行数から実際の行数に変換（1ベース）
                if start_line > 0 and end_line > start_line and end_line <= len(content):
                    section_content = content[start_line-1:end_line]
                    important_sections.extend(section_content)
        
        return '\n'.join(important_sections) if important_sections else '\n'.join(content)
    
    def _build_ochiai_prompt(self, paper_content: str) -> str:
        """
        落合フォーマット用プロンプト構築
        
        Args:
            paper_content: 論文内容
            
        Returns:
            str: 構築されたプロンプト
        """
        prompt = f"""以下の学術論文について、落合フォーマットの6項目で要約してください。
各項目は簡潔で分かりやすく、専門用語は適切に説明してください。
回答は以下のJSON形式で出力してください。

{{
    "what_is_this": "どんなもの？（この研究の内容を簡潔に説明）",
    "what_is_superior": "先行研究と比べてどこがすごい？（従来手法との違いや優位性）",
    "technical_key": "技術や手法のキモはどこ？（核心的な技術や方法論）",
    "validation_method": "どうやって有効だと検証した？（評価方法や実験設計）",
    "discussion_points": "議論はある？（限界や課題、今後の展望）",
    "next_papers": "次に読むべき論文は？（関連する重要な文献や発展研究）"
}}

論文内容:
{paper_content}

上記の論文について、落合フォーマットの6項目で日本語で要約してください："""
        
        return prompt
    
    def _parse_ochiai_response(self, response: str) -> Dict[str, Any]:
        """
        Claude APIの応答を解析
        
        Args:
            response: Claude APIからの応答
            
        Returns:
            Dict[str, Any]: 解析された落合フォーマットデータ
        """
        try:
            # JSON部分の抽出を試行
            response_clean = response.strip()
            
            # JSONブロックの検出
            if '```json' in response_clean:
                start_idx = response_clean.find('```json') + 7
                end_idx = response_clean.find('```', start_idx)
                if end_idx != -1:
                    response_clean = response_clean[start_idx:end_idx].strip()
            elif '{' in response_clean and '}' in response_clean:
                start_idx = response_clean.find('{')
                end_idx = response_clean.rfind('}') + 1
                response_clean = response_clean[start_idx:end_idx]
            
            # JSON解析
            parsed_data = json.loads(response_clean)
            
            # 必須フィールドの確認と補完
            required_fields = [
                'what_is_this', 'what_is_superior', 'technical_key',
                'validation_method', 'discussion_points', 'next_papers'
            ]
            
            for field in required_fields:
                if field not in parsed_data or not parsed_data[field]:
                    parsed_data[field] = f"解析エラー: {field}の情報を抽出できませんでした"
            
            # 生成時刻の追加
            parsed_data['generated_at'] = datetime.now().isoformat()
            
            return parsed_data
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            return self._create_fallback_ochiai_data(response)
        except Exception as e:
            self.logger.error(f"Error parsing Ochiai response: {e}")
            return self._create_fallback_ochiai_data(response)
    
    def _create_fallback_ochiai_data(self, response: str) -> Dict[str, Any]:
        """
        フォールバック用の落合フォーマットデータ作成（仕様書順序）
        
        Args:
            response: 元の応答
            
        Returns:
            Dict[str, Any]: フォールバック落合フォーマットデータ
        """
        from collections import OrderedDict
        return OrderedDict([
            ('what_is_this', f"解析エラー: JSON形式での応答を解析できませんでした。元の応答: {response[:200]}..."),
            ('what_is_superior', "解析エラー: 先行研究との比較情報を抽出できませんでした"),
            ('technical_key', "解析エラー: 技術的要素を抽出できませんでした"),
            ('validation_method', "解析エラー: 検証方法を抽出できませんでした"),
            ('discussion_points', "解析エラー: 議論点を抽出できませんでした"),
            ('next_papers', "解析エラー: 関連論文を抽出できませんでした"),
            ('generated_at', datetime.now().isoformat())
        ])
    
    def update_yaml_with_ochiai(self, paper_path: str, ochiai_data: Dict[str, Any]) -> None:
        """
        YAMLヘッダーに落合フォーマット要約を統合
        
        Args:
            paper_path: 論文ファイルパス
            ochiai_data: 落合フォーマットデータ
        """
        try:
            # IntegratedLoggerインスタンスを取得
            integrated_logger = self.logger.parent if hasattr(self.logger, 'parent') else self.logger
            from ..shared_modules.integrated_logger import IntegratedLogger
            if not hasattr(integrated_logger, 'get_logger'):
                integrated_logger = IntegratedLogger(self.config_manager)
            
            yaml_processor = YAMLHeaderProcessor(self.config_manager, integrated_logger)
            
            # 現在のYAMLヘッダーとMarkdownコンテンツを取得
            current_yaml, markdown_content = yaml_processor.parse_yaml_header(Path(paper_path))
            
            # ai_content.ochiai_format セクション更新（仕様書順序に従って）
            from collections import OrderedDict
            ochiai_section = {
                'generated_at': ochiai_data['generated_at'],
                'questions': OrderedDict([
                    ('what_is_this', ochiai_data['what_is_this']),
                    ('what_is_superior', ochiai_data['what_is_superior']),
                    ('technical_key', ochiai_data['technical_key']),
                    ('validation_method', ochiai_data['validation_method']),
                    ('discussion_points', ochiai_data['discussion_points']),
                    ('next_papers', ochiai_data['next_papers'])
                ])
            }
            
            # ai_contentセクションが存在しない場合は作成
            if 'ai_content' not in current_yaml:
                current_yaml['ai_content'] = {}
            
            # ochiai_formatセクションを更新
            current_yaml['ai_content']['ochiai_format'] = ochiai_section
            
            # YAMLヘッダーを書き込み
            yaml_processor.write_yaml_header(Path(paper_path), current_yaml, markdown_content)
            
            self.logger.info(f"Updated YAML header with Ochiai format for: {paper_path}")
            
        except Exception as e:
            self.logger.error(f"Error updating YAML with Ochiai data for {paper_path}: {e}")
            raise ProcessingError(f"Failed to update YAML header: {e}") from e