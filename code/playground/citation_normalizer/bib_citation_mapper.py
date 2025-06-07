"""
BibTeX引用文献マッピング機能

引用番号（[1], [2]等）をreferences.bibファイル内の文献エントリに
citation_numberプロパティとして追加する機能を提供する。
"""

import re
import os
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class BibCitationMapper:
    """引用番号とBibTeX文献エントリをマッピングするクラス"""
    
    def __init__(self):
        # 引用パターンの正規表現（通常の数字と脚注形式）
        self.citation_pattern = re.compile(r'\[(\^?\d+)\]')
        # BibTeX エントリのパターン
        self.bib_entry_pattern = re.compile(r'^@(\w+)\{([^,]+),\s*$', re.MULTILINE)
        
    def extract_citations_from_text(self, text: str) -> List[int]:
        """
        テキストから引用番号を抽出し、ソートされたリストを返す
        
        Args:
            text: 論文本文のテキスト
            
        Returns:
            List[int]: ソートされた引用番号のリスト
        """
        citations = set()
        
        # 引用統一処理後の形式も考慮（[1,2,3]のようなカンマ区切り）
        comma_separated_pattern = re.compile(r'\[([^\[\]]+)\]')
        
        for match in comma_separated_pattern.finditer(text):
            content = match.group(1)
            
            # カンマ区切りの場合
            if ',' in content:
                for item in content.split(','):
                    item = item.strip()
                    if item.startswith('^'):
                        citations.add(int(item[1:]))
                    elif item.isdigit():
                        citations.add(int(item))
            else:
                # 単一の引用番号
                if content.startswith('^'):
                    citations.add(int(content[1:]))
                elif content.isdigit():
                    citations.add(int(content))
        
        return sorted(list(citations))
    
    def parse_bib_file(self, bib_file_path: str) -> List[Dict[str, str]]:
        """
        BibTeXファイルを解析してエントリのリストを返す
        
        Args:
            bib_file_path: BibTeXファイルのパス
            
        Returns:
            List[Dict[str, str]]: BibTeXエントリの辞書のリスト
        """
        try:
            with open(bib_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"BibTeXファイルの読み込みエラー: {e}")
        
        entries = []
        current_entry = None
        current_content = []
        brace_count = 0
        in_entry = False
        
        for line in content.split('\n'):
            line = line.strip()
            
            # コメント行は無視
            if line.startswith('%') or not line:
                continue
            
            # エントリの開始を検出
            if line.startswith('@'):
                if current_entry is not None:
                    # 前のエントリを保存
                    entries.append({
                        'raw_content': '\n'.join(current_content),
                        'entry_type': current_entry['entry_type'],
                        'entry_key': current_entry['entry_key']
                    })
                
                # 新しいエントリを開始
                match = re.match(r'^@(\w+)\{([^,]+),?\s*$', line)
                if match:
                    current_entry = {
                        'entry_type': match.group(1),
                        'entry_key': match.group(2)
                    }
                    current_content = [line]
                    brace_count = 1
                    in_entry = True
                continue
            
            if in_entry:
                current_content.append(line)
                
                # 中括弧の数を数える
                brace_count += line.count('{') - line.count('}')
                
                # エントリの終了を検出
                if brace_count == 0:
                    entries.append({
                        'raw_content': '\n'.join(current_content),
                        'entry_type': current_entry['entry_type'],
                        'entry_key': current_entry['entry_key']
                    })
                    current_entry = None
                    current_content = []
                    in_entry = False
        
        # 最後のエントリを処理
        if current_entry is not None:
            entries.append({
                'raw_content': '\n'.join(current_content),
                'entry_type': current_entry['entry_type'],
                'entry_key': current_entry['entry_key']
            })
        
        return entries
    
    def add_citation_numbers_to_bib(self, bib_entries: List[Dict[str, str]], 
                                   citations: List[int]) -> List[Dict[str, str]]:
        """
        BibTeXエントリにcitation_numberプロパティを追加
        
        Args:
            bib_entries: BibTeXエントリのリスト
            citations: 引用番号のリスト
            
        Returns:
            List[Dict[str, str]]: citation_number追加後のエントリリスト
        """
        updated_entries = []
        
        for i, entry in enumerate(bib_entries):
            # 対応する引用番号を取得
            citation_number = None
            if i < len(citations):
                citation_number = citations[i]
            
            # エントリの内容を更新
            updated_entry = entry.copy()
            
            if citation_number is not None:
                # citation_numberプロパティを追加
                raw_content = entry['raw_content']
                
                # 最後の行（閉じ括弧）の前にcitation_numberを挿入
                lines = raw_content.split('\n')
                
                # 既存のcitation_numberを検索して削除
                filtered_lines = []
                for line in lines:
                    if not re.match(r'^\s*citation_number\s*=', line):
                        filtered_lines.append(line)
                
                # 最後のフィールドにカンマを追加し、citation_numberを挿入
                if filtered_lines and filtered_lines[-1].strip() == '}':
                    # 最後から2番目の行（最後のフィールド）を確認
                    if len(filtered_lines) >= 2:
                        last_field_line = filtered_lines[-2]
                        # 最後のフィールドがカンマで終わっていない場合は追加
                        if not last_field_line.rstrip().endswith(','):
                            filtered_lines[-2] = last_field_line.rstrip() + ','
                    
                    # citation_numberを追加（適切なインデント付き）
                    citation_line = f"citation_number = {{{citation_number}}}"
                    filtered_lines.insert(-1, citation_line)
                
                updated_entry['raw_content'] = '\n'.join(filtered_lines)
                updated_entry['citation_number'] = citation_number
            
            updated_entries.append(updated_entry)
        
        return updated_entries
    
    def save_updated_bib_file(self, bib_file_path: str, updated_entries: List[Dict[str, str]], 
                             backup: bool = True) -> None:
        """
        更新されたBibTeXエントリをファイルに保存
        
        Args:
            bib_file_path: BibTeXファイルのパス
            updated_entries: 更新されたエントリのリスト
            backup: バックアップを作成するかどうか
        """
        # バックアップを作成
        if backup:
            backup_path = f"{bib_file_path}.backup"
            import shutil
            shutil.copy2(bib_file_path, backup_path)
            print(f"  💾 バックアップ作成: {os.path.basename(backup_path)}")
        
        # 元のファイルのヘッダーコメントを保持
        try:
            with open(bib_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # ヘッダーコメントを抽出
            header_lines = []
            for line in original_content.split('\n'):
                if line.strip().startswith('%'):
                    header_lines.append(line)
                elif not line.strip():
                    header_lines.append(line)
                else:
                    break
            
            # 新しいファイル内容を構築
            new_content = []
            
            # ヘッダーコメントを追加
            if header_lines:
                new_content.extend(header_lines)
                new_content.append('')  # 空行
            
            # 更新されたエントリを追加
            for entry in updated_entries:
                new_content.append(entry['raw_content'])
                new_content.append('')  # エントリ間の空行
            
            # ファイルに書き込み
            with open(bib_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_content))
                
        except Exception as e:
            raise Exception(f"BibTeXファイルの保存エラー: {e}")
    
    def process_paper_directory(self, paper_dir: str, dry_run: bool = False, 
                               backup: bool = True) -> Dict[str, any]:
        """
        論文ディレクトリを処理して引用番号をマッピング
        
        Args:
            paper_dir: 論文ディレクトリのパス
            dry_run: ドライランモード
            backup: バックアップを作成するかどうか
            
        Returns:
            Dict[str, any]: 処理結果の辞書
        """
        paper_path = Path(paper_dir)
        
        # MDファイルとBibファイルを検索
        md_files = list(paper_path.glob('*.md'))
        bib_files = list(paper_path.glob('references.bib'))
        
        if not md_files:
            raise Exception(f"Markdownファイルが見つかりません: {paper_dir}")
        
        if not bib_files:
            raise Exception(f"references.bibファイルが見つかりません: {paper_dir}")
        
        md_file = md_files[0]  # 最初のMDファイルを使用
        bib_file = bib_files[0]
        
        # 論文本文から引用番号を抽出
        with open(md_file, 'r', encoding='utf-8') as f:
            paper_content = f.read()
        
        citations = self.extract_citations_from_text(paper_content)
        
        # BibTeXファイルを解析
        bib_entries = self.parse_bib_file(str(bib_file))
        
        # citation_numberを追加
        updated_entries = self.add_citation_numbers_to_bib(bib_entries, citations)
        
        result = {
            'paper_file': str(md_file),
            'bib_file': str(bib_file),
            'citations_found': citations,
            'bib_entries_count': len(bib_entries),
            'updated_entries_count': sum(1 for e in updated_entries if 'citation_number' in e)
        }
        
        if not dry_run:
            # ファイルを更新
            self.save_updated_bib_file(str(bib_file), updated_entries, backup)
            result['file_updated'] = True
        else:
            result['file_updated'] = False
        
        return result 