#!/usr/bin/env python3
"""
ConfigManager - 統一設定管理システム

ObsClippingsManagerの設定管理を統括するクラス
- YAML設定ファイル読み込み
- 環境変数統合
- デフォルト値適用
- 設定階層管理（コマンドライン > 環境変数 > 設定ファイル > デフォルト）
- パス自動導出
- 設定検証
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
from .exceptions import ConfigurationError, ValidationError


class ConfigManager:
    """
    統一設定管理クラス
    
    設定の読み込み、検証、アクセス機能を提供。
    階層的設定管理により、柔軟な設定上書きをサポート。
    """
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        ConfigManagerの初期化
        
        Args:
            config_file (str): 設定ファイルのパス
            
        Raises:
            ConfigurationError: 設定読み込みまたは検証に失敗した場合
        """
        self.config_file = config_file
        self.config = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        設定ファイルの読み込みとデフォルト値の適用
        
        Returns:
            Dict[str, Any]: マージされた設定辞書
            
        Raises:
            ConfigurationError: 設定ファイル読み込みに失敗した場合
        """
        try:
            # 設定ファイルの読み込み
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = yaml.safe_load(f) or {}
            else:
                file_config = {}
            
            # デフォルト設定の取得
            default_config = self._get_default_config()
            
            # 環境変数の統合
            env_config = self._get_environment_config()
            
            # 設定のマージ（デフォルト < ファイル < 環境変数）
            merged_config = self._merge_configs(default_config, file_config)
            merged_config = self._merge_configs(merged_config, env_config)
            
            return merged_config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML format in config file {self.config_file}: {e}",
                error_code="YAML_PARSE_ERROR",
                context={"config_file": self.config_file}
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from {self.config_file}: {e}",
                error_code="CONFIG_LOAD_ERROR",
                context={"config_file": self.config_file},
                cause=e
            )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定の取得
        
        Returns:
            Dict[str, Any]: デフォルト設定辞書
        """
        return {
            'workspace_path': '/home/user/ManuscriptsManager',
            'api_settings': {
                'request_delay': 1.0,
                'max_retries': 3,
                'timeout': 30
            },
            'ai_generation': {
                'default_model': 'claude-3-5-haiku-20241022',
                'api_key_env': 'ANTHROPIC_API_KEY',
                'tagger': {
                    'enabled': True,
                    'batch_size': 8,
                    'tag_count_range': [10, 20]
                },
                'translate_abstract': {
                    'enabled': True,
                    'batch_size': 5,
                    'preserve_formatting': True
                },
                'ochiai_format': {
                    'enabled': True,
                    'batch_size': 3
                },
                'section_parsing': {
                    'enabled': True
                }
            },
            'logging': {
                'log_file': 'logs/obsclippings.log',
                'log_level': 'INFO',
                'max_file_size': '10MB',
                'backup_count': 5
            },
            'error_handling': {
                'enabled': True,
                'capture_context': True,
                'auto_retry_on_transient_errors': True,
                'max_retry_attempts': 3,
                'retry_delay_seconds': 2
            },
            'backup_settings': {
                'enabled': True,
                'auto_backup_before_processing': True,
                'backup_location': 'backups/',
                'retention_days': 30,
                'max_backup_size_mb': 1000,
                'compress_old_backups': True
            }
        }
    
    def _get_environment_config(self) -> Dict[str, Any]:
        """
        環境変数から設定を取得
        
        Returns:
            Dict[str, Any]: 環境変数ベースの設定辞書
        """
        env_config = {}
        
        # 主要設定の環境変数チェック
        if 'WORKSPACE_PATH' in os.environ:
            env_config['workspace_path'] = os.environ['WORKSPACE_PATH']
        
        if 'ERROR_HANDLING_ENABLED' in os.environ:
            env_config.setdefault('error_handling', {})['enabled'] = \
                os.environ['ERROR_HANDLING_ENABLED'].lower() == 'true'
        
        if 'MAX_RETRY_ATTEMPTS' in os.environ:
            env_config.setdefault('error_handling', {})['max_retry_attempts'] = \
                int(os.environ['MAX_RETRY_ATTEMPTS'])
        
        if 'BACKUP_ENABLED' in os.environ:
            env_config.setdefault('backup_settings', {})['enabled'] = \
                os.environ['BACKUP_ENABLED'].lower() == 'true'
        
        if 'BACKUP_LOCATION' in os.environ:
            env_config.setdefault('backup_settings', {})['backup_location'] = \
                os.environ['BACKUP_LOCATION']
        
        return env_config
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        設定辞書の再帰的マージ
        
        Args:
            base (Dict[str, Any]): ベース設定
            override (Dict[str, Any]): 上書き設定
            
        Returns:
            Dict[str, Any]: マージされた設定
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self) -> None:
        """
        設定の妥当性検証
        
        Raises:
            ConfigurationError: 設定に問題がある場合
        """
        try:
            # workspace_pathの検証
            workspace_path = self.config.get('workspace_path')
            if not workspace_path or not isinstance(workspace_path, str):
                raise ConfigurationError(
                    "workspace_path must be a non-empty string",
                    error_code="INVALID_WORKSPACE_PATH"
                )
            
            # api_settingsの検証
            api_settings = self.config.get('api_settings', {})
            if not isinstance(api_settings, dict):
                raise ConfigurationError(
                    "api_settings must be a dictionary",
                    error_code="INVALID_API_SETTINGS"
                )
            
            # AI設定の検証
            ai_generation = self.config.get('ai_generation', {})
            if not isinstance(ai_generation, dict):
                raise ConfigurationError(
                    "ai_generation must be a dictionary",
                    error_code="INVALID_AI_GENERATION"
                )
                
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Configuration validation failed: {e}",
                error_code="CONFIG_VALIDATION_ERROR",
                cause=e
            )
    
    # 設定アクセスメソッド
    
    def get_workspace_path(self) -> str:
        """ワークスペースパスの取得"""
        return self.config['workspace_path']
    
    def get_bibtex_file(self) -> str:
        """BibTeXファイルパスの自動導出"""
        workspace = self.get_workspace_path()
        return os.path.join(workspace, 'CurrentManuscript.bib')
    
    def get_clippings_dir(self) -> str:
        """Clippingsディレクトリパスの自動導出"""
        workspace = self.get_workspace_path()
        return os.path.join(workspace, 'Clippings')
    
    def get_output_dir(self) -> str:
        """出力ディレクトリパスの自動導出"""
        # 現在はClippingsディレクトリと同じ
        return self.get_clippings_dir()
    
    def get_api_setting(self, key: str, default: Any = None) -> Any:
        """
        API設定の取得
        
        Args:
            key (str): 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        return self.config.get('api_settings', {}).get(key, default)
    
    def get_ai_setting(self, *keys: str, default: Any = None) -> Any:
        """
        AI設定の取得（ネストしたキーをサポート）
        
        Args:
            *keys: ネストしたキー（例: 'tagger', 'enabled'）
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        current = self.config.get('ai_generation', {})
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_logging_setting(self, key: str, default: Any = None) -> Any:
        """
        ログ設定の取得
        
        Args:
            key (str): 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        return self.config.get('logging', {}).get(key, default)
    
    def get_error_handling_setting(self, key: str, default: Any = None) -> Any:
        """
        エラーハンドリング設定の取得
        
        Args:
            key (str): 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        return self.config.get('error_handling', {}).get(key, default)
    
    def get_backup_setting(self, key: str, default: Any = None) -> Any:
        """
        バックアップ設定の取得
        
        Args:
            key (str): 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        return self.config.get('backup_settings', {}).get(key, default)
    
    # 設定更新メソッド
    
    def update_config(self, key: str, value: Any) -> None:
        """
        設定値の更新
        
        Args:
            key (str): 設定キー
            value (Any): 新しい値
        """
        self.config[key] = value
    
    def update_nested_config(self, keys: list, value: Any) -> None:
        """
        ネストした設定値の更新
        
        Args:
            keys (list): ネストしたキーのリスト
            value (Any): 新しい値
        """
        current = self.config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def save_config(self) -> None:
        """
        現在の設定をファイルに保存
        
        Raises:
            ConfigurationError: 保存に失敗した場合
        """
        try:
            # ディレクトリの作成
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            # 設定ファイルの保存
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            raise ConfigurationError(
                f"Failed to save configuration to {self.config_file}: {e}",
                error_code="CONFIG_SAVE_ERROR",
                context={"config_file": self.config_file},
                cause=e
            )
    
    # ユーティリティメソッド
    
    def get_config(self) -> Dict[str, Any]:
        """
        設定辞書全体の取得
        
        Returns:
            Dict[str, Any]: 設定辞書のコピー
        """
        return self.config.copy()
    
    def has_config(self, key: str) -> bool:
        """
        設定キーの存在確認
        
        Args:
            key (str): 設定キー
            
        Returns:
            bool: キーが存在するかどうか
        """
        return key in self.config
    
    def get_derived_paths(self) -> Dict[str, str]:
        """
        自動導出されるパス一覧の取得
        
        Returns:
            Dict[str, str]: パス名と値の辞書
        """
        return {
            'workspace_path': self.get_workspace_path(),
            'bibtex_file': self.get_bibtex_file(),
            'clippings_dir': self.get_clippings_dir(),
            'output_dir': self.get_output_dir()
        } 