#!/usr/bin/env python3
"""
TestManuscripts環境構築スクリプト

本番環境(/home/user/ManuscriptsManager)からテストデータをコピーし、
テスト用の初期状態を作成・管理します。

**重要**: 本番データのみを使用し、サンプルデータは一切作成しません。
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
import argparse

def setup_test_environment(source_dir: str = "/home/user/ManuscriptsManager", 
                          test_dir: str = "/home/user/proj/ObsClippingsManager/TestManuscripts"):
    """
    テスト環境をセットアップ（本番データのみ使用）
    
    Args:
        source_dir: 本番環境のパス
        test_dir: テスト環境のパス
    """
    source_path = Path(source_dir)
    test_path = Path(test_dir)
    
    print(f"🚀 Setting up test environment...")
    print(f"   Source: {source_path}")
    print(f"   Target: {test_path}")
    
    # 1. 本番ディレクトリの存在確認
    if not source_path.exists():
        print(f"❌ ERROR: Source directory not found: {source_path}")
        print(f"   Test environment requires actual production data.")
        return False
    
    # 2. 必須ファイルの確認
    source_bib = source_path / "CurrentManuscript.bib"
    source_clippings = source_path / "Clippings"
    
    if not source_bib.exists():
        print(f"❌ ERROR: BibTeX file not found: {source_bib}")
        print(f"   Test environment requires actual production BibTeX file.")
        return False
        
    if not source_clippings.exists():
        print(f"❌ ERROR: Clippings directory not found: {source_clippings}")
        print(f"   Test environment requires actual production Clippings directory.")
        return False
    
    # 3. テストディレクトリの準備
    if test_path.exists():
        print(f"⚠️  Test directory already exists: {test_path}")
        response = input("   Remove existing directory? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree(test_path)
            print(f"   Removed existing directory")
        else:
            print(f"   Keeping existing directory")
            return False
    
    test_path.mkdir(parents=True, exist_ok=True)
    
    # 4. 本番データの完全コピー
    target_bib = test_path / "CurrentManuscript.bib"
    target_clippings = test_path / "Clippings"
    
    # BibTeXファイルのコピー
    shutil.copy2(source_bib, target_bib)
    print(f"✅ Copied BibTeX file: {target_bib}")
    
    # Clippingsディレクトリのコピー
    shutil.copytree(source_clippings, target_clippings)
    print(f"✅ Copied Clippings directory: {target_clippings}")
    
    # 5. ファイル数の確認
    bib_entries = count_bibtex_entries(target_bib)
    md_files = count_markdown_files(target_clippings)
    
    print(f"📊 Test data summary:")
    print(f"   BibTeX entries: {bib_entries}")
    print(f"   Markdown files: {md_files}")
    
    # 6. テスト環境情報ファイルの作成
    backup_info = test_path / ".test_env_info.txt"
    with open(backup_info, 'w', encoding='utf-8') as f:
        f.write(f"Test Environment Setup Information\n")
        f.write(f"==================================\n")
        f.write(f"Setup Date: {datetime.now().isoformat()}\n")
        f.write(f"Source Directory: {source_path}\n")
        f.write(f"Test Directory: {test_path}\n")
        f.write(f"BibTeX File: {target_bib}\n")
        f.write(f"Clippings Directory: {target_clippings}\n")
        f.write(f"BibTeX Entries: {bib_entries}\n")
        f.write(f"Markdown Files: {md_files}\n")
        f.write(f"\n")
        f.write(f"Reset Command:\n")
        f.write(f"python code/scripts/setup_test_env.py --reset\n")
    
    print(f"✅ Created test environment info: {backup_info}")
    print(f"")
    print(f"🎉 Test environment setup completed!")
    print(f"")
    print(f"Ready for testing with:")
    print(f"  PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace {test_path}")
    
    return True

def count_bibtex_entries(bib_file: Path) -> int:
    """BibTeXエントリ数をカウント"""
    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return content.count('@article{') + content.count('@book{') + content.count('@inproceedings{')
    except Exception:
        return 0

def count_markdown_files(clippings_dir: Path) -> int:
    """Markdownファイル数をカウント"""
    try:
        return len(list(clippings_dir.glob("*.md")))
    except Exception:
        return 0

def reset_test_environment(test_dir: str = "/home/user/proj/ObsClippingsManager/TestManuscripts"):
    """
    テスト環境を初期状態にリセット（本番データを使用）
    """
    test_path = Path(test_dir)
    
    if not test_path.exists():
        print(f"❌ Test environment not found: {test_path}")
        return False
    
    # バックアップ情報の確認
    backup_info = test_path / ".test_env_info.txt"
    source_dir = "/home/user/ManuscriptsManager"
    
    if backup_info.exists():
        print(f"📋 Found test environment info:")
        with open(backup_info, 'r', encoding='utf-8') as f:
            print(f"   {f.read()}")
    
    print(f"🔄 Resetting test environment...")
    
    # 処理済みファイル・ディレクトリの削除
    clippings_dir = test_path / "Clippings"
    if clippings_dir.exists():
        # Citation keyディレクトリの削除（整理処理により作成されたもの）
        for item in clippings_dir.iterdir():
            if item.is_dir():
                print(f"   Removing citation key directory: {item.name}")
                shutil.rmtree(item)
        
        # 本番データからの復元
        source_clippings = Path(source_dir) / "Clippings"
        if source_clippings.exists():
            # 既存ファイルを削除
            for item in clippings_dir.iterdir():
                if item.is_file():
                    item.unlink()
            
            # 本番データをコピー
            for item in source_clippings.iterdir():
                if item.is_file():
                    shutil.copy2(item, clippings_dir / item.name)
            
            print(f"✅ Reset Clippings directory to initial state")
        else:
            print(f"❌ ERROR: Source Clippings directory not found: {source_clippings}")
            return False
    
    # BibTeXファイルも本番データで復元
    bibtex_file = test_path / "CurrentManuscript.bib"
    source_bib = Path(source_dir) / "CurrentManuscript.bib"
    
    if source_bib.exists():
        shutil.copy2(source_bib, bibtex_file)
        print(f"✅ Reset BibTeX file to initial state")
    else:
        print(f"❌ ERROR: Source BibTeX file not found: {source_bib}")
        return False
    
    print(f"")
    print(f"🎉 Test environment reset completed!")
    print(f"")
    print(f"Ready for testing with:")
    print(f"  PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace {test_path}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Test environment setup and management")
    parser.add_argument('--reset', action='store_true', help='Reset test environment to initial state')
    parser.add_argument('--source', default="/home/user/ManuscriptsManager", 
                       help='Source directory (default: /home/user/ManuscriptsManager)')
    parser.add_argument('--test-dir', default="/home/user/proj/ObsClippingsManager/TestManuscripts",
                       help='Test directory (default: ./TestManuscripts)')
    
    args = parser.parse_args()
    
    try:
        if args.reset:
            success = reset_test_environment(args.test_dir)
        else:
            success = setup_test_environment(args.source, args.test_dir)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 