# 状態管理システム仕様書 v3.1

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
- **ai-citation-support**: AI理解支援統合状態
- **tagger**: タグ生成状態
- **translate_abstract**: 要約翻訳状態

### 状態値定義
- **"pending"**: 処理が必要（初期状態・失敗後）
- **"completed"**: 処理完了
- **"failed"**: 処理失敗（次回再処理対象）

## YAMLヘッダー仕様

### 標準フォーマット
```yaml
---
citation_key: smith2023test
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
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai-citation-support: completed
  tagger: completed
  translate_abstract: completed
workflow_version: '3.1'
---
```

### フィールド詳細

#### citation_key (必須)
- **型**: String
- **説明**: BibTeXファイル内のcitation keyと同一
- **制約**: ファイル名と一致する必要がある

#### processing_status (必須)
- **型**: Object
- **説明**: 各処理ステップの状態記録
- **フィールド**: organize, sync, fetch, ai-citation-support, tagger, translate_abstract

#### last_updated (自動生成)
- **型**: ISO 8601 DateTime String
- **説明**: 状態最終更新日時
- **更新**: 状態変更時に自動更新

#### workflow_version (自動生成)
- **型**: String
- **説明**: 使用ワークフローバージョン

#### citations (AI理解支援機能)
- **型**: Object
- **説明**: references.bibから統合された引用文献情報
- **構造**: {引用番号: CitationInfo}

#### citation_metadata (AI理解支援機能)
- **型**: Object
- **フィールド**:
  - `total_citations`: 総引用数
  - `last_updated`: 引用情報最終更新日時
  - `source_bibtex`: 元のBibTeXファイルパス
  - `mapping_version`: マッピングバージョン

#### tags (AI生成機能)
- **型**: Array[String]
- **説明**: 論文内容に基づく自動生成タグ
- **命名規則**: 英語・スネークケース形式
- **数量**: 10-20個程度

#### abstract_japanese (AI翻訳機能)
- **型**: String (Multi-line)
- **説明**: 論文abstractの日本語翻訳
- **形式**: YAML multi-line string（`|` 記法使用）

## StatusManager クラス設計

### クラス概要
```python
class StatusManager:
    """YAMLヘッダーベースの状態管理システム"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger)
    
    # 主要メソッド
    def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessStatus]]
    def update_status(self, clippings_dir: str, citation_key: str, step: str, status: ProcessStatus) -> bool
    def get_papers_needing_processing(self, clippings_dir: str, step: str, target_papers: List[str] = None) -> List[str]
    def reset_statuses(self, clippings_dir: str, target_papers: List[str] = None) -> bool
    def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict[str, Any]
```

### 主要メソッド詳細

#### load_md_statuses() - 状態読み込み
```python
def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessStatus]]:
    """
    Clippingsディレクトリから全論文の状態を読み込み
    
    Returns:
        {
            "smith2023test": {
                "organize": ProcessStatus.COMPLETED,
                "sync": ProcessStatus.COMPLETED,
                "fetch": ProcessStatus.PENDING,
                "ai-citation-support": ProcessStatus.PENDING,
                "tagger": ProcessStatus.PENDING,
                "translate_abstract": ProcessStatus.PENDING
            }
        }
    """
```

#### update_status() - 状態更新
```python
def update_status(self, clippings_dir: str, citation_key: str, step: str, status: ProcessStatus) -> bool:
    """
    特定論文の特定ステップの状態を更新
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        citation_key: 論文のcitation key
        step: 処理ステップ名
        status: 新しい状態
    
    Returns:
        更新成功可否
    """
```

#### get_papers_needing_processing() - 処理対象論文取得
```python
def get_papers_needing_processing(self, clippings_dir: str, step: str, target_papers: List[str] = None) -> List[str]:
    """
    指定ステップで処理が必要な論文リストを取得
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        step: 処理ステップ名
        target_papers: 対象論文リスト（Noneの場合は全論文）
    
    Returns:
        処理が必要な論文のcitation keyリスト
    """
```

