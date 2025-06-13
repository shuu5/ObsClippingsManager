#!/usr/bin/env python3
"""
ObsClippingsManager v3.2.0 - Test Utilities

テスト環境の分離と共通機能を提供
- テスト環境ディレクトリ: /tmp/ObsClippingsManager_Test
- テストデータ管理
- 共通テストセットアップ・クリーンアップ
"""

import os
import shutil
import tempfile
from pathlib import Path
import yaml

class TestEnvironmentManager:
    """テスト環境の分離管理クラス"""
    
    TEST_DIR_BASE = "/tmp/ObsClippingsManager_Test"
    
    @classmethod
    def setup_test_environment(cls, test_name):
        """個別テスト用の分離環境を作成"""
        test_dir = Path(cls.TEST_DIR_BASE) / test_name
        
        # 既存ディレクトリの削除
        if test_dir.exists():
            shutil.rmtree(test_dir)
        
        # テストディレクトリ作成
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 基本ディレクトリ構造作成
        (test_dir / "Clippings").mkdir()
        (test_dir / "backups").mkdir()
        (test_dir / "logs").mkdir()
        
        return test_dir
    
    @classmethod
    def cleanup_test_environment(cls, test_dir=None):
        """テスト環境のクリーンアップ"""
        if test_dir:
            # 特定のテストディレクトリを削除
            if Path(test_dir).exists():
                shutil.rmtree(test_dir, ignore_errors=True)
        else:
            # 全テスト環境を削除
            if Path(cls.TEST_DIR_BASE).exists():
                shutil.rmtree(cls.TEST_DIR_BASE, ignore_errors=True)

class TestDataManager:
    """テストデータ管理クラス"""
    
    @staticmethod
    def create_test_bibtex(test_dir, entries=None):
        """テスト用BibTeXファイルを作成"""
        if entries is None:
            entries = [
                {
                    'ID': 'test2023',
                    'title': 'Test Paper Title',
                    'author': 'Test Author',
                    'year': '2023',
                    'journal': 'Test Journal'
                }
            ]
        
        bibtex_file = Path(test_dir) / "CurrentManuscript.bib"
        with open(bibtex_file, 'w', encoding='utf-8') as f:
            for entry in entries:
                f.write(f"@article{{{entry['ID']},\n")
                for key, value in entry.items():
                    if key != 'ID':
                        f.write(f"  {key} = {{{value}}},\n")
                f.write("}\n\n")
        
        return bibtex_file
    
    @staticmethod
    def create_test_markdown(test_dir, filename, yaml_header=None, content="Test content"):
        """テスト用Markdownファイルを作成"""
        if yaml_header is None:
            yaml_header = {
                'citation_key': 'test2023',
                'processing_status': {'organize': 'pending'},
                'workflow_version': '3.2'
            }
        
        markdown_file = Path(test_dir) / "Clippings" / f"{filename}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write("---\n")
            yaml.dump(yaml_header, f, default_flow_style=False, allow_unicode=True)
            f.write("---\n\n")
            f.write(content)
        
        return markdown_file
    
    @staticmethod
    def create_test_config(test_dir, custom_config=None):
        """テスト用設定ファイルを作成"""
        default_config = {
            'workspace_path': str(test_dir),
            'api_settings': {
                'request_delay': 0.1,  # テスト用に短縮
                'max_retries': 1,
                'timeout': 5
            },
            'logging': {
                'log_file': str(Path(test_dir) / "logs" / "test.log"),
                'log_level': "DEBUG"
            },
            'error_handling': {
                'enabled': True,
                'max_retry_attempts': 1
            },
            'backup_settings': {
                'enabled': True,
                'backup_location': str(Path(test_dir) / "backups")
            }
        }
        
        if custom_config:
            default_config.update(custom_config)
        
        config_file = Path(test_dir) / "config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
        
        return config_file

class BaseTestCase:
    """テスト基底クラス（Mixin）"""
    
    def setUp(self):
        """テスト前準備"""
        # テスト環境セットアップ
        self.test_dir = TestEnvironmentManager.setup_test_environment(
            self.__class__.__name__
        )
        
        # テスト用設定ファイル作成
        self.config_file = TestDataManager.create_test_config(self.test_dir)
    
    def tearDown(self):
        """テスト後クリーンアップ"""
        TestEnvironmentManager.cleanup_test_environment(self.test_dir)

# テストユーティリティ関数
def mock_api_response(status_code=200, json_data=None):
    """API レスポンスのモック作成"""
    class MockResponse:
        def __init__(self, status_code, json_data):
            self.status_code = status_code
            self._json_data = json_data or {}
        
        def json(self):
            return self._json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    return MockResponse(status_code, json_data)

def assert_yaml_header_exists(file_path, expected_keys=None):
    """Markdownファイルの YAMLヘッダー存在確認"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # YAMLヘッダーの存在確認
    if not content.startswith('---\n'):
        raise AssertionError("YAML header not found")
    
    # YAMLヘッダーの解析
    yaml_end = content.find('\n---\n', 4)
    if yaml_end == -1:
        raise AssertionError("YAML header end not found")
    
    yaml_content = content[4:yaml_end]
    try:
        yaml_data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise AssertionError(f"Invalid YAML: {e}")
    
    # 期待されるキーの確認
    if expected_keys:
        for key in expected_keys:
            if key not in yaml_data:
                raise AssertionError(f"Expected key '{key}' not found in YAML header")
    
    return yaml_data 