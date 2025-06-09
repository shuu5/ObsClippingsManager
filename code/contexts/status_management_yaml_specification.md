# 状態管理システム仕様書 v3.0 - YAMLヘッダー方式

## 概要
ObsClippingsManager v3.0では、論文の処理状態をBibTeXファイルではなく、各論文の.mdファイルのYAMLヘッダーに記録する方式に変更します。これにより、Zoteroによる自動BibTeX再生成の影響を受けずに、永続的な状態管理を実現します。

## 変更理由
- **問題**: BibTeXファイル（CurrentManuscript.bib）はZoteroにより自動生成され、状態フラグが消去される
- **解決策**: 各論文ディレクトリ内の.mdファイルのYAMLヘッダーに状態を記録
- **利点**: 
  - Zoteroの再生成に影響されない
  - 論文ファイルと状態の密結合
  - 可読性・編集可能性の向上

## アーキテクチャ変更

### 旧方式（v2.x）
```
CurrentManuscript.bib（Zotero管理）
├── @article{smith2023test,
│   ├── title = {...},
│   ├── author = {...},
│   ├── obsclippings_organize_status = {completed},
│   ├── obsclippings_sync_status = {completed},
│   ├── obsclippings_fetch_status = {pending},
│   └── obsclippings_parse_status = {pending}
│   }
└── [Zotero再生成時に状態フラグ消失]
```

### 新方式（v3.0）
```
/home/user/ManuscriptsManager/Clippings/
├── smith2023test/
│   ├── smith2023test.md（状態管理ヘッダー付き）
│   └── references.bib
├── jones2024neural/
│   ├── jones2024neural.md（状態管理ヘッダー付き）
│   └── references.bib
```

## YAMLヘッダー仕様

### 標準フォーマット
```yaml
---
obsclippings_metadata:
  citation_key: "smith2023test"
  processing_status:
    organize: "completed"
    sync: "completed" 
    fetch: "pending"
    parse: "pending"
  last_updated: "2025-01-15T10:30:00Z"
  source_doi: "10.1000/example.doi"
  workflow_version: "3.0"
---

# Smith et al. (2023) - Example Paper Title

論文の内容...
```

### フィールド定義

#### obsclippings_metadata
論文の処理メタデータを格納するトップレベルオブジェクト

#### citation_key (必須)
- **型**: String
- **説明**: BibTeXファイル内のcitation keyと同一の値
- **例**: "smith2023test"

#### processing_status (必須)
- **型**: Object
- **説明**: 各処理ステップの状態を記録
- **フィールド**:
  - `organize`: ファイル整理状態
  - `sync`: 同期チェック状態
  - `fetch`: 引用文献取得状態
  - `parse`: 引用文献解析状態

#### 状態値定義
- **"pending"**: 処理が必要（初期状態・失敗後の再処理待ち）
- **"completed"**: 処理完了
- **"failed"**: 処理失敗（次回実行時に再処理対象）

#### last_updated (自動生成)
- **型**: ISO 8601 DateTime String
- **説明**: 状態が最後に更新された日時
- **例**: "2025-01-15T10:30:00Z"

#### source_doi (オプション)
- **型**: String
- **説明**: 論文のDOI（参照用）
- **例**: "10.1000/example.doi"

#### workflow_version (自動生成)
- **型**: String
- **説明**: 使用したワークフローのバージョン
- **例**: "3.0"

## StatusManager v3.0 設計

### 主要な変更点

#### 1. ファイル読み込み方式の変更
```python
# 旧方式（v2.x）
def load_bib_statuses(self, bibtex_file: str) -> Dict[str, Dict[str, ProcessStatus]]:
    """BibTeXファイルから状態を読み込み"""

# 新方式（v3.0）
def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessStatus]]:
    """Clippingsディレクトリの各.mdファイルから状態を読み込み"""
```

#### 2. 状態更新方式の変更
```python
# 旧方式（v2.x）
def update_status(self, bibtex_file: str, citation_key: str, 
                 process_type: str, status: ProcessStatus) -> bool:
    """BibTeXファイル内の状態フィールドを更新"""

# 新方式（v3.0）
def update_status(self, clippings_dir: str, citation_key: str,
                 process_type: str, status: ProcessStatus) -> bool:
    """対応する.mdファイルのYAMLヘッダーを更新"""
```

#### 3. ファイル発見・作成メカニズム
```python
def get_md_file_path(self, clippings_dir: str, citation_key: str) -> Path:
    """citation keyに対応する.mdファイルパスを取得"""
    return Path(clippings_dir) / citation_key / f"{citation_key}.md"

def ensure_yaml_header(self, md_file_path: Path, citation_key: str) -> bool:
    """YAMLヘッダーが存在しない場合は初期化"""
```

### クラス設計

#### StatusManager v3.0
```python
class StatusManager:
    """YAMLヘッダーベースの状態管理システム"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('StatusManager')
        
    def load_md_statuses(self, clippings_dir: str) -> Dict[str, Dict[str, ProcessStatus]]:
        """Clippingsディレクトリから全論文の状態を読み込み"""
        
    def update_status(self, clippings_dir: str, citation_key: str,
                     process_type: str, status: ProcessStatus) -> bool:
        """指定論文の状態を更新"""
        
    def batch_update_statuses(self, clippings_dir: str,
                            updates: Dict[str, Dict[str, ProcessStatus]]) -> bool:
        """複数論文の状態を一括更新"""
        
    def get_papers_needing_processing(self, clippings_dir: str, process_type: str,
                                    include_failed: bool = True) -> List[str]:
        """指定処理が必要な論文リストを取得"""
        
    def reset_statuses(self, clippings_dir: str, 
                      target_papers: Optional[Union[str, List[str]]] = None) -> bool:
        """状態をリセット"""
        
    def check_status_consistency(self, bibtex_file: str, 
                               clippings_dir: str) -> Dict[str, Any]:
        """BibTeX ↔ Clippings間の整合性チェック"""
        
    def ensure_yaml_header(self, md_file_path: Path, citation_key: str) -> bool:
        """YAMLヘッダーの初期化"""
        
    def parse_yaml_header(self, md_file_path: Path) -> Dict[str, Any]:
        """YAMLヘッダーの解析"""
        
    def write_yaml_header(self, md_file_path: Path, metadata: Dict[str, Any]) -> bool:
        """YAMLヘッダーの書き込み"""
```

