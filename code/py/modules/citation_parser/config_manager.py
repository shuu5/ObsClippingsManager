"""
引用パーサー設定管理

設定ファイルの読み込みとパターン管理を行う
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .data_structures import PatternConfig
from .exceptions import ConfigurationError


class ConfigManager:
    """引用パーサー設定管理"""
    
    DEFAULT_CONFIG = {
        'patterns': {
            'linked_citation': {
                'regex': r'\[(\^?\d+)\]\(([^)]+)\)',
                'type': 'linked',
                'priority': 1,
                'enabled': True
            },
            'footnote_citation': {
                'regex': r'\[\^(\d+)\]',
                'type': 'footnote',
                'priority': 2,
                'enabled': True
            },
            'range_citation': {
                'regex': r'\[(\d+)[-–](\d+)\]',
                'type': 'range',
                'priority': 3,
                'enabled': True
            },
            'multiple_citation': {
                'regex': r'\[(\d+(?:[,\s]+\d+)+)\]',
                'type': 'multiple',
                'priority': 4,
                'enabled': True
            },
            'single_citation': {
                'regex': r'\[(\d+)\]',
                'type': 'single',
                'priority': 5,
                'enabled': True
            },
            'mixed_footnote': {
                'regex': r'\[\^(\d+(?:,\^?\d+)*)\]',
                'type': 'footnote',
                'priority': 6,
                'enabled': True
            }
        },
        'output_formats': {
            'standard': {
                'single': '[{number}]',
                'multiple': '[{numbers}]',
                'separator': ',',
                'sort_numbers': True,
                'expand_ranges': True,
                'remove_spaces': False
            },
            'compact': {
                'single': '[{number}]',
                'multiple': '[{numbers}]',
                'separator': ',',
                'sort_numbers': True,
                'expand_ranges': True,
                'remove_spaces': True
            },
            'spaced': {
                'single': '[{number}]',
                'multiple': '[{numbers}]',
                'separator': ', ',
                'sort_numbers': True,
                'expand_ranges': True,
                'remove_spaces': False
            }
        },
        'conversion_rules': {
            'expand_ranges': True,
            'remove_spaces': False,
            'sort_numbers': True,
            'merge_adjacent': False,
            'validate_urls': True
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルパス
        """
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("ObsClippingsManager.CitationParser.ConfigManager")
        
        # 設定を読み込み
        self._load_config()
    
    def _load_config(self):
        """設定を読み込み"""
        if self.config_path and Path(self.config_path).exists():
            try:
                self.config = self._load_yaml_config(self.config_path)
                self.logger.info(f"Loaded config from: {self.config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load config file: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.logger.debug("Using default configuration")
    
    def _load_yaml_config(self, config_path: str) -> Dict[str, Any]:
        """YAMLファイルから設定を読み込み"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # デフォルト設定とマージ
            merged_config = self.DEFAULT_CONFIG.copy()
            self._deep_update(merged_config, config)
            
            return merged_config
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read config file: {e}")
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict):
        """辞書を深い階層まで更新"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get_pattern_configs(self) -> List[PatternConfig]:
        """
        パターン設定のリストを取得
        
        Returns:
            PatternConfigのリスト
        """
        patterns = []
        
        pattern_configs = self.config.get('patterns', {})
        for name, config in pattern_configs.items():
            try:
                pattern = PatternConfig(
                    name=name,
                    regex=config['regex'],
                    pattern_type=config['type'],
                    priority=config['priority'],
                    enabled=config.get('enabled', True)
                )
                patterns.append(pattern)
            except KeyError as e:
                self.logger.warning(f"Invalid pattern config '{name}': missing {e}")
                continue
        
        return patterns
    
    def get_output_format_config(self, format_name: str = 'standard') -> Dict[str, Any]:
        """
        出力フォーマット設定を取得
        
        Args:
            format_name: フォーマット名
            
        Returns:
            フォーマット設定辞書
        """
        formats = self.config.get('output_formats', {})
        
        if format_name not in formats:
            self.logger.warning(f"Unknown format '{format_name}', using 'standard'")
            format_name = 'standard'
        
        return formats.get(format_name, formats['standard'])
    
    def get_conversion_rules(self) -> Dict[str, Any]:
        """
        変換ルール設定を取得
        
        Returns:
            変換ルール設定辞書
        """
        return self.config.get('conversion_rules', {})
    
    def add_custom_pattern(self, name: str, regex: str, pattern_type: str, 
                          priority: int, enabled: bool = True):
        """
        カスタムパターンを追加
        
        Args:
            name: パターン名
            regex: 正規表現
            pattern_type: パターンタイプ
            priority: 優先度
            enabled: 有効/無効
        """
        if 'patterns' not in self.config:
            self.config['patterns'] = {}
        
        self.config['patterns'][name] = {
            'regex': regex,
            'type': pattern_type,
            'priority': priority,
            'enabled': enabled
        }
        
        self.logger.info(f"Added custom pattern: {name}")
    
    def disable_pattern(self, pattern_name: str):
        """
        パターンを無効化
        
        Args:
            pattern_name: パターン名
        """
        if pattern_name in self.config.get('patterns', {}):
            self.config['patterns'][pattern_name]['enabled'] = False
            self.logger.info(f"Disabled pattern: {pattern_name}")
        else:
            raise ConfigurationError(f"Pattern not found: {pattern_name}")
    
    def enable_pattern(self, pattern_name: str):
        """
        パターンを有効化
        
        Args:
            pattern_name: パターン名
        """
        if pattern_name in self.config.get('patterns', {}):
            self.config['patterns'][pattern_name]['enabled'] = True
            self.logger.info(f"Enabled pattern: {pattern_name}")
        else:
            raise ConfigurationError(f"Pattern not found: {pattern_name}")
    
    def save_config(self, output_path: str):
        """
        設定をファイルに保存
        
        Args:
            output_path: 出力ファイルパス
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            
            self.logger.info(f"Saved config to: {output_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save config: {e}")
    
    def validate_config(self) -> List[str]:
        """
        設定の妥当性を検証
        
        Returns:
            エラーメッセージのリスト
        """
        errors = []
        
        # パターン設定の検証
        patterns = self.config.get('patterns', {})
        if not patterns:
            errors.append("No patterns defined")
        
        for name, pattern in patterns.items():
            # 必須フィールドの確認
            required_fields = ['regex', 'type', 'priority']
            for field in required_fields:
                if field not in pattern:
                    errors.append(f"Pattern '{name}' missing required field: {field}")
            
            # 正規表現の妥当性
            try:
                import re
                re.compile(pattern.get('regex', ''))
            except re.error as e:
                errors.append(f"Invalid regex in pattern '{name}': {e}")
        
        # 出力フォーマットの検証
        formats = self.config.get('output_formats', {})
        for format_name, format_config in formats.items():
            required_format_fields = ['single', 'multiple', 'separator']
            for field in required_format_fields:
                if field not in format_config:
                    errors.append(f"Format '{format_name}' missing required field: {field}")
        
        return errors
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        設定の概要を取得
        
        Returns:
            設定概要辞書
        """
        patterns = self.config.get('patterns', {})
        enabled_patterns = [name for name, config in patterns.items() 
                           if config.get('enabled', True)]
        
        return {
            'total_patterns': len(patterns),
            'enabled_patterns': len(enabled_patterns),
            'enabled_pattern_names': enabled_patterns,
            'output_formats': list(self.config.get('output_formats', {}).keys()),
            'conversion_rules': self.config.get('conversion_rules', {}),
            'config_source': self.config_path or 'default'
        } 