# 論文セクション分割機能仕様書 v3.2

## 概要
Markdownファイルの見出し構造（##, ###, ####）を解析し、学術論文の標準的なセクション（Abstract, Introduction, Methods, Results, Discussion等）を自動識別・分割する機能。AI処理機能の精度向上のため、論文の構造情報をYAMLヘッダーに永続化します。

## 主要機能
- **見出し構造解析**: ##, ###, #### レベルでの階層的セクション分割
- **セクション分類**: 学術論文の標準構造パターンによる自動分類
- **構造情報記録**: YAMLヘッダーへのセクション情報永続化
- **他機能連携**: AI tagging/translation機能の精度向上支援

## データ構造

### Section
```python
@dataclass
class Section:
    title: str                 # セクションタイトル 
    level: int                # 見出しレベル (2=##, 3=###, 4=####)
    content: str              # セクション本文
    start_line: int           # 開始行番号
    end_line: int            # 終了行番号
    word_count: int          # 文字数
    subsections: List['Section']  # 子セクション
    section_type: str        # abstract, introduction, results等
```

### PaperStructure
```python
@dataclass  
class PaperStructure:
    sections: List[Section]   # トップレベルセクション
    total_sections: int      # 総セクション数
    section_types_found: List[str]  # 発見されたセクションタイプ
    parsed_at: str           # 解析日時
```

## YAMLヘッダー形式

```yaml
---
citation_key: smith2023test
paper_structure:
  parsed_at: '2025-01-15T10:30:00.123456'
  total_sections: 5
  sections:
    - title: "Abstract" 
      level: 2
      section_type: "abstract"
      start_line: 15
      end_line: 25
      word_count: 250
    - title: "Introduction"
      level: 2  
      section_type: "introduction"
      start_line: 27
      end_line: 85
      word_count: 1200
      subsections:
        - title: "Background"
          level: 3
          start_line: 30
          end_line: 50
          word_count: 400
    - title: "Methods"
      level: 2
      section_type: "methods" 
      start_line: 87
      end_line: 140
      word_count: 1500
    - title: "Results"
      level: 2
      section_type: "results" 
      start_line: 142
      end_line: 200
      word_count: 2100
    - title: "Discussion"
      level: 2
      section_type: "discussion" 
      start_line: 202
      end_line: 250
      word_count: 1800
  section_types_found: ["abstract", "introduction", "methods", "results", "discussion"]
processing_status:
  section_parsing: completed
workflow_version: '3.2'
---
```

## 実装クラス

### SectionParserWorkflow
```python
class SectionParserWorkflow:
    """論文セクション解析ワークフロー"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('SectionParserWorkflow')
        
    def process_papers(self, clippings_dir: str, target_papers: List[str] = None) -> Dict[str, Any]:
        """論文の一括セクション解析処理"""
        
    def parse_paper_structure(self, paper_path: str) -> PaperStructure:
        """単一論文の構造解析"""
        
    def extract_sections_by_heading(self, content: str) -> List[Section]:
        """見出しレベルによるセクション分割"""
        
    def identify_section_types(self, sections: List[Section]) -> None:
        """セクションタイプの自動識別（セクションオブジェクトを直接更新）"""
        
    def update_yaml_with_structure(self, paper_path: str, structure: PaperStructure) -> bool:
        """YAMLヘッダーにセクション情報を記録"""
```

## セクション識別ルール

### 標準パターン
```python
SECTION_TYPE_PATTERNS = {
    'abstract': ['abstract', 'summary'],
    'introduction': ['introduction', 'intro', 'background'],
    'methods': ['methods', 'methodology', 'materials and methods', 'experimental'],
    'results': ['results', 'findings'],
    'discussion': ['discussion', 'discussion and conclusions'],
    'conclusion': ['conclusion', 'conclusions', 'summary and conclusions'],
    'references': ['references', 'bibliography', 'citations'],
    'acknowledgments': ['acknowledgments', 'acknowledgements', 'thanks']
}
```

### 識別アルゴリズム
1. **見出しレベル検出**: ##, ###, #### の階層構造を解析
2. **タイトル正規化**: 小文字変換・記号除去による前処理
3. **パターンマッチング**: 標準パターンとの部分一致判定
4. **階層構造保持**: 親子関係を維持したツリー構造構築

## 設定項目

```yaml
section_parsing:
  min_section_words: 50          # 最小セクション文字数
  max_heading_level: 4           # 最大見出しレベル (####まで)
  enable_subsection_analysis: true
  section_type_detection: true
```

## エラーハンドリング

- **構造なし論文**: 見出しがない場合は全文を単一セクションとして処理
- **短すぎるセクション**: 最小文字数未満のセクションをスキップ
- **不明セクション**: パターンマッチしないセクションは"unknown"として記録
- **エンコーディングエラー**: UTF-8変換エラーの適切な処理

## 他機能との連携

### AI Tagging機能
- Introduction + Results + Discussionセクションを抽出してタグ生成に使用
- セクション情報により論文の重要部分を正確に特定

### Abstract Translation機能  
- Abstractセクションを正確に抽出して翻訳精度を向上
- セクション境界の明確化により翻訳対象範囲を限定

## 使用例

### 基本実行
```bash
# 単独実行
PYTHONPATH=code/py uv run python code/py/main.py section-parsing

# 統合ワークフローでの実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-section-parsing
```

### セクション情報の取得
```python
def get_section_by_type(paper_path: str, section_type: str) -> Optional[Section]:
    """指定タイプのセクションを取得"""
    with open(paper_path, 'r') as f:
        content = f.read()
        yaml_header = yaml.safe_load(content.split('---')[1])
        
    for section in yaml_header['paper_structure']['sections']:
        if section['section_type'] == section_type:
            return section
    return None
```

---

**論文セクション分割機能仕様書バージョン**: 3.2.0 