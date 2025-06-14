#!/usr/bin/env python3
"""
統合ログシステム (IntegratedLogger)

ObsClippingsManager全体で使用される統一ログシステム。
構造化ログ、レベル管理、ファイルローテーション、エラートラッキング機能を提供。
"""

import logging
import logging.handlers
import os
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
import time
from datetime import datetime

from .exceptions import ObsClippingsManagerError, ConfigurationError


class PerformanceContext:
    """パフォーマンス測定コンテキスト"""
    
    def __init__(self, operation_name: str, logger: logging.Logger):
        self.operation_name = operation_name
        self.logger = logger
        self.start_time = None
        self.metrics = {}
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metrics['duration'] = duration
        
        if exc_type is None:
            self.logger.info(
                f"Operation completed: {self.operation_name} "
                f"(duration: {duration:.3f}s, metrics: {self.metrics})"
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation_name} "
                f"(duration: {duration:.3f}s, error: {exc_val})"
            )
    
    def add_metric(self, key: str, value: Union[int, float, str]):
        """メトリクス追加"""
        self.metrics[key] = value


class IntegratedLogger:
    """統合ログシステム"""
    
    def __init__(self, config_manager, log_file: Optional[str] = None):
        """
        IntegratedLoggerの初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            log_file (str, optional): ログファイルパス
        """
        self.config_manager = config_manager
        self.loggers = {}
        self.handlers_configured = False
        
        # 設定取得
        config = config_manager.get_config()
        logging_config = config.get('logging', {})
        
        # ログファイルパス設定
        if log_file:
            self.log_file = Path(log_file)
        else:
            default_log_file = logging_config.get('log_file', 'logs/obsclippings.log')
            self.log_file = Path(default_log_file)
        
        # ログレベル設定
        self.log_level = logging_config.get('log_level', 'INFO')
        
        # ファイルローテーション設定
        self.max_file_size = self._parse_file_size(
            logging_config.get('max_file_size', '10MB')
        )
        self.backup_count = logging_config.get('backup_count', 5)
        
        # ログフォーマット設定
        self.log_format = logging_config.get(
            'format',
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        # 初期化
        self._setup_logging()
    
    def _parse_file_size(self, size_str: str) -> int:
        """ファイルサイズ文字列をバイト数に変換"""
        size_str = size_str.strip().upper()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # 数値のみの場合はバイト数として扱う
            return int(size_str)
    
    def _setup_logging(self):
        """ログ設定の初期化"""
        # ログディレクトリ作成
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        
        # 既存のハンドラーをクリア（テスト時の重複を避ける）
        if not self.handlers_configured:
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
        
        # ログレベル設定
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)
        
        # フォーマッター作成
        formatter = logging.Formatter(self.log_format)
        
        # ファイルハンドラー（ローテーション機能付き）
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
        
        self.handlers_configured = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        モジュール別ロガーの取得
        
        Args:
            name (str): モジュール名
            
        Returns:
            logging.Logger: ロガーオブジェクト
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]
    
    def log_structured(self, level: str, message: str, module_name: str, 
                      extra_data: Optional[Dict[str, Any]] = None):
        """
        構造化ログ出力
        
        Args:
            level (str): ログレベル ('debug', 'info', 'warning', 'error')
            message (str): ログメッセージ
            module_name (str): モジュール名
            extra_data (dict, optional): 追加データ
        """
        logger = self.get_logger(module_name)
        
        # 構造化データの準備
        structured_message = message
        if extra_data:
            structured_data = json.dumps(extra_data, ensure_ascii=False, separators=(',', ':'))
            structured_message = f"{message} | data: {structured_data}"
        
        # ログレベルに応じて出力
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(structured_message)
    
    def log_error_with_traceback(self, message: str, module_name: str, 
                               exception: Optional[Exception] = None):
        """
        エラートラッキング機能付きログ出力
        
        Args:
            message (str): エラーメッセージ
            module_name (str): モジュール名
            exception (Exception, optional): 例外オブジェクト
        """
        logger = self.get_logger(module_name)
        
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'module': module_name,
            'message': message
        }
        
        if exception:
            error_info.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'traceback': traceback.format_exc()
            })
        
        # エラーログ出力
        logger.error(f"{message}")
        
        # トレースバック情報があれば詳細出力
        if exception:
            logger.error(f"Exception details: {type(exception).__name__}: {exception}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    @contextmanager
    def performance_context(self, operation_name: str, module_name: str):
        """
        パフォーマンス測定コンテキスト
        
        Args:
            operation_name (str): 操作名
            module_name (str): モジュール名
        
        Yields:
            PerformanceContext: パフォーマンス測定コンテキスト
        """
        logger = self.get_logger(module_name)
        context = PerformanceContext(operation_name, logger)
        
        # 開始処理
        context.__enter__()
        
        try:
            yield context
        except Exception as exc:
            # 例外発生時の終了処理
            context.__exit__(type(exc), exc, exc.__traceback__)
            raise
        else:
            # 正常終了時の終了処理
            context.__exit__(None, None, None)
    
    def set_level(self, level: str):
        """
        ログレベル動的変更
        
        Args:
            level (str): ログレベル ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # ルートロガーのレベル変更
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        # 全ハンドラーのレベル変更
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        
        self.log_level = level.upper()
        
        # 変更を記録
        root_logger.info(f"Log level changed to: {level.upper()}")
    
    def get_log_file_path(self) -> Path:
        """ログファイルパスの取得"""
        return self.log_file
    
    def get_current_log_level(self) -> str:
        """現在のログレベルの取得"""
        return self.log_level
    
    def cleanup(self):
        """ロガーのクリーンアップ"""
        root_logger = logging.getLogger()
        
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        self.loggers.clear()
        self.handlers_configured = False 