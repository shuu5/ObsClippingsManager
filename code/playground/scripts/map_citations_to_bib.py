#!/usr/bin/env python3
"""
引用番号とBibTeXファイルマッピングスクリプト

論文本文の引用番号（[1], [2]等）をreferences.bibファイル内の
文献エントリにcitation_numberプロパティとして追加する。
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

# 親ディレクトリのモジュールをインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from citation_normalizer.bib_citation_mapper import BibCitationMapper


class CitationBibMappingScript:
    """引用番号とBibTeXマッピングスクリプトクラス"""
    
    def __init__(self):
        self.mapper = BibCitationMapper()
        self.processed_papers = 0
        self.updated_papers = 0
        
    def map_citations_in_directory(self, directory_path: str, dry_run: bool = False, 
                                  backup: bool = False):
        """
        ディレクトリ内の論文の引用番号をマッピング
        
        Args:
            directory_path: 処理対象ディレクトリのパス
            dry_run: ドライランモード
            backup: バックアップを作成するかどうか
        """
        print("引用番号とBibTeXファイルマッピング処理を開始します...")
        print(f"対象ディレクトリ: {directory_path}")
        print(f"ドライラン: {'はい' if dry_run else 'いいえ'}")
        print(f"バックアップ: {'はい' if backup else 'いいえ'}")
        print("-" * 60)
        
        # ディレクトリが存在するかチェック
        if not os.path.exists(directory_path):
            print(f"エラー: ディレクトリ '{directory_path}' が見つかりません。")
            return
        
        # 各サブディレクトリを処理
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            
            if os.path.isdir(item_path):
                self._process_paper_directory(item_path, dry_run, backup)
        
        print("-" * 60)
        print(f"処理完了:")
        print(f"  処理論文数: {self.processed_papers}")
        print(f"  更新論文数: {self.updated_papers}")
        
        if dry_run:
            print("\nドライランモードでした。実際の変更は行われていません。")
            print("実際に変更するには --dry-run オプションを外して再実行してください。")
    
    def _process_paper_directory(self, paper_dir: str, dry_run: bool, backup: bool):
        """
        単一の論文ディレクトリを処理
        
        Args:
            paper_dir: 論文ディレクトリのパス
            dry_run: ドライランモード
            backup: バックアップフラグ
        """
        self.processed_papers += 1
        paper_name = os.path.basename(paper_dir)
        
        try:
            # 論文ディレクトリを処理
            result = self.mapper.process_paper_directory(paper_dir, dry_run, backup)
            
            print(f"\n📝 論文: {paper_name}")
            print(f"  📄 論文ファイル: {os.path.basename(result['paper_file'])}")
            print(f"  📚 BibTeXファイル: {os.path.basename(result['bib_file'])}")
            print(f"  🔢 検出された引用番号: {result['citations_found']}")
            print(f"  📖 BibTeXエントリ数: {result['bib_entries_count']}")
            print(f"  🔗 マッピング済みエントリ数: {result['updated_entries_count']}")
            
            if result['updated_entries_count'] > 0:
                self.updated_papers += 1
                
                if not dry_run and result['file_updated']:
                    print("  ✅ BibTeXファイルを更新しました")
                elif dry_run:
                    print("  🔍 ドライランモード - 変更は保存されていません")
            else:
                print("  ℹ️  引用番号が見つからないか、既にマッピング済みです")
                
        except Exception as e:
            print(f"❌ エラー: {paper_name} - {e}")
    
    def process_single_paper(self, paper_dir: str, dry_run: bool = False, 
                            backup: bool = False):
        """
        単一の論文を処理
        
        Args:
            paper_dir: 論文ディレクトリのパス
            dry_run: ドライランモード
            backup: バックアップを作成するかどうか
        """
        print("単一論文の引用番号マッピング処理を開始します...")
        print(f"対象論文: {paper_dir}")
        print(f"ドライラン: {'はい' if dry_run else 'いいえ'}")
        print(f"バックアップ: {'はい' if backup else 'いいえ'}")
        print("-" * 60)
        
        self._process_paper_directory(paper_dir, dry_run, backup)
        
        print("-" * 60)
        print("処理完了")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="引用番号とBibTeXファイルマッピングスクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/map_citations_to_bib.py --dry-run
  python scripts/map_citations_to_bib.py --backup
  python scripts/map_citations_to_bib.py --directory Clippings
  python scripts/map_citations_to_bib.py --paper-dir Clippings/takenakaW2023J.Radiat.Res.Tokyo
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
        '--paper-dir',
        help='単一の論文ディレクトリを指定'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='変更前のBibTeXファイルをバックアップ'
    )
    
    args = parser.parse_args()
    
    # スクリプトを実行
    script = CitationBibMappingScript()
    
    if args.paper_dir:
        # 単一論文の処理
        script.process_single_paper(
            paper_dir=args.paper_dir,
            dry_run=args.dry_run,
            backup=args.backup
        )
    else:
        # ディレクトリ全体の処理
        script.map_citations_in_directory(
            directory_path=args.directory,
            dry_run=args.dry_run,
            backup=args.backup
        )


if __name__ == '__main__':
    main() 