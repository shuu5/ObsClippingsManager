#!/usr/bin/env python3
"""
ワークフローバージョン管理

WorkflowVersionManager

ワークフローバージョンの管理、互換性チェック、マイグレーション機能を担当。
古いYAMLヘッダーを新しい形式に自動変換し、下位互換性を確保。
"""

import os
import re
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from .yaml_header_processor import YAMLHeaderProcessor
from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import ValidationError, ProcessingError
from ..shared_modules.file_utils import BackupManager


class WorkflowVersionManager:
    """
    ワークフローバージョン管理クラス
    
    ワークフローのバージョン管理と互換性チェック、自動マイグレーション機能を提供。
    古いバージョンのYAMLヘッダーを新しい形式に安全に変換する。
    """
    
    # サポートされているワークフローバージョン
    SUPPORTED_VERSIONS = ['3.0', '3.1', '3.2']
    CURRENT_VERSION = '3.2'
    
    # バージョン間のマイグレーション定義
    MIGRATION_RULES = {
        ('unknown', '3.2'): '_migrate_unknown_to_3_2',
        ('3.0', '3.2'): '_migrate_3_0_to_3_2',
        ('3.1', '3.2'): '_migrate_3_1_to_3_2'
    }
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        WorkflowVersionManagerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('WorkflowVersionManager')
        self.yaml_processor = YAMLHeaderProcessor(config_manager, logger)
        self.backup_manager = BackupManager()
        
        self.current_version = self.CURRENT_VERSION
        
        self.logger.info("WorkflowVersionManager initialized")
    
    def check_version_compatibility(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        YAMLヘッダーのバージョン互換性をチェック
        
        Args:
            yaml_header: 対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: 互換性チェック結果
        """
        file_version = yaml_header.get('workflow_version', 'unknown')
        
        result = {
            'current_version': self.current_version,
            'file_version': file_version,
            'compatible': False,
            'migration_needed': False,
            'version_diff': None,
            'error_message': None
        }
        
        # バージョンフォーマット検証
        if file_version != 'unknown' and not self._validate_version_format(file_version):
            result['error_message'] = f"Invalid version format: {file_version}"
            return result
        
        # 現在バージョンと同じ場合
        if file_version == self.current_version:
            result['compatible'] = True
            return result
        
        # 未知バージョンまたは古いバージョンの場合
        if file_version == 'unknown' or self._is_older_version(file_version):
            result['compatible'] = True
            result['migration_needed'] = True
            result['version_diff'] = self._calculate_version_diff(file_version, self.current_version)
            return result
        
        # 新しいバージョンの場合（非互換）
        if self._is_newer_version(file_version):
            result['error_message'] = f"File version {file_version} is newer than current version {self.current_version}"
            return result
        
        result['compatible'] = True
        return result
    
    def migrate_version(
        self, 
        yaml_header: Dict[str, Any], 
        from_version: str, 
        to_version: str
    ) -> Dict[str, Any]:
        """
        YAMLヘッダーのバージョンマイグレーション
        
        Args:
            yaml_header: マイグレーション対象のYAMLヘッダー
            from_version: 変換元バージョン
            to_version: 変換先バージョン
            
        Returns:
            Dict[str, Any]: マイグレーション後のYAMLヘッダー
            
        Raises:
            ValidationError: サポートされていないマイグレーションの場合
        """
        migration_key = (from_version, to_version)
        
        if migration_key not in self.MIGRATION_RULES:
            raise ValidationError(
                f"Unsupported migration from {from_version} to {to_version}",
                error_code="UNSUPPORTED_MIGRATION"
            )
        
        migration_method = getattr(self, self.MIGRATION_RULES[migration_key])
        migrated_header = migration_method(yaml_header.copy())
        
        # マイグレーション履歴を追加
        if 'migration_history' not in migrated_header:
            migrated_header['migration_history'] = []
        
        migration_record = {
            'from_version': from_version,
            'to_version': to_version,
            'migrated_at': datetime.now().isoformat(),
            'migration_type': 'automatic'
        }
        migrated_header['migration_history'].append(migration_record)
        
        self.logger.info(f"Migrated YAML header from {from_version} to {to_version}")
        return migrated_header
    
    def update_version(self, file_path: Path) -> Dict[str, Any]:
        """
        ファイルのワークフローバージョンを更新
        
        Args:
            file_path: 更新対象のファイルパス
            
        Returns:
            Dict[str, Any]: 更新結果
            
        Raises:
            ProcessingError: ファイルが見つからない、更新に失敗した場合
        """
        if not file_path.exists():
            raise ProcessingError(
                f"File not found: {file_path}",
                error_code="FILE_NOT_FOUND"
            )
        
        try:
            yaml_header, content = self.yaml_processor.parse_yaml_header(file_path)
            
            compatibility = self.check_version_compatibility(yaml_header)
            
            result = {
                'file_path': str(file_path),
                'from_version': compatibility['file_version'],
                'to_version': self.current_version,
                'updated': False,
                'migration_performed': False,
                'error': None
            }
            
            # 更新が不要な場合
            if not compatibility['migration_needed']:
                return result
            
            # バックアップ作成
            if self.config_manager.get_config().get('version_management', {}).get('backup_before_migration', True):
                self.backup_manager.create_backup(file_path)
            
            # マイグレーション実行
            from_version = compatibility['file_version']
            migrated_header = self.migrate_version(yaml_header, from_version, self.current_version)
            
            # メタデータ更新
            migrated_header['last_updated'] = datetime.now().isoformat()
            
            # ファイルに書き戻し
            self.yaml_processor.write_yaml_header(file_path, migrated_header, content)
            
            result.update({
                'updated': True,
                'migration_performed': True
            })
            
            self.logger.info(f"Updated version for {file_path.name} from {from_version} to {self.current_version}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to update version for {file_path}: {e}"
            self.logger.error(error_msg)
            raise ProcessingError(
                error_msg,
                error_code="VERSION_UPDATE_FAILED",
                context={"file": str(file_path)}
            )
    
    def batch_version_update(self, directory: str) -> Dict[str, Any]:
        """
        ディレクトリ内の全Markdownファイルのバージョンを一括更新
        
        Args:
            directory: 対象ディレクトリのパス
            
        Returns:
            Dict[str, Any]: 一括更新結果
        """
        pattern = os.path.join(directory, "**/*.md")
        md_files = glob.glob(pattern, recursive=True)
        
        results = {
            'total_files': len(md_files),
            'updated_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'update_details': [],
            'errors': []
        }
        
        for md_file in md_files:
            try:
                file_path = Path(md_file)
                update_result = self.update_version(file_path)
                
                if update_result['updated']:
                    results['updated_files'] += 1
                    results['update_details'].append({
                        'filename': file_path.name,
                        'from_version': update_result['from_version'],
                        'to_version': update_result['to_version'],
                        'migration_performed': update_result['migration_performed']
                    })
                else:
                    results['skipped_files'] += 1
                    
            except Exception as e:
                results['failed_files'] += 1
                results['errors'].append({
                    'filename': Path(md_file).name,
                    'error': str(e)
                })
                self.logger.warning(f"Failed to update version for {md_file}: {e}")
        
        self.logger.info(
            f"Batch version update completed: "
            f"{results['updated_files']} updated, "
            f"{results['skipped_files']} skipped, "
            f"{results['failed_files']} failed"
        )
        
        return results
    
    def get_version_history(self, yaml_header: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        YAMLヘッダーからバージョン履歴を取得
        
        Args:
            yaml_header: 対象のYAMLヘッダー
            
        Returns:
            List[Dict[str, Any]]: バージョン履歴リスト
        """
        return yaml_header.get('migration_history', [])
    
    def _validate_version_format(self, version: str) -> bool:
        """
        バージョンフォーマットの検証
        
        Args:
            version: 検証対象のバージョン文字列
            
        Returns:
            bool: 有効なフォーマットの場合True
        """
        if version == 'unknown':
            return True
        
        # X.Y形式のバージョン（例: 3.2, 3.1）
        pattern = r'^\d+\.\d+$'
        return bool(re.match(pattern, version))
    
    def _is_older_version(self, version: str) -> bool:
        """
        指定されたバージョンが現在より古いかチェック
        
        Args:
            version: チェック対象のバージョン
            
        Returns:
            bool: 古いバージョンの場合True
        """
        if version == 'unknown':
            return True
        
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            version_parts = [int(x) for x in version.split('.')]
            
            return version_parts < current_parts
        except ValueError:
            return True
    
    def _is_newer_version(self, version: str) -> bool:
        """
        指定されたバージョンが現在より新しいかチェック
        
        Args:
            version: チェック対象のバージョン
            
        Returns:
            bool: 新しいバージョンの場合True
        """
        if version == 'unknown':
            return False
        
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            version_parts = [int(x) for x in version.split('.')]
            
            return version_parts > current_parts
        except ValueError:
            return False
    
    def _calculate_version_diff(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """
        バージョン間の差分を計算
        
        Args:
            from_version: 変換元バージョン
            to_version: 変換先バージョン
            
        Returns:
            Dict[str, Any]: バージョン差分情報
        """
        return {
            'from': from_version,
            'to': to_version,
            'major_changes': self._get_major_changes(from_version, to_version),
            'new_features': self._get_new_features(from_version, to_version)
        }
    
    def _get_major_changes(self, from_version: str, to_version: str) -> List[str]:
        """
        バージョン間の主要変更点を取得
        
        Args:
            from_version: 変換元バージョン
            to_version: 変換先バージョン
            
        Returns:
            List[str]: 主要変更点のリスト
        """
        changes = []
        
        if from_version in ['unknown', '3.0', '3.1'] and to_version == '3.2':
            changes.extend([
                'AI機能ワークフローの統合',
                '統一YAMLテンプレート導入',
                'エラーハンドリング強化',
                'バックアップシステム改善'
            ])
        
        return changes
    
    def _get_new_features(self, from_version: str, to_version: str) -> List[str]:
        """
        バージョン間の新機能を取得
        
        Args:
            from_version: 変換元バージョン
            to_version: 変換先バージョン
            
        Returns:
            List[str]: 新機能のリスト
        """
        features = []
        
        if from_version in ['unknown', '3.0', '3.1'] and to_version == '3.2':
            features.extend([
                'section_parsing: セクション分割機能',
                'ai_citation_support: AI理解支援引用文献パーサー',
                'tagger: AI自動タグ生成',
                'translate_abstract: 要約翻訳機能',
                'ochiai_format: 落合フォーマット要約',
                'citation_metadata: 引用文献メタデータ管理',
                'ai_content: AI生成コンテンツセクション'
            ])
        
        return features
    
    def _migrate_unknown_to_3_2(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        未知バージョンから3.2へのマイグレーション
        
        Args:
            yaml_header: マイグレーション対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: マイグレーション後のYAMLヘッダー
        """
        # 基本テンプレートを作成
        migrated = self._create_3_2_template(yaml_header.get('citation_key', 'unknown'))
        
        # 既存の値を保持
        migrated.update({
            k: v for k, v in yaml_header.items() 
            if k not in ['workflow_version', 'created_at', 'last_updated']
        })
        
        # 必須フィールドの追加・更新
        current_time = datetime.now().isoformat()
        migrated.update({
            'workflow_version': '3.2',
            'last_updated': current_time,
            'created_at': yaml_header.get('created_at', current_time)
        })
        
        return migrated
    
    def _migrate_3_0_to_3_2(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        バージョン3.0から3.2へのマイグレーション
        
        Args:
            yaml_header: マイグレーション対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: マイグレーション後のYAMLヘッダー
        """
        # 3.1へマイグレーション後、3.2へマイグレーション
        v3_1 = self._migrate_3_0_to_3_1(yaml_header)
        return self._migrate_3_1_to_3_2(v3_1)
    
    def _migrate_3_1_to_3_2(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        バージョン3.1から3.2へのマイグレーション
        
        Args:
            yaml_header: マイグレーション対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: マイグレーション後のYAMLヘッダー
        """
        migrated = yaml_header.copy()
        
        # ワークフローバージョン更新
        migrated['workflow_version'] = '3.2'
        
        # 新しい処理ステップを追加（既存のものは保持）
        if 'processing_status' not in migrated:
            migrated['processing_status'] = {}
        
        new_steps = {
            'fetch': 'pending',
            'section_parsing': 'pending',
            'ai_citation_support': 'pending',
            'tagger': 'pending',
            'translate_abstract': 'pending',
            'ochiai_format': 'pending',
            'final_sync': 'pending'
        }
        
        for step, default_status in new_steps.items():
            if step not in migrated['processing_status']:
                migrated['processing_status'][step] = default_status
        
        # 新しいセクションを追加（既存のものは保持）
        if 'citation_metadata' not in migrated:
            migrated['citation_metadata'] = {
                'last_updated': None,
                'mapping_version': None,
                'source_bibtex': None,
                'total_citations': 0
            }
        
        if 'citations' not in migrated:
            migrated['citations'] = {}
        
        if 'paper_structure' not in migrated:
            migrated['paper_structure'] = {
                'parsed_at': None,
                'total_sections': 0,
                'sections': [],
                'section_types_found': []
            }
        
        if 'ai_content' not in migrated:
            migrated['ai_content'] = {
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
            }
        
        if 'tags' not in migrated:
            migrated['tags'] = []
        
        # 統合ワークフロー実行記録セクション
        if 'execution_summary' not in migrated:
            migrated['execution_summary'] = {
                'executed_at': None,
                'total_execution_time': 0,
                'steps_executed': [],
                'steps_summary': {},
                'edge_cases': {}
            }
        
        # エラー・バックアップ情報セクション
        if 'error_history' not in migrated:
            migrated['error_history'] = []
        
        if 'backup_information' not in migrated:
            migrated['backup_information'] = {
                'last_backup_at': None,
                'backup_location': None,
                'recovery_available': False
            }
        
        return migrated
    
    def _migrate_3_0_to_3_1(self, yaml_header: Dict[str, Any]) -> Dict[str, Any]:
        """
        バージョン3.0から3.1へのマイグレーション（中間ステップ）
        
        Args:
            yaml_header: マイグレーション対象のYAMLヘッダー
            
        Returns:
            Dict[str, Any]: マイグレーション後のYAMLヘッダー
        """
        migrated = yaml_header.copy()
        migrated['workflow_version'] = '3.1'
        
        # 3.1で追加された機能（仮）
        if 'processing_status' not in migrated:
            migrated['processing_status'] = {}
        
        # 基本的な処理ステップが存在することを確認
        basic_steps = ['organize', 'sync', 'fetch']
        for step in basic_steps:
            if step not in migrated['processing_status']:
                migrated['processing_status'][step] = 'pending'
        
        return migrated
    
    def _create_3_2_template(self, citation_key: str) -> Dict[str, Any]:
        """
        バージョン3.2の基本テンプレートを作成
        
        Args:
            citation_key: 論文の識別キー
            
        Returns:
            Dict[str, Any]: 3.2テンプレート
        """
        current_time = datetime.now().isoformat()
        
        return {
            'tags': [],
            'citation_key': citation_key,
            'workflow_version': '3.2',
            'last_updated': current_time,
            'created_at': current_time,
            'processing_status': {
                'organize': 'pending',
                'sync': 'pending',
                'fetch': 'pending',
                'section_parsing': 'pending',
                'ai_citation_support': 'pending',
                'tagger': 'pending',
                'translate_abstract': 'pending',
                'ochiai_format': 'pending',
                'final_sync': 'pending'
            },
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