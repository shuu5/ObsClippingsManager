"""
統合ログシステム

ObsClippingsManager統合システムのログ機能を提供します。
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Dict, Any, Optional


class IntegratedLogger:
    """統合ログシステム"""
    
    def __init__(self, 
                 log_level: str = "INFO", 
                 log_file: Optional[str] = None,
                 console_output: bool = True):
        """
        Args:
            log_level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: ログファイルパス
            console_output: コンソール出力有無
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_file = log_file
        self.console_output = console_output
        self.loggers = {}
        
        # ルートロガーの設定
        self.root_logger = logging.getLogger("ObsClippingsManager")
        self.root_logger.setLevel(self.log_level)
        
        # 既存のハンドラをクリア
        self.root_logger.handlers.clear()
        
        # フォーマッタの設定
        self.formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self._setup_handlers()
        
    def _setup_handlers(self) -> None:
        """ハンドラーの設定"""
        # コンソールハンドラ
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(self.formatter)
            self.root_logger.addHandler(console_handler)
            
        # ファイルハンドラ
        if self.log_file:
            # ログディレクトリの作成
            log_dir = os.path.dirname(self.log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # ローテーションファイルハンドラ（10MB、5世代保持）
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(self.formatter)
            self.root_logger.addHandler(file_handler)
            
    def setup_loggers(self) -> None:
        """各機能用のロガーを設定"""
        # 各モジュール用のロガーを事前設定
        module_names = [
            "CitationFetcher",
            "CitationFetcher.CrossRef",
            "CitationFetcher.OpenCitations",
            "RenameMkDir",
            "RenameMkDir.FileMatcher",
            "RenameMkDir.DirectoryOrganizer",
            "SharedModules",
            "SharedModules.BibTeXParser",
            "SharedModules.ConfigManager",
            "Workflows",
            "Workflows.SyncCheck",
            "Main"
        ]
        
        for module_name in module_names:
            self.get_logger(module_name)
            
    def get_logger(self, module_name: str) -> logging.Logger:
        """モジュール専用ロガーを取得"""
        if module_name not in self.loggers:
            logger_name = f"ObsClippingsManager.{module_name}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(self.log_level)
            self.loggers[module_name] = logger
            
        return self.loggers[module_name]
        
    def log_operation_start(self, operation: str, details: Dict[str, Any] = None) -> None:
        """操作開始をログ"""
        logger = self.get_logger("Main")
        message = f"Operation started: {operation}"
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message = f"{message} ({detail_str})"
            
        logger.info(message)
        
    def log_operation_end(self, operation: str, success: bool, details: Dict[str, Any] = None) -> None:
        """操作終了をログ"""
        logger = self.get_logger("Main")
        status = "completed successfully" if success else "failed"
        message = f"Operation {operation} {status}"
        
        if details:
            detail_str = ", ".join([f"{k}={v}" for k, v in details.items()])
            message = f"{message} ({detail_str})"
            
        if success:
            logger.info(message)
        else:
            logger.error(message)
            
    def log_progress(self, module: str, current: int, total: int, message: str = "") -> None:
        """進捗状況をログ"""
        logger = self.get_logger(module)
        percentage = (current / total * 100) if total > 0 else 0
        progress_msg = f"Progress: {current}/{total} ({percentage:.1f}%)"
        
        if message:
            progress_msg = f"{progress_msg} - {message}"
            
        logger.info(progress_msg)
        
    def log_error_with_context(self, module: str, error: Exception, context: Dict[str, Any] = None) -> None:
        """コンテキスト付きでエラーをログ"""
        logger = self.get_logger(module)
        error_type = type(error).__name__
        error_msg = f"{error_type}: {str(error)}"
        
        if context:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            error_msg = f"{error_msg} (Context: {context_str})"
            
        logger.error(error_msg, exc_info=True)
        
    def log_statistics(self, module: str, stats: Dict[str, Any]) -> None:
        """統計情報をログ"""
        logger = self.get_logger(module)
        stats_lines = ["Statistics:"]
        
        for key, value in stats.items():
            stats_lines.append(f"  - {key}: {value}")
            
        logger.info("\n".join(stats_lines))
        
    def set_log_level(self, level: str) -> None:
        """ログレベルを動的に変更"""
        new_level = getattr(logging, level.upper(), logging.INFO)
        self.log_level = new_level
        
        # すべてのロガーとハンドラのレベルを更新
        self.root_logger.setLevel(new_level)
        for handler in self.root_logger.handlers:
            handler.setLevel(new_level)
            
        for logger in self.loggers.values():
            logger.setLevel(new_level)
            
    def close(self) -> None:
        """ログハンドラをクローズ"""
        for handler in self.root_logger.handlers:
            handler.close()
            self.root_logger.removeHandler(handler)


# シングルトンインスタンス
_logger_instance: Optional[IntegratedLogger] = None


def get_integrated_logger(log_level: str = "INFO", 
                        log_file: Optional[str] = None,
                        console_output: bool = True) -> IntegratedLogger:
    """統合ロガーのシングルトンインスタンスを取得"""
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = IntegratedLogger(log_level, log_file, console_output)
        _logger_instance.setup_loggers()
        
    return _logger_instance 