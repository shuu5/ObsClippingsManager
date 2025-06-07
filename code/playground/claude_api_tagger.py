#!/usr/bin/env python3
"""
Claude API を使った論文ファイルの tags 自動生成実験
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional
import anthropic
from anthropic import Anthropic

class PaperTagger:
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: Claude API key (環境変数ANTHROPIC_API_KEYがない場合に指定)
        """
        if api_key:
            self.client = Anthropic(api_key=api_key)
        else:
            # 環境変数から取得
            self.client = Anthropic()
    
    def extract_paper_content(self, file_path: Path) -> Dict[str, str]:
        """
        論文ファイルから必要な情報を抽出
        
        Args:
            file_path: 論文ファイルのパス
            
        Returns:
            Dict with title, abstract, content等
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAMLフロントマターを解析
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not frontmatter_match:
            raise ValueError("Invalid markdown format: No YAML frontmatter found")
        
        frontmatter = frontmatter_match.group(1)
        body_content = frontmatter_match.group(2)
        
        # titleを抽出
        title_match = re.search(r'^title:\s*"(.+?)"', frontmatter, re.MULTILINE)
        title = title_match.group(1) if title_match else "Unknown Title"
        
        # abstractを抽出（## Abstractセクション）
        abstract_match = re.search(r'## Abstract\n\n(.*?)\n\n##', body_content, re.DOTALL)
        abstract = abstract_match.group(1).strip() if abstract_match else ""
        
        return {
            'title': title,
            'abstract': abstract,
            'full_content': body_content,
            'frontmatter': frontmatter
        }
    
    def generate_tags(self, paper_info: Dict[str, str]) -> List[str]:
        """
        Claude APIを使ってtagsを生成
        
        Args:
            paper_info: extract_paper_content()で取得した論文情報
            
        Returns:
            生成されたtagsのリスト
        """
        prompt = f"""
以下の論文の内容を分析して、適切なtagsを生成してください。

## タイトル
{paper_info['title']}

## アブストラクト  
{paper_info['abstract']}

## 全文（最初の3000文字）
{paper_info['full_content'][:3000]}

## Tags生成ルール
- 関係のあるトピック、技術の詳細、遺伝子名など、その論文の内容を理解するうえで重要なtermを列挙する
- 英語で記載する
- スネークケースで記載する（半角スペースは使用しない）
- 遺伝子名はgene symbolで記載する（例：KRT13）
- 10-20個程度のtagsを生成する

以下の形式で回答してください：
```
single_cell_rna_sequencing
prostate_cancer
stem_cells
keratin_profiling
KRT13
KRT23
...
```

各tagは改行で区切って記載してください。前後に説明文は不要です。
"""

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # レスポンスからtagsを抽出
            content = response.content[0].text
            
            # ```で囲まれた部分を抽出
            code_block_match = re.search(r'```\n(.*?)\n```', content, re.DOTALL)
            if code_block_match:
                tags_text = code_block_match.group(1)
            else:
                tags_text = content
            
            # 改行で分割してtagsリストを作成
            tags = [tag.strip() for tag in tags_text.split('\n') if tag.strip()]
            
            return tags
            
        except Exception as e:
            print(f"Error generating tags: {e}")
            return []
    
    def update_paper_tags(self, file_path: Path, new_tags: List[str]) -> bool:
        """
        論文ファイルのtagsを更新
        
        Args:
            file_path: 論文ファイルのパス
            new_tags: 新しいtagsのリスト
            
        Returns:
            成功時True
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # YAMLフロントマターでtagsを更新
            tags_yaml = '\n'.join([f'- {tag}' for tag in new_tags])
            
            # 既存のtagsを置き換える
            if re.search(r'^tags:\s*$', content, re.MULTILINE):
                # 空のtagsがある場合
                content = re.sub(r'^tags:\s*$', f'tags:\n{tags_yaml}', content, flags=re.MULTILINE)
            elif re.search(r'^tags:\n.*?^---', content, re.MULTILINE | re.DOTALL):
                # 既存のtagsがある場合
                content = re.sub(r'^tags:\n.*?(?=^[a-zA-Z_]+:|^---)', f'tags:\n{tags_yaml}\n', content, flags=re.MULTILINE | re.DOTALL)
            else:
                # tagsが存在しない場合、YAMLフロントマターに追加
                frontmatter_end = content.find('---', 3)
                if frontmatter_end != -1:
                    insert_pos = frontmatter_end
                    content = content[:insert_pos] + f'tags:\n{tags_yaml}\n' + content[insert_pos:]
            
            # ファイルに書き戻し
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"Error updating tags: {e}")
            return False
    
    def process_single_paper(self, citation_key: str, clippings_dir: Path) -> bool:
        """
        単一の論文ファイルを処理
        
        Args:
            citation_key: 論文のcitation key
            clippings_dir: Clippingsディレクトリのパス
            
        Returns:
            成功時True
        """
        paper_dir = clippings_dir / citation_key
        paper_file = paper_dir / f"{citation_key}.md"
        
        if not paper_file.exists():
            print(f"Paper file not found: {paper_file}")
            return False
        
        print(f"Processing paper: {citation_key}")
        
        try:
            # 論文内容を抽出
            paper_info = self.extract_paper_content(paper_file)
            print(f"Title: {paper_info['title']}")
            
            # tagsを生成
            print("Generating tags...")
            tags = self.generate_tags(paper_info)
            print(f"Generated {len(tags)} tags: {tags[:5]}...")  # 最初の5個を表示
            
            # tagsを更新
            if tags:
                success = self.update_paper_tags(paper_file, tags)
                if success:
                    print(f"Tags updated successfully for {citation_key}")
                    return True
                else:
                    print(f"Failed to update tags for {citation_key}")
            else:
                print(f"No tags generated for {citation_key}")
            
        except Exception as e:
            print(f"Error processing {citation_key}: {e}")
        
        return False

def main():
    """メイン関数"""
    # 設定
    clippings_dir = Path("code/playground/Clippings")
    
    # API keyをチェック
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set your Claude API key as an environment variable:")
        print("export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # タガーを初期化
    tagger = PaperTagger()
    
    # 利用可能な論文をリスト
    if not clippings_dir.exists():
        print(f"Clippings directory not found: {clippings_dir}")
        return
    
    paper_dirs = [d for d in clippings_dir.iterdir() if d.is_dir()]
    print(f"Found {len(paper_dirs)} papers:")
    for i, paper_dir in enumerate(paper_dirs, 1):
        print(f"  {i}. {paper_dir.name}")
    
    # テスト実行: 最初の論文を処理
    if paper_dirs:
        test_paper = paper_dirs[0].name
        print(f"\nTesting with paper: {test_paper}")
        success = tagger.process_single_paper(test_paper, clippings_dir)
        if success:
            print("Test completed successfully!")
        else:
            print("Test failed!")

if __name__ == "__main__":
    main() 