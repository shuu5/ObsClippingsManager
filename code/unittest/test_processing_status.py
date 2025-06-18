#!/usr/bin/env python3
"""
ProcessingStatus - Test Suite

ProcessingStatus Enumクラスのテストスイート。
状態値管理、文字列変換機能をテスト。
"""

import unittest
import sys
import os

# テスト対象モジュールのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from code.py.modules.status_management_yaml.processing_status import ProcessingStatus
from code.py.modules.shared_modules.exceptions import ValidationError


class TestProcessingStatus(unittest.TestCase):
    """ProcessingStatus Enumクラスのテスト"""
    
    def test_processing_status_import(self):
        """ProcessingStatusクラスのインポートテスト"""
        self.assertTrue(hasattr(ProcessingStatus, 'PENDING'))
        self.assertTrue(hasattr(ProcessingStatus, 'COMPLETED'))
        self.assertTrue(hasattr(ProcessingStatus, 'FAILED'))
    
    def test_status_values(self):
        """ステータス値の定義テスト"""
        self.assertEqual(ProcessingStatus.PENDING.value, "pending")
        self.assertEqual(ProcessingStatus.COMPLETED.value, "completed")
        self.assertEqual(ProcessingStatus.FAILED.value, "failed")
    
    def test_from_string_valid_values(self):
        """有効な文字列からProcessingStatusへの変換テスト"""
        self.assertEqual(ProcessingStatus.from_string("pending"), ProcessingStatus.PENDING)
        self.assertEqual(ProcessingStatus.from_string("completed"), ProcessingStatus.COMPLETED)
        self.assertEqual(ProcessingStatus.from_string("failed"), ProcessingStatus.FAILED)
    
    def test_from_string_invalid_value(self):
        """無効な文字列の場合はPENDINGを返すテスト"""
        self.assertEqual(ProcessingStatus.from_string("invalid"), ProcessingStatus.PENDING)
        self.assertEqual(ProcessingStatus.from_string(""), ProcessingStatus.PENDING)
        self.assertEqual(ProcessingStatus.from_string(None), ProcessingStatus.PENDING)
    
    def test_to_string_conversion(self):
        """ProcessingStatusから文字列への変換テスト"""
        self.assertEqual(ProcessingStatus.PENDING.to_string(), "pending")
        self.assertEqual(ProcessingStatus.COMPLETED.to_string(), "completed")
        self.assertEqual(ProcessingStatus.FAILED.to_string(), "failed")
    
    def test_string_representation(self):
        """文字列表現テスト"""
        self.assertEqual(str(ProcessingStatus.PENDING), "ProcessingStatus.PENDING")
        self.assertEqual(repr(ProcessingStatus.COMPLETED), "<ProcessingStatus.COMPLETED: 'completed'>")
    
    def test_equality_comparison(self):
        """等価性比較テスト"""
        status1 = ProcessingStatus.from_string("completed")
        status2 = ProcessingStatus.COMPLETED
        self.assertEqual(status1, status2)
        
        status3 = ProcessingStatus.from_string("pending")
        self.assertNotEqual(status1, status3)
    
    def test_iteration_over_statuses(self):
        """ステータス値の反復処理テスト"""
        statuses = list(ProcessingStatus)
        self.assertEqual(len(statuses), 3)
        self.assertIn(ProcessingStatus.PENDING, statuses)
        self.assertIn(ProcessingStatus.COMPLETED, statuses)
        self.assertIn(ProcessingStatus.FAILED, statuses)


if __name__ == '__main__':
    unittest.main() 