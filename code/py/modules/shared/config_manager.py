"""
統合設定管理モジュール

ObsClippingsManager統合システムの設定管理機能を提供します。
"""

import json
import os
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from .exceptions import ConfigError, ValidationError


# デフォルト設定
DEFAULT_INTEGRATED_CONFIG = {
    # 共通設定
    "common": {
        "bibtex_file": "/home/user/ManuscriptsManager/CurrentManuscript.bib",
        "clippings_dir": "/home/user/ManuscriptsManager/Clippings/",
        "output_dir": "/home/user/ManuscriptsManager/References/",
        "log_level": "INFO",
        "log_file": "obsclippings.log",
        "backup_enabled": True,
        "backup_dir": "/home/user/ManuscriptsManager/backups/",
        "dry_run": False
    },
    
    # Citation Fetcher設定
    "citation_fetcher": {
        "request_delay": 1.0,
        "max_retries": 3,
        "timeout": 30,
        "crossref_base_url": "https://api.crossref.org",
        "opencitations_endpoints": [
            "https://opencitations.net/index/api/v1",
            "https://w3id.org/oc/index/coci/api/v1"
        ],
        "user_agent": "ObsClippingsManager/2.0 (mailto:user@example.com)",
        "output_format": "bibtex",
        "max_references_per_paper": 1000,
        "enable_enrichment": True,
        "enrichment_field_type": "general",
        "enrichment_quality_threshold": 0.8,
        "enrichment_max_attempts": 3,
        "api_priorities": {
            "life_sciences": ["crossref", "opencitations", "openalex", "semantic_scholar", "pubmed"],
            "computer_science": ["crossref", "opencitations", "openalex", "semantic_scholar", "pubmed"],
            "general": ["crossref", "opencitations", "openalex", "semantic_scholar", "pubmed"]
        },
        "rate_limits": {
            "pubmed": 1.0,
            "semantic_scholar": 1.0,
            "openalex": 0.1,
            "opencitations": 0.5
        }
    },
    
    # Rename & MkDir設定
    "rename_mkdir": {
        "doi_matching_enabled": True,
        "title_fallback_enabled": True,
        "similarity_threshold": 0.8,
        "title_sync_enabled": True,
        "title_sync_prompt": True,
        "title_comparison_normalize": True,
        "auto_approve": False,
        "create_directories": True,
        "cleanup_empty_dirs": True,
        "max_filename_length": 255,
        "invalid_chars": r'[<>:"/\\|?*]',
        "case_sensitive_matching": False,
        "validate_doi_format": True,
        "require_yaml_frontmatter": False,
        "backup_suffix": ".backup"
    },
    
    # Sync Check設定
    "sync_check": {
        "show_missing_in_clippings": True,
        "show_missing_in_bib": True,
        "show_clickable_links": True,
        "show_doi_statistics": True,
        "max_displayed_files": 10,
        "sort_by_year": True,
        "doi_required_warning": True
    },
    
    # Citation Parser設定
    "citation_parser": {
        "default_pattern_type": "all",
        "default_output_format": "unified",
        "enable_link_extraction": False,
        "expand_ranges": True,
        "max_file_size_mb": 10,
        "output_encoding": "utf-8",
        "pattern_config_file": "modules/citation_parser/patterns.yaml",
        "processing_timeout": 60
    }
}

