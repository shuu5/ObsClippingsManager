# 状態管理システム仕様書 v3.0

## 概要
ObsClippingsManager v3.0の状態管理システムは、各論文の処理状態をMarkdownファイルのYAMLヘッダーに記録し、効率的な重複処理回避を実現します。Zoteroによる自動BibTeX再生成の影響を受けずに、永続的な状態管理を提供します。

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
    pages: '567-578'
    title: Advanced Biomarker Techniques in Oncology
    volume: '28'
    year: 2022
  2:
    authors: Davis
    citation_key: davis2023neural
    doi: 10.1126/science.abcd1234
    journal: Science
    pages: '123-135'
    title: Neural Networks in Medical Diagnosis
    volume: '381'
    year: 2023
last_updated: '2025-01-15T10:30:00.654321+00:00'
processing_status:
  ai-citation-support: completed
  fetch: completed
  organize: completed
  sync: completed
workflow_version: '3.0'
---

# Smith et al. (2023) - Example Paper Title

論文の内容...
```

### フィールド詳細

#### citation_key (必須)
- **型**: String
- **説明**: BibTeXファイル内のcitation keyと同一
- **例**: "smith2023test"
- **制約**: ファイル名と一致する必要がある

#### processing_status (必須)
- **型**: Object
- **説明**: 各処理ステップの状態記録
- **フィールド**:
  - `organize`: ファイル整理状態
  - `sync`: 同期チェック状態
  - `fetch`: 引用文献取得状態
  - `ai-citation-support`: AI理解支援統合状態

#### last_updated (自動生成)
- **型**: ISO 8601 DateTime String
- **説明**: 状態最終更新日時
- **例**: "2025-01-15T10:30:00Z"
- **更新**: 状態変更時に自動更新

#### workflow_version (自動生成)
- **型**: String
- **説明**: 使用ワークフローバージョン
- **例**: "3.0"
- **用途**: 将来の互換性確認

#### citations (AI理解支援機能)
- **型**: Object
- **説明**: references.bibから統合された引用文献情報
- **構造**: {引用番号: CitationInfo}
- **生成**: ai-citation-supportステップで作成
- **更新**: references.bib変更時に再生成

#### citation_metadata (AI理解支援機能)
- **型**: Object
- **説明**: 引用文献統合のメタデータ
- **フィールド**:
  - `total_citations`: 総引用数（BibTeXエントリー数）
  - `last_updated`: 引用情報最終更新日時
  - `source_bibtex`: 元のBibTeXファイルパス
  - `mapping_version`: マッピングバージョン

## StatusManager v3.0 クラス設計

### クラス概要
```python
class StatusManager:
    """YAMLヘッダーベースの状態管理システム"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('StatusManager')
        
    # 主要メソッド群
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
    
    Args:
        clippings_dir: Clippingsディレクトリパス
    
    Returns:
        {
            "smith2023test": {
                "organize": ProcessStatus.COMPLETED,
                "sync": ProcessStatus.COMPLETED,
                "fetch": ProcessStatus.PENDING,
                "ai-citation-support": ProcessStatus.PENDING
            },
            "jones2024neural": {
                "organize": ProcessStatus.PENDING,
                "sync": ProcessStatus.PENDING,
                "fetch": ProcessStatus.PENDING,
                "ai-citation-support": ProcessStatus.PENDING
            }
        }
    
    処理フロー:
    1. clippings_dir内のサブディレクトリを走査
    2. 各ディレクトリ内の.mdファイルを検索
    3. YAMLヘッダーから状態情報を抽出
    4. 状態辞書として返却
    """
    statuses = {}
    clippings_path = Path(clippings_dir)
    
    if not clippings_path.exists():
        self.logger.warning(f"Clippings directory not found: {clippings_dir}")
        return statuses
    
    for paper_dir in clippings_path.iterdir():
        if not paper_dir.is_dir():
            continue
            
        citation_key = paper_dir.name
        md_file_path = paper_dir / f"{citation_key}.md"
        
        if md_file_path.exists():
            paper_status = self._parse_md_status(md_file_path)
            if paper_status:
                statuses[citation_key] = paper_status
            else:
                # YAMLヘッダーが存在しない場合は初期化
                statuses[citation_key] = self._initialize_paper_status(citation_key)
                self._ensure_yaml_header(md_file_path, citation_key)
    
    return statuses
