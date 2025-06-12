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

#### 必須フィールド
- **citation_key**: BibTeXファイル内のcitation keyと同一（ファイル名と一致）
- **processing_status**: 各処理ステップの状態記録
- **last_updated**: 状態最終更新日時（ISO 8601形式、自動生成）
- **workflow_version**: 使用ワークフローバージョン（自動生成）

#### AI理解支援機能フィールド
- **citations**: references.bibから統合された引用文献情報（{引用番号: CitationInfo}形式）
- **citation_metadata**: 引用情報のメタデータ（総数、更新日時、ソース、バージョン）

#### AI生成機能フィールド
- **tags**: 論文内容に基づく自動生成タグ（Array[String]、英語・スネークケース、10-20個程度）
- **abstract_japanese**: 論文abstractの日本語翻訳（YAML multi-line string、`|` 記法使用）

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

## YAML操作実装

### ヘッダー読み込み・更新
```python
def read_yaml_header(md_file: str) -> Dict[str, Any]:
    """Markdownファイルからヘッダーを読み込み"""
    # YAML frontmatter抽出・解析処理

def update_yaml_header(md_file: str, updates: Dict[str, Any]) -> bool:
    """Markdownファイルのヘッダーを更新"""
    # ヘッダー更新・ファイル書き込み処理
```

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
```python
def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict[str, Any]:
    """
    整合性チェック（エッジケース詳細情報付き）
    
    Returns:
        {
            "consistent": bool,
            "missing_in_clippings": List[str],           # BibTeXにあるがMDなし
            "orphaned_in_clippings": List[str],          # MDにあるがBibTeXなし  
            "valid_papers": List[str],                   # 両方に存在（処理対象）
            "total_papers": int,                         # BibTeX内論文総数
            "total_clippings": int,                      # MD ファイル総数
            "edge_case_details": {
                "missing_count": int,
                "orphaned_count": int,
                "missing_with_doi": List[Dict[str, str]], # DOI情報付き
                "orphaned_file_paths": List[str]          # ファイルパス情報
            }
        }
    """
    # エッジケース特定・詳細情報収集処理
```

### ワークフローとの連携

#### エッジケース除外処理
```python
def get_papers_needing_processing(self, clippings_dir: str, step: str, target_papers: List[str] = None) -> List[str]:
    """
    処理が必要な論文リストを取得（エッジケース除外済み）
    
    Args:
        target_papers: 事前にエッジケースが除外された有効な論文リスト（必須）
    """
    if target_papers is None:
        raise ValueError("target_papers must be provided after edge case filtering")
    
    # 指定された有効な論文の中から、処理が必要なもののみを抽出
    all_statuses = self.load_md_statuses(clippings_dir)
    
    papers_needing_processing = []
    for paper in target_papers:
        if paper in all_statuses:
            current_status = all_statuses[paper].get(step, ProcessStatus.PENDING)
            if current_status in [ProcessStatus.PENDING, ProcessStatus.FAILED]:
                papers_needing_processing.append(paper)
    
    return papers_needing_processing
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

## 設計方針

### エッジケース処理の原則
1. **安全性優先**: 不完全なデータでの処理は行わない
2. **情報提供**: 問題の詳細を明確に報告
3. **処理継続**: 一部の問題で全体が停止しない
4. **ユーザビリティ**: DOIリンク等で問題解決を支援

### 状態管理の責任範囲
- **対象**: BibTeXとMarkdownファイルの両方に存在する論文のみ
- **除外**: エッジケースは状態管理対象外（上位レイヤーで処理）
- **報告**: エッジケース検出と詳細情報提供は責任範囲内

---

**状態管理システム仕様書バージョン**: 3.1.0 