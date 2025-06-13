#!/usr/bin/env python3
"""
YAMLHeaderProcessor

YAMLヘッダーの読み書き、検証、修復機能を提供するクラス。
状態管理システムの基盤となるYAMLフロントマター処理を担当。
"""

import yaml
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

from ..shared.config_manager import ConfigManager
from ..shared.integrated_logger import IntegratedLogger
from ..shared.exceptions import (
    YAMLError, ValidationError, FileSystemError, ProcessingError
)
from ..shared.file_utils import FileUtils, BackupManager, StringUtils


class YAMLHeaderProcessor:
    """
    YAMLヘッダー処理クラス
    
    Markdownファイル内のYAMLフロントマターの処理を担当。
    読み書き、検証、修復、一括処理機能を提供。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        YAMLHeaderProcessorの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('YAMLHeaderProcessor')
        self.file_utils = FileUtils(config_manager)
        self.backup_manager = BackupManager()
        self.string_utils = StringUtils()
        
        # 必須フィールドの定義
        self.required_fields = {
            'citation_key', 'workflow_version', 'last_updated', 
            'created_at', 'processing_status', 'tags'
        }
        
        # 有効な処理状態値
        self.valid_status_values = {'pending', 'completed', 'failed'}
        
        self.logger.info("YAMLHeaderProcessor initialized")
    
    def parse_yaml_header(self, file_path: Path) -> Tuple[Dict[str, Any], str]:
        """
        MarkdownファイルからYAMLヘッダーとコンテンツを分離して読み込み
        
        Args:
            file_path: 対象ファイルのパス
            
        Returns:
            Tuple[Dict[str, Any], str]: YAMLヘッダー辞書とコンテンツ文字列
            
        Raises:
            FileSystemError: ファイルが存在しない場合
            YAMLError: YAML解析エラーの場合
        """
        try:
            if not file_path.exists():
                raise FileSystemError(
                    f"File not found: {file_path}",
                    error_code="FILE_NOT_FOUND"
                )
            
            # ファイル内容を読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLヘッダーの抽出
            yaml_header, markdown_content = self._extract_yaml_and_content(content)
            
            self.logger.debug(f"Parsed YAML header from {file_path.name}")
            return yaml_header, markdown_content
            
        except YAMLError:
            # 既に適切なYAMLErrorが発生している場合はそのまま再発生
            raise
        except yaml.YAMLError as e:
            raise YAMLError(
                f"YAML parsing error in {file_path.name}: {e}",
                error_code="YAML_PARSE_ERROR",
                context={"file": str(file_path)}
            )
        except Exception as e:
            raise FileSystemError(
                f"Failed to read file {file_path}: {e}",
                error_code="FILE_READ_ERROR",
                context={"file": str(file_path)}
            )
    
    def write_yaml_header(self, file_path: Path, yaml_header: Dict[str, Any], content: str) -> None:
        """
        YAMLヘッダーとコンテンツをMarkdownファイルに書き込み
        
        Args:
            file_path: 書き込み先ファイルのパス
            yaml_header: YAMLヘッダー辞書
            content: Markdownコンテンツ
            
        Raises:
            YAMLError: YAML書き込みエラーの場合
            FileSystemError: ファイル書き込みエラーの場合
        """
        try:
            # YAMLヘッダーの文字列化
            yaml_str = yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True)
            
            # ファイル内容の構築
            full_content = f"---\n{yaml_str}---\n\n{content}"
            
            # アトミック書き込み
            self.file_utils.atomic_write(file_path, full_content)
            
            self.logger.debug(f"Written YAML header to {file_path.name}")
            
        except Exception as e:
            raise YAMLError(
                f"Failed to write YAML header to {file_path}: {e}",
                error_code="YAML_WRITE_ERROR",
                context={"file": str(file_path)}
            )
    
    def validate_yaml_structure(self, yaml_header: Dict[str, Any]) -> bool:
        """
        YAMLヘッダーの構造を検証
        
        Args:
            yaml_header: 検証対象のYAMLヘッダー
            
        Returns:
            bool: 検証成功の場合True
            
        Raises:
            ValidationError: 検証失敗の場合
        """
        errors = []
        
        # 必須フィールドの確認
        missing_fields = self.required_fields - set(yaml_header.keys())
        if missing_fields:
            errors.append(f"Missing required fields: {missing_fields}")
        
        # processing_statusの検証
        if 'processing_status' in yaml_header:
            processing_status = yaml_header['processing_status']
            if not isinstance(processing_status, dict):
                errors.append("processing_status must be a dictionary")
            else:
                for step, status in processing_status.items():
                    if status not in self.valid_status_values:
                        errors.append(
                            f"Invalid status '{status}' for step '{step}'. "
                            f"Valid values: {self.valid_status_values}"
                        )
        
        # タグの検証
        if 'tags' in yaml_header and not isinstance(yaml_header['tags'], list):
            errors.append("tags must be a list")
        
        if errors:
            raise ValidationError(
                f"YAML structure validation failed: {', '.join(errors)}",
                error_code="YAML_VALIDATION_ERROR",
                context={"errors": errors}
            )
        
        return True
    
    def repair_yaml_header(self, file_path: Path) -> bool:
        """
        破損したYAMLヘッダーの修復
        
        Args:
            file_path: 修復対象ファイルのパス
            
        Returns:
            bool: 修復成功の場合True
        """
        try:
            # 修復前のバックアップ作成
            try:
                should_backup = self.config_manager.get('status_management.auto_backup', True)
            except (AttributeError, TypeError):
                should_backup = True  # デフォルト値
            
            if should_backup:
                self.backup_manager.create_backup(file_path)
            
            # ファイル内容の読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # citation_keyの抽出を試行
            citation_key = self.extract_citation_key_from_content(str(file_path), content)
            
            # 基本的なYAMLヘッダーテンプレートの生成
            repaired_yaml = self._create_basic_yaml_template(citation_key)
            
            # Markdownコンテンツの抽出（YAML部分を除去）
            markdown_content = self._extract_markdown_content_only(content)
            
            # 修復されたファイルの書き込み
            self.write_yaml_header(file_path, repaired_yaml, markdown_content)
            
            self.logger.info(f"Successfully repaired YAML header in {file_path.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair YAML header in {file_path.name}: {e}")
            return False
    
    def extract_citation_key_from_content(self, file_path: str, content: str) -> str:
        """
        ファイルパスやコンテンツからcitation_keyを抽出
        
        Args:
            file_path: ファイルパス
            content: ファイル内容
            
        Returns:
            str: 抽出されたcitation_key
        """
        # ファイル名から抽出（拡張子を除く）
        file_stem = Path(file_path).stem
        if file_stem and file_stem != "unknown":
            return file_stem
        
        # DOIから抽出を試行
        doi_match = re.search(r'DOI:\s*10\.\d+/([^\s]+)', content)
        if doi_match:
            doi_part = doi_match.group(1)
            # DOIから適切なcitation_keyを生成（暫定的に現在年を使用）
            current_year = datetime.now().year
            return self.string_utils.format_citation_key(doi_part.split('.')[-1], str(current_year))
        
        # デフォルトキーを生成
        return f"unknown_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def update_metadata_fields(self, yaml_header: Dict[str, Any]) -> None:
        """
        メタデータフィールドの自動更新
        
        Args:
            yaml_header: 更新対象のYAMLヘッダー（インプレース更新）
        """
        current_time = datetime.now().isoformat()
        
        # last_updatedの更新
        yaml_header['last_updated'] = current_time
        
        # workflow_versionの設定
        yaml_header['workflow_version'] = '3.2'
        
        # created_atが存在しない場合のみ設定
        if not yaml_header.get('created_at'):
            yaml_header['created_at'] = current_time
    
    def batch_validate_directory(self, directory: Path) -> Dict[str, List[str]]:
        """
        ディレクトリ内の全Markdownファイルを一括検証
        
        Args:
            directory: 検証対象ディレクトリ
            
        Returns:
            Dict[str, List[str]]: 検証結果（valid_files, invalid_files, no_yaml_files）
        """
        results = {
            'valid_files': [],
            'invalid_files': [],
            'no_yaml_files': []
        }
        
        markdown_files = list(directory.glob("**/*.md"))
        
        for md_file in markdown_files:
            try:
                yaml_header, _ = self.parse_yaml_header(md_file)
                self.validate_yaml_structure(yaml_header)
                results['valid_files'].append(str(md_file))
                
            except YAMLError:
                results['invalid_files'].append(str(md_file))
                
            except Exception:
                # YAMLヘッダーが存在しない等
                results['no_yaml_files'].append(str(md_file))
        
        self.logger.info(
            f"Batch validation completed: "
            f"{len(results['valid_files'])} valid, "
            f"{len(results['invalid_files'])} invalid, "
            f"{len(results['no_yaml_files'])} no YAML"
        )
        
        return results
    
    def batch_repair_directory(self, directory: Path) -> Dict[str, List[str]]:
        """
        ディレクトリ内の破損したMarkdownファイルを一括修復
        
        Args:
            directory: 修復対象ディレクトリ
            
        Returns:
            Dict[str, List[str]]: 修復結果（repaired_files, failed_repairs）
        """
        results = {
            'repaired_files': [],
            'failed_repairs': []
        }
        
        # まず問題のあるファイルを特定
        validation_results = self.batch_validate_directory(directory)
        problematic_files = validation_results['invalid_files'] + validation_results['no_yaml_files']
        
        for file_path in problematic_files:
            if self.repair_yaml_header(Path(file_path)):
                results['repaired_files'].append(file_path)
            else:
                results['failed_repairs'].append(file_path)
        
        self.logger.info(
            f"Batch repair completed: "
            f"{len(results['repaired_files'])} repaired, "
            f"{len(results['failed_repairs'])} failed"
        )
        
        return results
    
    def _extract_yaml_and_content(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        ファイル内容からYAMLヘッダーとMarkdownコンテンツを分離
        
        Args:
            content: ファイル全体の内容
            
        Returns:
            Tuple[Dict[str, Any], str]: YAMLヘッダーとMarkdownコンテンツ
            
        Raises:
            YAMLError: YAML解析エラーの場合
        """
        if not content.startswith('---'):
            raise YAMLError(
                "No YAML front matter found",
                error_code="NO_YAML_HEADER"
            )
        
        # 2番目の --- を探す
        yaml_end = content.find('---', 3)
        if yaml_end == -1:
            raise YAMLError(
                "Incomplete YAML front matter (missing closing ---)",
                error_code="INCOMPLETE_YAML_HEADER"
            )
        
        # YAML部分とMarkdown部分を分離
        yaml_content = content[3:yaml_end].strip()
        markdown_content = content[yaml_end + 3:].lstrip('\n')
        
        try:
            yaml_header = yaml.safe_load(yaml_content)
            if not isinstance(yaml_header, dict):
                raise YAMLError(
                    "YAML header must be a dictionary",
                    error_code="INVALID_YAML_STRUCTURE"
                )
            
            return yaml_header, markdown_content
            
        except yaml.YAMLError as e:
            raise YAMLError(
                f"YAML parsing error: {e}",
                error_code="YAML_PARSE_ERROR"
            )
    
    def _create_basic_yaml_template(self, citation_key: str) -> Dict[str, Any]:
        """
        基本的なYAMLヘッダーテンプレートを作成
        
        Args:
            citation_key: 論文の識別キー
            
        Returns:
            Dict[str, Any]: 基本YAMLヘッダー
        """
        current_time = datetime.now().isoformat()
        
        return {
            'citation_key': citation_key,
            'workflow_version': '3.2',
            'last_updated': current_time,
            'created_at': current_time,
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending',
                'fetch': 'pending',
                'ai_citation_support': 'pending',
                'section_parsing': 'pending',
                'tagger': 'pending',
                'translate_abstract': 'pending',
                'ochiai_format': 'pending',
                'final_sync': 'pending'
            },
            'tags': [],
            'citation_metadata': {
                'last_updated': None,
                'mapping_version': None,
                'source_bibtex': None,
                'total_citations': 0
            },
            'citations': {},
            'paper_structure': {
                'parsed_at': None,
                'total_sections': 0,
                'sections': [],
                'section_types_found': []
            },
            'ai_content': {
                'abstract_japanese': {
                    'generated_at': None,
                    'content': None
                },
                'ochiai_format': {
                    'generated_at': None,
                    'questions': {
                        'what_is_this': None,
                        'what_is_superior': None,
                        'technical_key': None,
                        'validation_method': None,
                        'discussion_points': None,
                        'next_papers': None
                    }
                }
            },
            'execution_summary': {
                'executed_at': None,
                'total_execution_time': 0,
                'steps_executed': [],
                'steps_summary': {},
                'edge_cases': {}
            },
            'error_history': [],
            'backup_information': {
                'last_backup_at': None,
                'backup_location': None,
                'recovery_available': False
            }
        }
    
    def _extract_markdown_content_only(self, content: str) -> str:
        """
        YAML部分を除いたMarkdownコンテンツのみを抽出
        
        Args:
            content: ファイル全体の内容
            
        Returns:
            str: Markdownコンテンツのみ
        """
        if content.startswith('---'):
            yaml_end = content.find('---', 3)
            if yaml_end != -1:
                return content[yaml_end + 3:].lstrip('\n')
        
        # YAML部分が見つからない場合は全体を返す
        return content 