```

#### update_status() - 状態更新
```python
def update_status(self, clippings_dir: str, citation_key: str, 
                 step: str, status: ProcessStatus) -> bool:
    """
    指定論文の指定ステップの状態を更新
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        citation_key: 論文のcitation key
        step: 処理ステップ名 ("organize"|"sync"|"fetch"|"ai-citation-support")
        status: 新しい状態 (ProcessStatus.COMPLETED|FAILED|PENDING)
    
    Returns:
        更新成功時 True, 失敗時 False
    
    処理フロー:
    1. 対象.mdファイルパスを構築
    2. 現在のYAMLヘッダーを読み込み
    3. 指定ステップの状態を更新
    4. last_updatedを現在時刻に更新
    5. YAMLヘッダーを書き戻し
    """
    md_file_path = Path(clippings_dir) / citation_key / f"{citation_key}.md"
    
    if not md_file_path.exists():
        self.logger.error(f"Markdown file not found: {md_file_path}")
        return False
    
    try:
        # 現在のメタデータ読み込み
        metadata = self._parse_yaml_header(md_file_path)
        
        # 状態更新
        if 'processing_status' not in metadata:
            metadata.update(self._create_default_metadata(citation_key))
        
        metadata['processing_status'][step] = status.value
        metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        # ファイル更新
        return self._write_yaml_header(md_file_path, metadata)
        
    except Exception as e:
        self.logger.error(f"Failed to update status for {citation_key}: {str(e)}")
        return False
```

#### get_papers_needing_processing() - 処理対象論文取得
```python
def get_papers_needing_processing(self, clippings_dir: str, step: str, 
                                target_papers: List[str] = None) -> List[str]:
    """
    指定ステップで処理が必要な論文リストを取得
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        step: 処理ステップ名
        target_papers: 対象論文リスト（None時は全論文）
    
    Returns:
        処理が必要な論文のcitation keyリスト
    
    処理条件:
    - 状態が "pending" または "failed"
    - target_papersが指定された場合はその範囲内のみ
    - 依存関係チェック（前段階が完了していない場合は除外）
    """
    all_statuses = self.load_md_statuses(clippings_dir)
    papers_needing_processing = []
    
    # 対象論文の決定
    if target_papers is None:
        target_papers = list(all_statuses.keys())
    
    for citation_key in target_papers:
        if citation_key not in all_statuses:
            # 状態情報がない場合は処理対象
            papers_needing_processing.append(citation_key)
            continue
        
        paper_status = all_statuses[citation_key]
        step_status = paper_status.get(step, ProcessStatus.PENDING)
        
        # pending or failed の場合は処理対象
        if step_status in [ProcessStatus.PENDING, ProcessStatus.FAILED]:
            # 依存関係チェック
            if self._check_dependencies(paper_status, step):
                papers_needing_processing.append(citation_key)
    
    return papers_needing_processing