#### reset_statuses() - 状態リセット
```python
def reset_statuses(self, clippings_dir: str, target_papers: List[str] = None) -> bool:
    """
    指定論文の全状態をpendingにリセット
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        target_papers: 対象論文リスト（Noneの場合は全論文）
    
    Returns:
        リセット成功可否
    """
```

#### check_consistency() - 整合性チェック
```python
def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict[str, Any]:
    """
    BibTeXファイルとClippingsディレクトリの整合性チェック
    
    Returns:
        {
            "consistent": bool,
            "missing_in_clippings": List[str],
            "orphaned_in_clippings": List[str],
            "total_papers": int,
            "total_clippings": int
        }
    """
```

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

## YAML操作実装

### ヘッダー読み込み
```python
def read_yaml_header(md_file: str) -> Dict[str, Any]:
    """Markdownファイルからヘッダーを読み込み"""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # YAML frontmatter抽出
    if content.startswith('---\n'):
        end_pos = content.find('\n---\n', 4)
        yaml_content = content[4:end_pos]
        return yaml.safe_load(yaml_content)
    return {}
```

### ヘッダー更新
```python
def update_yaml_header(md_file: str, updates: Dict[str, Any]) -> bool:
    """Markdownファイルのヘッダーを更新"""
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # ヘッダーと本文を分離
        if content.startswith('---\n'):
            end_pos = content.find('\n---\n', 4)
            yaml_content = content[4:end_pos]
            body = content[end_pos + 5:]
            
            # ヘッダー更新
            header_data = yaml.safe_load(yaml_content)
            header_data.update(updates)
            
            # ファイル書き込み
            new_content = f"---\n{yaml.dump(header_data, allow_unicode=True)}---\n{body}"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
    except Exception as e:
        logger.error(f"Failed to update YAML header: {e}")
        return False
```

## エラーハンドリング

### 状態不整合対応
- **欠損状態**: 存在しない状態項目はデフォルト値"pending"で補完
- **不正値**: 不正な状態値は"pending"にリセット
- **形式エラー**: YAML形式エラーの場合は新規作成

### ファイル操作エラー
- **ファイル未存在**: 新規Markdownファイルとして作成
- **権限エラー**: エラーログ記録後処理継続
- **ディスク容量不足**: 処理停止とエラー通知

## 使用例

### 基本的な使用方法
```python
# StatusManager初期化
status_manager = StatusManager(config_manager, logger)

# 全状態読み込み
statuses = status_manager.load_md_statuses("/path/to/clippings")

# fetch処理が必要な論文を取得
papers_to_fetch = status_manager.get_papers_needing_processing(
    "/path/to/clippings", "fetch"
)

# 処理実行後の状態更新
for paper in papers_to_fetch:
    try:
        # 実際の処理
        fetch_citations(paper)
        # 成功時
        status_manager.update_status("/path/to/clippings", paper, "fetch", ProcessStatus.COMPLETED)
    except Exception as e:
        # 失敗時
        status_manager.update_status("/path/to/clippings", paper, "fetch", ProcessStatus.FAILED)
```

### 強制再処理
```python
# 全状態リセット
status_manager.reset_statuses("/path/to/clippings")

# 特定論文のみリセット
status_manager.reset_statuses("/path/to/clippings", ["smith2023test", "jones2024neural"])
```

### 整合性チェック
```python
# BibTeXファイルとClippingsの整合性確認
consistency = status_manager.check_consistency(
    "/path/to/CurrentManuscript.bib",
    "/path/to/clippings"
)

if not consistency["consistent"]:
    print(f"Missing papers: {consistency['missing_in_clippings']}")
    print(f"Orphaned files: {consistency['orphaned_in_clippings']}")
```

---

**状態管理システム仕様書バージョン**: 3.1.0 