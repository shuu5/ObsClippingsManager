# 状態管理システム仕様書

## 概要
各論文の処理状態をMarkdownファイルのYAMLヘッダーに記録し、効率的な重複処理回避を実現します。Zoteroによる自動BibTeX再生成の影響を受けない永続的な状態管理を提供します。

## 基本原理

### YAMLヘッダー方式の利点
- **永続性**: Zoteroの再生成に影響されない
- **可視性**: 論文ファイルで直接状態確認可能
- **密結合**: 論文ファイルと状態の自然な関連付け
- **編集可能**: 必要時の手動編集が容易

### 状態追跡対象
- **organize**: ファイル整理状態
- **sync**: 同期チェック状態
- **fetch**: 引用文献取得状態
- **section-parsing**: セクション分割処理状態
- **ai-citation-support**: AI理解支援統合状態
- **tagger**: タグ生成状態
- **translate_abstract**: 要約翻訳状態
- **ochiai_format**: 落合フォーマット要約状態

### 状態値定義
- **"pending"**: 処理が必要（初期状態・失敗後）
- **"completed"**: 処理完了
- **"failed"**: 処理失敗（次回再処理対象）

## YAMLヘッダー仕様

### 標準フォーマット
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
citation_metadata:
  last_updated: '2025-01-15T10:30:00.123456'
  mapping_version: '2.0'
  source_bibtex: references.bib
  total_citations: 2
citations:
  1:
    authors: Jones
    citation_key: jones2022biomarkers
    doi: 10.1038/s41591-022-0456-7
    journal: Nature Medicine
    title: Advanced Biomarker Techniques in Oncology
    year: 2022
  2:
    authors: Davis
    citation_key: davis2023neural
    doi: 10.1126/science.abcd1234
    journal: Science
    title: Neural Networks in Medical Diagnosis
    year: 2023
tags:
  - oncology
  - biomarkers
  - cancer_research
  - machine_learning
  - KRT13
  - EGFR
abstract_japanese: |
  本研究では、がん研究における先進的なバイオマーカー技術について報告する。
  KRT13およびEGFR遺伝子の発現パターンを機械学習アルゴリズムを用いて解析し、
  診断精度の向上を達成した。
ochiai_format:
  generated_at: '2025-01-15T11:00:00.123456'
  questions:
    what_is_this: |
      KRT13タンパク質の発現パターンを機械学習で解析し、
      がん診断精度を95%まで向上させた新しいバイオマーカー技術。
    what_is_superior: |
      既存手法と比較してAI画像解析による客観的定量評価を実現。
    technical_key: |
      深層学習ベースのCNNを用いたKRT13発現パターンの定量化。
    validation_method: |
      500例の組織サンプルによる後向き研究。
    discussion_points: |
      サンプル数制限により一般化性能に課題。
    next_papers: |
      1. Jones et al. (2022) - KRT13分子メカニズム
      2. Davis et al. (2023) - 他がん種での類似手法
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  section_parsing: completed
  ai-citation-support: completed
  tagger: completed
  translate_abstract: completed
  ochiai_format: completed
workflow_version: '3.2'
---
```

### フィールド詳細

#### 必須フィールド
- **citation_key**: BibTeXファイル内のcitation keyと同一（ファイル名と一致）
- **processing_status**: 各処理ステップの状態記録
- **last_updated**: 状態最終更新日時（ISO 8601形式、自動生成）
- **workflow_version**: 使用ワークフローバージョン（自動生成）

#### 構造解析フィールド
- **paper_structure**: セクション分割処理結果

#### AI理解支援機能フィールド
- **citations**: references.bibから統合された引用文献情報
- **citation_metadata**: 引用情報のメタデータ（総数、更新日時、ソース、バージョン）

#### AI生成機能フィールド
- **tags**: 論文内容に基づく自動生成タグ
- **abstract_japanese**: 論文abstractの日本語翻訳
- **ochiai_format**: 落合フォーマット6項目要約

## StatusManager クラス設計

### クラス概要
YAMLヘッダーベースの状態管理システムの中核クラス。

### 主要メソッド機能

#### load_md_statuses()
Clippingsディレクトリから全論文の状態を読み込み。
戻り値: `{citation_key: {step: ProcessStatus}}`形式の辞書

#### update_status()
特定論文の特定ステップの状態を更新。
引数: clippings_dir, citation_key, step, status

#### get_papers_needing_processing()
指定ステップで処理が必要な論文リストを取得（エッジケース除外済み論文のみ対象）。
引数: clippings_dir, step, target_papers（必須）

#### reset_statuses()
指定論文の全状態をpendingにリセット。
引数: clippings_dir, target_papers（Noneの場合は全論文）

#### check_consistency()
BibTeXファイルとClippingsディレクトリの整合性チェック（詳細情報付き）。

## ProcessStatus Enum

```python
from enum import Enum

class ProcessStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @classmethod
    def from_string(cls, status: str) -> 'ProcessStatus':
        """文字列から ProcessStatus へ変換"""
        
    def to_string(self) -> str:
        """ProcessStatus から文字列へ変換"""
```

## 状態更新フロー

### 処理開始時
1. **状態読み込み**: `load_md_statuses()` で現在状態取得
2. **処理対象特定**: `get_papers_needing_processing()` で対象論文抽出
3. **処理実行**: 各論文に対して実際の処理実行

### 処理中
1. **状態更新**: 処理開始時に状態を"pending"から"running"へ更新（オプション）
2. **エラーハンドリング**: 例外発生時は"failed"状態に更新

### 処理完了時
1. **成功時**: 状態を"completed"に更新
2. **失敗時**: 状態を"failed"に更新
3. **ログ記録**: 処理結果の詳細をログに記録

## エッジケース処理における状態管理

### 処理対象の限定
ステータス管理システムは、BibTeXファイルとClippingsディレクトリの**両方に存在する論文のみ**を処理対象とします。

#### 処理対象外ケース
1. **missing_in_clippings**: BibTeXに記載されているが.mdファイルが存在しない
   - **状態管理対象外**: YAMLヘッダーが存在しないため状態追跡不可
   - **処理**: DOI情報表示後スキップ
   - **ログ**: WARNING レベルで記録

2. **orphaned_in_clippings**: .mdファイルは存在するがBibTeXに記載されていない
   - **状態管理対象外**: BibTeX参照がないため処理ワークフローの対象外
   - **処理**: ファイル存在通知後スキップ  
   - **ログ**: WARNING レベルで記録

### check_consistency() の拡張
詳細な整合性チェック結果を返します。

### ワークフローとの連携

#### エッジケース除外処理
処理が必要な論文リストを取得する際、事前にエッジケースが除外された有効な論文リストを必須とします。

## エラーハンドリング

### 状態不整合対応
- **欠損状態**: 存在しない状態項目はデフォルト値"pending"で補完
- **不正値**: 不正な状態値は"pending"にリセット
- **形式エラー**: YAML形式エラーの場合は新規作成

### YAML操作安全性
- **バックアップ**: 更新前の自動バックアップ作成
- **原子性**: 更新操作の原子性保証
- **エンコーディング**: UTF-8エンコーディングの一貫性

## データ構造定義

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

### OchiaiFormat
```python
@dataclass
class OchiaiFormat:
    what_is_this: str            # どんなもの？
    what_is_superior: str        # 先行研究と比べてどこがすごい？
    technical_key: str           # 技術や手法のキモはどこ？
    validation_method: str       # どうやって有効だと検証した？
    discussion_points: str       # 議論はある？
    next_papers: str            # 次に読むべき論文は？
    generated_at: str           # 生成日時
```