```

#### reset_statuses() - 状態リセット
```python
def reset_statuses(self, clippings_dir: str, 
                  target_papers: List[str] = None) -> bool:
    """
    指定論文の状態をpendingにリセット（強制再処理用）
    
    Args:
        clippings_dir: Clippingsディレクトリパス
        target_papers: 対象論文リスト（None時は全論文）
    
    Returns:
        リセット成功時 True
    
    処理内容:
    - 全ステップの状態を "pending" に設定
    - last_updatedを現在時刻に更新
    - workflow_versionを現在バージョンに更新
    """
    all_statuses = self.load_md_statuses(clippings_dir)
    
    if target_papers is None:
        target_papers = list(all_statuses.keys())
    
    success_count = 0
    
    for citation_key in target_papers:
        try:
            md_file_path = Path(clippings_dir) / citation_key / f"{citation_key}.md"
            
            if not md_file_path.exists():
                self.logger.warning(f"Markdown file not found for reset: {citation_key}")
                continue
            
            # メタデータリセット
            metadata = self._parse_yaml_header(md_file_path)
            
            if 'processing_status' not in metadata:
                metadata.update(self._create_default_metadata(citation_key))
            
            # 全ステップをpendingに設定
            metadata['processing_status'] = {
                'organize': ProcessStatus.PENDING.value,
                'sync': ProcessStatus.PENDING.value,
                'fetch': ProcessStatus.PENDING.value,
                'ai-citation-support': ProcessStatus.PENDING.value
            }
            
            metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
            metadata['workflow_version'] = "3.0"
            
            if self._write_yaml_header(md_file_path, metadata):
                success_count += 1
                self.logger.info(f"Reset status for: {citation_key}")
            
        except Exception as e:
            self.logger.error(f"Failed to reset status for {citation_key}: {str(e)}")
    
    self.logger.info(f"Successfully reset {success_count}/{len(target_papers)} papers")
    return success_count == len(target_papers)
```

#### check_consistency() - 整合性チェック
```python
def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict[str, Any]:
    """
    BibTeX ↔ Clippingsディレクトリ間の整合性チェック
    
    Args:
        bibtex_file: BibTeXファイルパス
        clippings_dir: Clippingsディレクトリパス
    
    Returns:
        {
            "status": "success"|"warning"|"error",
            "summary": {
                "bibtex_entries": 10,
                "clippings_directories": 12,
                "matched": 8,
                "missing_in_clippings": 2,
                "orphaned_directories": 4
            },
            "details": {
                "missing_in_clippings": [
                    {
                        "citation_key": "smith2023",
                        "title": "Example Paper",
                        "doi": "10.1000/example.doi"
                    }
                ],
                "orphaned_directories": [
                    {
                        "citation_key": "old_paper2022",
                        "directory_path": "/path/to/clippings/old_paper2022"
                    }
                ],
                "status_inconsistencies": [
                    {
                        "citation_key": "jones2024",
                        "issue": "marked as completed but references.bib missing"
                    }
                ]
            }
        }
    """
    from .bibtex_parser import BibTeXParser
    
    # BibTeXエントリ読み込み
    bibtex_parser = BibTeXParser(self.logger)
    bib_entries = bibtex_parser.parse_file(bibtex_file)
    bib_keys = set(bib_entries.keys())
    
    # Clippingsディレクトリ読み込み
    clippings_path = Path(clippings_dir)
    clipping_keys = set()
    
    if clippings_path.exists():
        clipping_keys = {d.name for d in clippings_path.iterdir() if d.is_dir()}
    
    # 整合性分析
    matched = bib_keys & clipping_keys
    missing_in_clippings = bib_keys - clipping_keys
    orphaned_directories = clipping_keys - bib_keys
    
    # 状態管理整合性チェック
    status_inconsistencies = self._check_status_inconsistencies(clippings_dir, clipping_keys)
    
    # 結果生成
    result = {
        "status": "success",
        "summary": {
            "bibtex_entries": len(bib_keys),
            "clippings_directories": len(clipping_keys),
            "matched": len(matched),
            "missing_in_clippings": len(missing_in_clippings),
            "orphaned_directories": len(orphaned_directories)
        },
        "details": {
            "missing_in_clippings": [
                {
                    "citation_key": key,
                    "title": bib_entries[key].get('title', 'Unknown'),
                    "doi": bib_entries[key].get('doi', 'Unknown')
                }
                for key in missing_in_clippings
            ],
            "orphaned_directories": [
                {
                    "citation_key": key,
                    "directory_path": str(clippings_path / key)
                }
                for key in orphaned_directories
            ],
            "status_inconsistencies": status_inconsistencies
        }
    }
    
    # ステータス判定
    if missing_in_clippings or orphaned_directories or status_inconsistencies:
        result["status"] = "warning"
    
    return result