# バリデーションルール
VALIDATION_RULES = {
    "common": {
        "bibtex_file": {"required": True, "type": "file_path"},
        "clippings_dir": {"required": True, "type": "directory_path"},
        "log_level": {"required": False, "type": "choice", "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]}
    },
    "citation_fetcher": {
        "request_delay": {"required": False, "type": "float", "min": 0.1, "max": 10.0},
        "max_retries": {"required": False, "type": "int", "min": 1, "max": 10},
        "timeout": {"required": False, "type": "int", "min": 5, "max": 120},
        "enable_enrichment": {"required": False, "type": "bool"},
        "enrichment_field_type": {"required": False, "type": "choice", "choices": ["life_sciences", "computer_science", "general"]},
        "enrichment_quality_threshold": {"required": False, "type": "float", "min": 0.0, "max": 1.0},
        "enrichment_max_attempts": {"required": False, "type": "int", "min": 1, "max": 5}
    },
    "rename_mkdir": {
        "doi_matching_enabled": {"required": False, "type": "bool"},
        "title_fallback_enabled": {"required": False, "type": "bool"},
        "similarity_threshold": {"required": False, "type": "float", "min": 0.0, "max": 1.0},
        "title_sync_enabled": {"required": False, "type": "bool"},
        "title_sync_prompt": {"required": False, "type": "bool"},
        "title_comparison_normalize": {"required": False, "type": "bool"},
        "auto_approve": {"required": False, "type": "bool"},
        "create_directories": {"required": False, "type": "bool"},
        "cleanup_empty_dirs": {"required": False, "type": "bool"},
        "max_filename_length": {"required": False, "type": "int", "min": 50, "max": 255},
        "case_sensitive_matching": {"required": False, "type": "bool"},
        "validate_doi_format": {"required": False, "type": "bool"},
        "require_yaml_frontmatter": {"required": False, "type": "bool"}
    },
    "sync_check": {
        "show_missing_in_clippings": {"required": False, "type": "bool"},
        "show_missing_in_bib": {"required": False, "type": "bool"},
        "show_clickable_links": {"required": False, "type": "bool"},
        "show_doi_statistics": {"required": False, "type": "bool"},
        "max_displayed_files": {"required": False, "type": "int", "min": 1, "max": 100},
        "sort_by_year": {"required": False, "type": "bool"},
        "doi_required_warning": {"required": False, "type": "bool"}
    },
    
    "citation_parser": {
        "default_pattern_type": {"required": False, "type": "choice", "choices": ["basic", "advanced", "all"]},
        "default_output_format": {"required": False, "type": "choice", "choices": ["unified", "table", "json"]},
        "enable_link_extraction": {"required": False, "type": "bool"},
        "expand_ranges": {"required": False, "type": "bool"},
        "max_file_size_mb": {"required": False, "type": "int", "min": 1, "max": 100},
        "output_encoding": {"required": False, "type": "choice", "choices": ["utf-8", "ascii", "latin-1"]},
        "processing_timeout": {"required": False, "type": "int", "min": 10, "max": 300}
    }
}


class ConfigManager:
    """統合設定管理クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Args:
            config_file: 設定ファイルパス（指定なしでデフォルト設定）
        """
        self.config_file = config_file
        self.config = self._initialize_config()
        
    def _initialize_config(self) -> Dict[str, Any]:
        """設定を初期化"""
        if self.config_file and os.path.exists(self.config_file):
            return self.load_config()
        return DEFAULT_INTEGRATED_CONFIG.copy()
        
    def load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        if not self.config_file:
            return DEFAULT_INTEGRATED_CONFIG.copy()
            
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # デフォルト設定とマージ
            merged_config = self._merge_configs(DEFAULT_INTEGRATED_CONFIG, config)
            
            # バリデーション
            is_valid, errors = self.validate_config(merged_config)
            if not is_valid:
                raise ConfigError(f"Configuration validation failed: {', '.join(errors)}")
                
            return merged_config
            
        except (IOError, json.JSONDecodeError) as e:
            raise ConfigError(f"Failed to load config file: {e}")
            
    def save_config(self, config: Dict[str, Any] = None) -> bool:
        """設定を保存"""
        if not self.config_file:
            raise ConfigError("No config file path specified")
            
        config_to_save = config or self.config
        
        # バリデーション
        is_valid, errors = self.validate_config(config_to_save)
        if not is_valid:
            raise ConfigError(f"Configuration validation failed: {', '.join(errors)}")
            
        try:
            # ディレクトリが存在しない場合は作成
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=4, ensure_ascii=False)
                
            self.config = config_to_save
            return True
            
        except IOError as e:
            raise ConfigError(f"Failed to save config file: {e}")
            
    def get_citation_fetcher_config(self) -> Dict[str, Any]:
        """Citation Fetcher用設定を取得"""
        return {
            **self.config.get("citation_fetcher", {}),
            "bibtex_file": self.config["common"]["bibtex_file"],
            "output_dir": self.config["common"]["output_dir"],
            "dry_run": self.config["common"]["dry_run"]
        }
        
    def get_rename_mkdir_config(self) -> Dict[str, Any]:
        """Rename & MkDir用設定を取得"""
        return {
            **self.config.get("rename_mkdir", {}),
            "bibtex_file": self.config["common"]["bibtex_file"],
            "clippings_dir": self.config["common"]["clippings_dir"],
            "backup_enabled": self.config["common"]["backup_enabled"],
            "backup_dir": self.config["common"]["backup_dir"],
            "dry_run": self.config["common"]["dry_run"]
        }
        
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """設定の妥当性チェック"""
        errors = []
        
        for section, rules in VALIDATION_RULES.items():
            if section not in config:
                errors.append(f"Missing section: {section}")
                continue
                
            for field, rule in rules.items():
                if rule["required"] and field not in config[section]:
                    errors.append(f"Missing required field: {section}.{field}")
                    continue
                    
                if field in config[section]:
                    value = config[section][field]
                    
                    # 型チェック
                    if rule["type"] == "file_path":
                        if not isinstance(value, str):
                            errors.append(f"{section}.{field} must be a string")
                            
                    elif rule["type"] == "directory_path":
                        if not isinstance(value, str):
                            errors.append(f"{section}.{field} must be a string")
                            
                    elif rule["type"] == "choice":
                        if value not in rule["choices"]:
                            errors.append(f"{section}.{field} must be one of {rule['choices']}")
                            
                    elif rule["type"] == "float":
                        try:
                            float_value = float(value)
                            if "min" in rule and float_value < rule["min"]:
                                errors.append(f"{section}.{field} must be >= {rule['min']}")
                            if "max" in rule and float_value > rule["max"]:
                                errors.append(f"{section}.{field} must be <= {rule['max']}")
                        except (TypeError, ValueError):
                            errors.append(f"{section}.{field} must be a float")
                            
                    elif rule["type"] == "int":
                        try:
                            int_value = int(value)
                            if "min" in rule and int_value < rule["min"]:
                                errors.append(f"{section}.{field} must be >= {rule['min']}")
                            if "max" in rule and int_value > rule["max"]:
                                errors.append(f"{section}.{field} must be <= {rule['max']}")
                        except (TypeError, ValueError):
                            errors.append(f"{section}.{field} must be an integer")
                            
                    elif rule["type"] == "bool":
                        if not isinstance(value, bool):
                            errors.append(f"{section}.{field} must be a boolean")
                            
        return len(errors) == 0, errors
        
    def _merge_configs(self, default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
        """デフォルト設定とカスタム設定をマージ"""
        merged = default.copy()
        
        for key, value in custom.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
                
        return merged
        
    def get(self, key_path: str, default: Any = None) -> Any:
        """ドット記法でネストされた設定値を取得"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
        
    def set(self, key_path: str, value: Any) -> None:
        """ドット記法でネストされた設定値を設定"""
        keys = key_path.split('.')
        target = self.config
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
            
        target[keys[-1]] = value

    # API一貫性のためのエイリアスメソッド
    def get_config(self) -> Dict[str, Any]:
        """設定全体を取得 (プロパティのエイリアス)"""
        return self.config.copy()
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """設定値を取得 (getメソッドのエイリアス)"""
        return self.get(key_path, default)
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """設定を更新"""
        def update_nested(target_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
            for key, value in update_dict.items():
                if key in target_dict and isinstance(target_dict[key], dict) and isinstance(value, dict):
                    update_nested(target_dict[key], value)
                else:
                    target_dict[key] = value
        
        update_nested(self.config, updates)
    
    def get_common_config(self) -> Dict[str, Any]:
        """共通設定セクションを取得"""
        return self.config.get("common", {}).copy()
    
    def get_sync_check_config(self) -> Dict[str, Any]:
        """Sync Check用設定を取得"""
        return {
            **self.config.get("sync_check", {}),
            "bibtex_file": self.config["common"]["bibtex_file"],
            "clippings_dir": self.config["common"]["clippings_dir"],
            "dry_run": self.config["common"]["dry_run"]
        }
    
    def get_citation_parser_config(self) -> Dict[str, Any]:
        """Citation Parser用設定を取得"""
        return {
            **self.config.get("citation_parser", {}),
            "dry_run": self.config["common"]["dry_run"]
        }
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """すべての設定セクションを取得"""
        return {
            "common": self.get_common_config(),
            "citation_fetcher": self.get_citation_fetcher_config(),
            "rename_mkdir": self.get_rename_mkdir_config(),
            "sync_check": self.get_sync_check_config(),
            "citation_parser": self.get_citation_parser_config()
        } 