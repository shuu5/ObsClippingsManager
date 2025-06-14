#!/usr/bin/env python3
"""
ProcessingStatus

処理状態を管理するEnumクラス。
状態値の統一管理と文字列変換機能を提供。
"""

from enum import Enum
from typing import Optional, Union


class ProcessingStatus(Enum):
    """
    処理状態Enum
    
    各処理ステップの状態を管理。
    pending: 処理が必要（初期状態・失敗後）
    completed: 処理完了
    failed: 処理失敗（次回再処理対象）
    """
    
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @classmethod
    def from_string(cls, status: Optional[Union[str, None]]) -> 'ProcessingStatus':
        """
        文字列からProcessingStatusへ変換
        
        Args:
            status: 変換対象の文字列
            
        Returns:
            ProcessingStatus: 対応するステータス。無効な場合はPENDING
        """
        if status is None:
            return cls.PENDING
            
        if not isinstance(status, str):
            return cls.PENDING
            
        try:
            return cls(status)
        except ValueError:
            return cls.PENDING
    
    def to_string(self) -> str:
        """
        ProcessingStatusから文字列へ変換
        
        Returns:
            str: ステータス文字列
        """
        return self.value 