```

## ヘルパーメソッド

### YAMLヘッダー処理
```python
def _parse_yaml_header(self, md_file_path: Path) -> Dict[str, Any]:
    """
    MarkdownファイルからYAMLヘッダーを解析
    
    Returns:
        YAMLヘッダーの内容、存在しない場合は空辞書
    """
    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAML frontmatter の抽出
        if content.startswith('---\n'):
            end_marker = content.find('\n---\n', 4)
            if end_marker != -1:
                yaml_content = content[4:end_marker]
                return yaml.safe_load(yaml_content) or {}
        
        return {}
        
    except Exception as e:
        self.logger.error(f"Failed to parse YAML header from {md_file_path}: {str(e)}")
        return {}

def _write_yaml_header(self, md_file_path: Path, metadata: Dict[str, Any]) -> bool:
    """
    MarkdownファイルにYAMLヘッダーを書き込み
    
    Args:
        md_file_path: 対象ファイルパス
        metadata: 書き込むメタデータ
    
    Returns:
        書き込み成功時 True
    """
    try:
        # 既存コンテンツの読み込み
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # YAML frontmatter とボディの分離
        body = content
        if content.startswith('---\n'):
            end_marker = content.find('\n---\n', 4)
            if end_marker != -1:
                body = content[end_marker + 5:]  # "---\n" 以降
        
        # 新しいYAMLヘッダーの生成
        yaml_header = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
        
        # ファイル書き込み
        new_content = f"---\n{yaml_header}---\n{body}"
        
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        self.logger.error(f"Failed to write YAML header to {md_file_path}: {str(e)}")
        return False

def _ensure_yaml_header(self, md_file_path: Path, citation_key: str) -> bool:
    """
    YAMLヘッダーが存在しない場合の初期化
    
    Args:
        md_file_path: 対象ファイルパス
        citation_key: 論文のcitation key
    
    Returns:
        初期化成功時 True
    """
    if not md_file_path.exists():
        # ファイル自体が存在しない場合は作成
        default_content = f"# {citation_key}\n\n論文の内容をここに記載してください。\n"
        
        try:
            md_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(default_content)
        except Exception as e:
            self.logger.error(f"Failed to create markdown file {md_file_path}: {str(e)}")
            return False
    
    # YAMLヘッダーの確認・初期化
    metadata = self._parse_yaml_header(md_file_path)
    
    if 'processing_status' not in metadata:
        metadata.update(self._create_default_metadata(citation_key))
        return self._write_yaml_header(md_file_path, metadata)
    
    return True
```

### 状態管理ヘルパー
```python
def _create_default_metadata(self, citation_key: str) -> Dict[str, Any]:
    """
    デフォルトメタデータの生成
    """
    return {
        'citation_key': citation_key,
        'citation_metadata': {
            'last_updated': datetime.now(timezone.utc).isoformat()[:26],
            'mapping_version': '2.0',
            'source_bibtex': 'references.bib',
            'total_citations': 0
        },
        'citations': {},
        'last_updated': datetime.now(timezone.utc).isoformat(),
        'processing_status': {
            'organize': ProcessStatus.PENDING.value,
            'sync': ProcessStatus.PENDING.value,
            'fetch': ProcessStatus.PENDING.value,
            'ai-citation-support': ProcessStatus.PENDING.value,
            'final-sync': ProcessStatus.PENDING.value
        },
        'workflow_version': '3.0'
    }

