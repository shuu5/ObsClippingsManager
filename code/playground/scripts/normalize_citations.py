#!/usr/bin/env python3
"""
引用文献の統一処理スクリプト

使用方法:
    python code/scripts/normalize_citations.py [OPTIONS]

オプション:
    --dry-run: 実際には変更せず、変更内容のプレビューのみ表示
    --directory: 処理対象ディレクトリ（デフォルト: code/playground/Clippings）
    --backup: 変更前のファイルをバックアップ
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from citation_normalizer.citation_normalizer import CitationNormalizer


class CitationNormalizationScript:
    
    def __init__(self):
        self.normalizer = CitationNormalizer()
        self.changes_made = 0
        self.files_processed = 0
        
    def normalize_clippings(self, directory_path: str, dry_run: bool = False, backup: bool = False):
        """
        Clippingsディレクトリ内のMarkdownファイルの引用文献を統一する
        
        Args:
            directory_path: 処理対象ディレクトリのパス
            dry_run: Trueの場合、実際には変更せず変更内容のみ表示
            backup: Trueの場合、変更前のファイルをバックアップ
        """
        print(f"引用文献統一処理を開始します...")
        print(f"対象ディレクトリ: {directory_path}")
        print(f"ドライラン: {'はい' if dry_run else 'いいえ'}")
        print(f"バックアップ: {'はい' if backup else 'いいえ'}")
        print("-" * 60)
        
        # ディレクトリが存在するかチェック
        if not os.path.exists(directory_path):
            print(f"エラー: ディレクトリ '{directory_path}' が見つかりません。")
            return
        
        # Markdownファイルを検索して処理
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    self._process_file(file_path, dry_run, backup)
        
        print("-" * 60)
        print(f"処理完了:")
        print(f"  処理ファイル数: {self.files_processed}")
        print(f"  変更ファイル数: {self.changes_made}")
        
        if dry_run:
            print("\nドライランモードでした。実際の変更は行われていません。")
            print("実際に変更するには --dry-run オプションを外して再実行してください。")
    
    def _process_file(self, file_path: str, dry_run: bool, backup: bool):
        """
        単一ファイルを処理する
        
        Args:
            file_path: ファイルパス
            dry_run: ドライランモード
            backup: バックアップフラグ
        """
        self.files_processed += 1
        
        try:
            # ファイルを読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # 引用文献を統一
            normalized_content = self.normalizer.normalize_citations(original_content)
            
            # 変更があるかチェック
            if original_content != normalized_content:
                self.changes_made += 1
                relative_path = os.path.relpath(file_path, Path.cwd())
                
                print(f"\n📝 変更対象ファイル: {relative_path}")
                
                # 変更内容を表示
                self._show_changes(original_content, normalized_content)
                
                if not dry_run:
                    # バックアップを作成
                    if backup:
                        self._create_backup(file_path)
                    
                    # ファイルを更新
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(normalized_content)
                    
                    print("  ✅ ファイルを更新しました")
                else:
                    print("  🔍 ドライランモード - 変更は保存されていません")
        
        except Exception as e:
            print(f"❌ エラー: {file_path} - {e}")
    
    def _show_changes(self, original: str, normalized: str):
        """
        変更内容を表示する
        
        Args:
            original: 元のテキスト
            normalized: 統一後のテキスト
        """
        import re
        
        # 変更された引用を検出
        original_citations = set(re.findall(r'\[[0-9\-–—,\s]+\]', original))
        normalized_citations = set(re.findall(r'\[[0-9,\s]+\]', normalized))
        
        # 範囲表記の変更を表示
        range_pattern = re.compile(r'\[(\d+)[\-–—](\d+)\]')
        range_changes = []
        
        for citation in original_citations:
            if range_pattern.match(citation):
                # 対応する統一後の引用を探す
                match = range_pattern.match(citation)
                if match:
                    start, end = int(match.group(1)), int(match.group(2))
                    expected = f"[{','.join(map(str, range(start, end + 1)))}]"
                    if expected in normalized_citations:
                        range_changes.append((citation, expected))
        
        # 連続引用の統合を検出
        consecutive_pattern = re.compile(r'\[\d+\](?:\s*,\s*\[\d+\])+')
        consecutive_changes = []
        
        for match in consecutive_pattern.finditer(original):
            original_consecutive = match.group(0)
            # 数字を抽出
            numbers = re.findall(r'\[(\d+)\]', original_consecutive)
            if len(numbers) > 1:
                expected = f"[{','.join(numbers)}]"
                if expected in normalized_citations:
                    consecutive_changes.append((original_consecutive, expected))
        
        # 変更内容を表示
        if range_changes:
            print("  📊 範囲表記の展開:")
            for old, new in range_changes:
                print(f"    {old} → {new}")
        
        if consecutive_changes:
            print("  🔗 連続引用の統合:")
            for old, new in consecutive_changes:
                print(f"    {old} → {new}")
    
    def _create_backup(self, file_path: str):
        """
        ファイルのバックアップを作成する
        
        Args:
            file_path: バックアップ対象ファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup_{timestamp}"
        shutil.copy2(file_path, backup_path)
        print(f"  💾 バックアップ作成: {os.path.basename(backup_path)}")


def main():
    parser = argparse.ArgumentParser(
        description="引用文献の統一処理スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python code/scripts/normalize_citations.py --dry-run
  python code/scripts/normalize_citations.py --backup
  python code/scripts/normalize_citations.py --directory /path/to/clippings
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='実際には変更せず、変更内容のプレビューのみ表示'
    )
    
    parser.add_argument(
        '--directory',
        default='Clippings',
        help='処理対象ディレクトリ（デフォルト: Clippings）'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='変更前のファイルをバックアップ'
    )
    
    args = parser.parse_args()
    
    # スクリプトを実行
    script = CitationNormalizationScript()
    script.normalize_clippings(
        directory_path=args.directory,
        dry_run=args.dry_run,
        backup=args.backup
    )


if __name__ == '__main__':
    main() 