### YAMLパーサー統合

#### 依存関係追加
```python
import yaml
from datetime import datetime, timezone
```

#### YAMLヘッダー処理
```python
def parse_yaml_header(self, md_file_path: Path) -> Dict[str, Any]:
    """
    .mdファイルからYAMLヘッダーを解析
    
    Returns:
        YAMLヘッダーの内容、存在しない場合は空辞書
    """
    
def write_yaml_header(self, md_file_path: Path, metadata: Dict[str, Any]) -> bool:
    """
    .mdファイルにYAMLヘッダーを書き込み
    
    既存のヘッダーがある場合は更新、ない場合は追加
    """
```

## 移行戦略

### 段階的移行

#### Phase 1: StatusManager v3.0実装
1. 新しいStatusManagerクラスの実装
2. YAMLヘッダー処理機能の実装
3. ユニットテストの作成・実行

#### Phase 2: ワークフロー統合
1. EnhancedIntegratedWorkflow の修正
2. 各ワークフローのStatusManager呼び出し修正
3. CLI引数の調整

#### Phase 3: 後方互換性の確保
1. 旧形式（BibTeX状態フラグ）の検出・移行機能
2. 移行ツールの提供
3. 移行完了後の旧データクリーンアップ

### 移行ツール仕様

#### migrate_status_to_yaml コマンド
```bash
uv run python code/py/main.py migrate-status-to-yaml \
  -b /path/to/CurrentManuscript.bib \
  -d /path/to/Clippings \
  [--backup] [--dry-run]
```

**動作**:
1. BibTeXファイルから状態フラグを読み取り
2. 対応する.mdファイルを特定
3. YAMLヘッダーに状態を移行
4. 移行完了後、BibTeXから状態フラグを削除（オプション）

## テスト仕様変更

### 新規テストファイル
- `test_status_management_yaml.py`: YAMLヘッダー方式のテスト
- `test_migration_tools.py`: 移行ツールのテスト

### 既存テストの更新
- `test_enhanced_run_integrated.py`: StatusManager呼び出し方法の変更
- `test_workflow_manager.py`: 状態管理に関連する部分の更新

### テストケース

#### YAMLヘッダー処理テスト
```python
class TestYAMLHeaderProcessing(unittest.TestCase):
    def test_parse_yaml_header_existing(self):
        """既存YAMLヘッダーの解析テスト"""
        
    def test_parse_yaml_header_missing(self):
        """YAMLヘッダーなしファイルの処理テスト"""
        
    def test_write_yaml_header_new(self):
        """新規YAMLヘッダー作成テスト"""
        
    def test_write_yaml_header_update(self):
        """既存YAMLヘッダー更新テスト"""
        
    def test_yaml_format_validation(self):
        """YAMLフォーマット検証テスト"""
```

#### 状態管理機能テスト
```python
class TestStatusManagerV3(unittest.TestCase):
    def test_load_md_statuses(self):
        """Clippingsディレクトリからの状態読み込みテスト"""
        
    def test_update_status_yaml(self):
        """YAMLヘッダー経由の状態更新テスト"""
        
    def test_batch_update_yaml(self):
        """一括状態更新テスト（YAML）"""
        
    def test_consistency_check_yaml(self):
        """BibTeX-Clippings整合性チェック（YAML）"""
```

#### 移行テスト
```python
class TestMigrationTools(unittest.TestCase):
    def test_migrate_bibtex_to_yaml(self):
        """BibTeX状態フラグ → YAML移行テスト"""
        
    def test_migration_rollback(self):
        """移行ロールバックテスト"""
        
    def test_migration_error_handling(self):
        """移行エラーハンドリングテスト"""
```

## 実装優先順位

### 高優先度（即時実装）
1. StatusManager v3.0 基本実装
2. YAMLヘッダー読み書き機能
3. 基本的なユニットテスト

### 中優先度（基本実装後）
1. EnhancedIntegratedWorkflow修正
2. 全ワークフローの統合
3. 包括的テストスイート

### 低優先度（安定化後）
1. 移行ツール実装
2. 後方互換性確保
3. パフォーマンス最適化

## 注意事項

### 設計上の考慮点
- **YAMLパーサーの選択**: PyYAMLまたはruamel.yaml
- **ファイルロック**: 複数プロセス同時実行時の競合回避
- **エラーハンドリング**: YAML構文エラー、ファイル権限等
- **パフォーマンス**: 大量論文時のファイルI/O最適化

### セキュリティ考慮
- YAML Bomb攻撃の防止
- ファイルパストラバーサル対策
- 権限チェック

### 互換性確保
- 既存.mdファイルの内容保持
- 段階的移行による運用継続
- ロールバック機能の提供

---

**この仕様書は、ObsClippingsManager v3.0における状態管理システムの根本的な改善を定義し、Zotero環境での安定した動作を保証します。** 