def _check_dependencies(self, paper_status: Dict[str, ProcessStatus], step: str) -> bool:
    """
    ステップ依存関係のチェック
    
    依存関係: organize → sync → fetch → ai-citation-support → final-sync
    """
    dependencies = {
        'organize': [],
        'sync': ['organize'],
        'fetch': ['organize', 'sync'],
        'ai-citation-support': ['organize', 'sync', 'fetch'],
        'final-sync': ['organize', 'sync', 'fetch', 'ai-citation-support']
    }
    
    required_steps = dependencies.get(step, [])
    
    for required_step in required_steps:
        if paper_status.get(required_step) != ProcessStatus.COMPLETED:
            return False
    
    return True

def _check_status_inconsistencies(self, clippings_dir: str, clipping_keys: Set[str]) -> List[Dict[str, str]]:
    """
    状態管理の整合性チェック
    
    チェック項目:
    - fetch完了だがreferences.bibが存在しない
    - organize完了だが適切なディレクトリ構造でない
    """
    inconsistencies = []
    
    for citation_key in clipping_keys:
        paper_dir = Path(clippings_dir) / citation_key
        md_file = paper_dir / f"{citation_key}.md"
        
        if not md_file.exists():
            continue
        
        metadata = self._parse_yaml_header(md_file)
        processing_status = metadata.get('processing_status', {})
        
        # fetch完了だがreferences.bibが存在しない
        if processing_status.get('fetch') == 'completed':
            references_bib = paper_dir / 'references.bib'
            if not references_bib.exists():
                inconsistencies.append({
                    'citation_key': citation_key,
                    'issue': 'fetch marked as completed but references.bib missing'
                })
        
        # organize完了だが適切な構造でない
        if processing_status.get('organize') == 'completed':
            if not paper_dir.is_dir():
                inconsistencies.append({
                    'citation_key': citation_key,
                    'issue': 'organize marked as completed but directory structure incorrect'
                })
    
    return inconsistencies
```

## ProcessStatus 列挙型

### 定義
```python
from enum import Enum

class ProcessStatus(Enum):
    """処理状態の列挙型"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    
    @classmethod
    def from_string(cls, status_str: str) -> 'ProcessStatus':
        """文字列から ProcessStatus オブジェクトを生成"""
        try:
            return cls(status_str.lower())
        except ValueError:
            return cls.PENDING  # 不明な状態はpending扱い
```

## 使用例

### 基本的な状態確認
```python
# StatusManager初期化
status_manager = StatusManager(config_manager, logger)

# 全論文の状態読み込み
statuses = status_manager.load_md_statuses("/home/user/ManuscriptsManager/Clippings")

# organize処理が必要な論文を取得
papers_needing_organize = status_manager.get_papers_needing_processing(
    "/home/user/ManuscriptsManager/Clippings", "organize"
)

# 特定論文の状態更新
status_manager.update_status(
    "/home/user/ManuscriptsManager/Clippings", 
    "smith2023test", 
    "organize", 
    ProcessStatus.COMPLETED
)
```

### 整合性チェック
```python
# BibTeX ↔ Clippings整合性チェック
consistency_result = status_manager.check_consistency(
    "/home/user/ManuscriptsManager/CurrentManuscript.bib",
    "/home/user/ManuscriptsManager/Clippings"
)

if consistency_result["status"] == "warning":
    print("整合性に問題があります:")
    for missing in consistency_result["details"]["missing_in_clippings"]:
        print(f"  - 不足: {missing['citation_key']}")
```

### 強制再処理
```python
# 特定論文の状態リセット
status_manager.reset_statuses(
    "/home/user/ManuscriptsManager/Clippings",
    target_papers=["smith2023test", "jones2024neural"]
)

# 全論文の状態リセット
status_manager.reset_statuses(
    "/home/user/ManuscriptsManager/Clippings"
)
```

---

**状態管理システム仕様書バージョン**: 3.0.0 