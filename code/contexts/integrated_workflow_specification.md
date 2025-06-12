# 統合ワークフロー仕様書 v3.1

## 概要
統合ワークフロー（Integrated Workflow）は、ObsClippingsManager v3.1の中核機能。すべての処理を`run-integrated`コマンド一つで完結させるシンプルかつ効率的なシステム。状態管理により重複処理を自動回避し、デフォルト設定での引数なし実行を実現。

## 基本原理

### 単一コマンド統合
- **すべての機能**を`run-integrated`に集約
- **引数なし実行**でデフォルト動作
- **個別設定**は必要時のみ
- **AI理解支援**をオプションで追加

### 状態管理による効率化
- **YAMLヘッダー**による処理状態追跡
- **自動スキップ**で完了済み処理を回避
- **失敗再実行**で必要な処理のみ実施
- **AI機能処理状態**の追跡

### 統一ディレクトリ設定
- **workspace_path**一つでの全パス管理
- **自動導出**による設定シンプル化
- **個別指定**での柔軟性確保

## システム構成

### 処理フロー v3.1
```
organize → sync → fetch (with automatic metadata enrichment) → ai-citation-support → tagger → translate_abstract → final-sync
```

### メタデータ自動補完システム
- **デフォルト有効**: 全引用文献に対して自動的にメタデータ補完を実行
- **フォールバック戦略**: CrossRef → Semantic Scholar → OpenAlex → PubMed → OpenCitations
- **完全自動制御**: 十分な情報（title, author, journal, year）が得られた時点で後続API呼び出しを停止
- **API最適化**: 無駄なAPI呼び出しを削減し、効率的な処理を実現

### 依存関係
- 各ステップは**順次実行**
- **前段階完了**後に次段階実行
- **失敗時は後続ステップ停止**
- **AI機能**は**ai-citation-support完了後**に実行

### 状態追跡
- 各論文の`.md`ファイルYAMLヘッダーで状態管理
- ステップごとの処理状態を記録
- 完了/失敗/保留の状態管理
- **AI機能処理状態**の追跡

## 設定システム

### デフォルト設定
```yaml
# config/config.yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"

# AI機能設定（デフォルト無効）
ai_generation:
  tagger:
    enabled: false
    model: "claude-3-5-sonnet-20241022"
    batch_size: 5
  translate_abstract:
    enabled: false
    model: "claude-3-5-sonnet-20241022"
    batch_size: 3
```

### 設定優先順位
1. **コマンドライン引数** (最高優先度)
2. **設定ファイル** (config.yaml)
3. **デフォルト値** (最低優先度)

## IntegratedWorkflow クラス

### クラス設計
```python
class IntegratedWorkflow:
    """統合ワークフロー実行エンジン"""
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('IntegratedWorkflow')
        self.status_manager = StatusManager(config_manager, logger)
        
        # 各モジュールの初期化
        self.organize_workflow = OrganizationWorkflow(config_manager, logger)
        self.sync_workflow = SyncCheckWorkflow(config_manager, logger)
        self.fetch_workflow = CitationWorkflow(config_manager, logger)
        self.ai_citation_support_workflow = AICitationSupportWorkflow(config_manager, logger)
        self.tagger_workflow = TaggerWorkflow(config_manager, logger)
        self.translate_abstract_workflow = TranslateAbstractWorkflow(config_manager, logger)
    
    def execute(self, **options) -> Dict[str, Any]:
        """統合ワークフロー実行"""
    
    def show_execution_plan(self, **options) -> Dict[str, Any]:
        """実行計画表示（実行なし）"""
    
    def force_reprocess(self, **options) -> Dict[str, Any]:
        """強制再処理実行"""
```

### 主要処理フロー
1. **パス解決**: workspace_pathから全パス自動導出
2. **設定検証**: ファイル存在・エッジケース検出
3. **処理対象決定**: BibTeXとMarkdownの両方に存在する論文のみ
4. **ステップ実行**: 順次処理（前段階完了後に次段階）
5. **状態更新**: 各ステップ完了時の状態記録

## エッジケース処理仕様 v3.1

### 概要
BibTeXファイルとClippingsディレクトリ間の不整合ケースに対する処理方針を定義します。

### エッジケース定義

#### 1. missing_in_clippings
- **定義**: BibTeXに記載されているがClippingsディレクトリに対応する.mdファイルが存在しない論文
- **処理方針**: **DOI情報表示のみ、処理スキップ**
- **ログレベル**: WARNING
- **表示内容**: Citation key、DOI（利用可能な場合）、クリック可能なDOIリンク

#### 2. orphaned_in_clippings  
- **定義**: Clippingsディレクトリに存在するがBibTeXファイルに記載されていない.mdファイル
- **処理方針**: **論文情報表示のみ、処理スキップ**
- **ログレベル**: WARNING  
- **表示内容**: ファイルパス、Citation key（ファイル名から推定）

### 処理対象論文の決定
```python
def _determine_target_papers(self, paths: Dict[str, str], options: Dict[str, Any]) -> List[str]:
    """
    エッジケースを除外した処理対象論文リストを生成
    """
    # 整合性チェック実行
    consistency = self.status_manager.check_consistency(
        paths['bibtex_file'], 
        paths['clippings_dir']
    )
    
    # エッジケース検出時の警告表示
    if not consistency['consistent']:
        self._log_edge_cases(consistency['edge_case_details'])
    
    # BibTeXとMarkdownの両方に存在する論文のみを処理対象とする
    valid_papers = consistency['valid_papers']
    
    # ユーザー指定がある場合はフィルタリング
    if options.get('papers'):
        specified_papers = [p.strip() for p in options['papers'].split(',')]
        valid_papers = [p for p in valid_papers if p in specified_papers]
    
    return valid_papers
```

### 実行結果への影響
```python
execution_results = {
    'status': 'success',
    'executed_steps': [],
    'skipped_steps': [],
    'failed_steps': [],
    'total_papers_processed': 0,
    'skipped_papers': {
        'missing_in_clippings': [],
        'orphaned_in_clippings': []
    },
    'execution_time': 0
}
```

### 表示例
```
📊 Execution Summary:
Total papers in BibTeX: 15
Total markdown files: 12
Valid papers (both sources): 10
Skipped papers: 5
  - Missing markdown files: 3
  - Orphaned markdown files: 2

⚠️  Edge Cases Detected:
Missing markdown files for:
  - smith2023biomarkers (DOI: 10.1038/s41591-023-1234-5)
  - jones2024neural (DOI: 10.1126/science.xyz789)

Orphaned markdown files:
  - old_paper2022/old_paper2022.md
  - test_paper2021/test_paper2021.md
```

## 設計原則

### エッジケース処理の原則
1. **安全性優先**: 不完全なデータでの処理は行わない
2. **情報提供**: 問題の詳細を明確に報告
3. **処理継続**: 一部の問題で全体が停止しない
4. **ユーザビリティ**: DOIリンク等で問題解決を支援

### 情報提供の充実
1. **DOI表示**: 論文特定・取得支援のため
2. **クリック可能リンク**: ターミナルでの直接アクセス支援
3. **明確なメッセージ**: 問題の性質と対応方法の明示
4. **統計情報**: 全体的な処理状況の把握支援

## コマンドライン仕様

### 基本実行
```bash
# デフォルト実行（推奨）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess
```

### AI機能有効化
```bash
# タグ生成有効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-tagger

# 要約翻訳有効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-translate-abstract

# 両方有効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-tagger --enable-translate-abstract
```

### カスタム設定
```bash
# ワークスペース変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --papers "paper1,paper2,paper3"

# 特定ステップのスキップ
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --skip-steps "sync,final-sync"
```

## 実行結果例

### 正常実行
```json
{
    'status': 'success',
    'executed_steps': ['organize', 'sync', 'fetch', 'ai-citation-support', 'final-sync'],
    'skipped_steps': ['tagger', 'translate_abstract'],
    'failed_steps': [],
    'total_papers_processed': 10,
    'execution_time': 45.2
}
```

### 部分的成功（AI機能有効化時）
```json
{
    'status': 'success',
    'executed_steps': ['organize', 'sync', 'fetch', 'ai-citation-support', 'tagger', 'translate_abstract', 'final-sync'],
    'skipped_steps': [],
    'failed_steps': [],
    'total_papers_processed': 8,
    'steps_details': {
        'organize': {'processed': 2, 'skipped': 3},
        'tagger': {'generated_tags': 156, 'papers': 8},
        'translate_abstract': {'translated': 7, 'failed': 1}
    },
    'execution_time': 78.5
}
```

## エラーハンドリング

### 想定エラー
- **設定エラー**: 不正なパス・ファイル不存在
- **整合性エラー**: BibTeX-Clippings不整合
- **ネットワークエラー**: API通信失敗
- **処理エラー**: ステップ実行失敗

### エラー対応
- **設定エラー**: 詳細なエラーメッセージと修正方法の提示
- **整合性エラー**: エッジケース処理で継続実行
- **ネットワークエラー**: リトライ処理と適切なログ記録
- **処理エラー**: 状態管理による再実行サポート

## パフォーマンス仕様

### 処理時間目標
- **設定検証**: < 1秒
- **エッジケース検出**: < 2秒  
- **論文処理**: 10論文/分（AI機能無効時）
- **AI処理**: 5論文/分（AI機能有効時）

### リソース制約
- **メモリ使用量**: 100MB以下
- **API制限**: レート制限の適切な管理
- **ディスク容量**: 一時ファイルの適切な削除

## 9. 統合テストシステム v3.1.0

### 9.1 テストシステム概要

**ユニットテスト vs 統合テスト**:
- **ユニットテスト**: 個別モジュールの単体テスト (`code/unittest/`)
- **統合テスト**: マスターテストデータを使用したエンドツーエンドテスト

### 9.2 マスターテストデータ構造

```
code/test_data_master/           # 固定マスターデータ（Git管理）
├── CurrentManuscript.bib        # 5つのBibTeXエントリ
└── Clippings/                   # 3つのMarkdownファイル
    ├── Keratin_Profiling_*.md   # 対応エントリ: takenakaW2023J
    ├── KRT13_promotes_*.md      # 対応エントリ: zhangQ2023A
    └── KRT13_is_upregulated_*.md # orphaned（BibTeXに未対応）

TestManuscripts/                 # 実行環境（自動生成・Git除外）
├── CurrentManuscript.bib        # masterからコピー
└── Clippings/                   # masterからコピー
```

### 9.3 エッジケーステストケース

**意図的不整合データ**:
1. `missing_in_clippings`: BibTeXにあるがClippingsにないエントリ（2件）
2. `orphaned_in_clippings`: ClippingsにあるがBibTeXにないファイル（1件）
3. `matching_entries`: 正常に対応するペア（2件）

### 9.4 統合テストスクリプト仕様

**スクリプト**: `code/scripts/test_run.sh`

**主要機能**:
- マスターデータからテスト環境自動構築
- 統合ワークフロー実行（複数モード対応）
- テスト結果自動確認・表示
- 一貫したテスト環境保証

**実行モード**:
```bash
# 基本実行
./code/scripts/test_run.sh

# 環境リセット後実行
./code/scripts/test_run.sh --reset --run

# ドライラン
./code/scripts/test_run.sh --dry-run

# デバッグモード
./code/scripts/test_run.sh --debug

# 実行計画表示
./code/scripts/test_run.sh --plan
```

### 9.5 テスト結果検証

**自動確認項目**:
1. ファイル構造整合性
2. YAML状態管理正確性
3. エッジケース処理妥当性
4. AI機能動作確認（タグ生成・翻訳）

**期待される結果**:
- `matching_entries`: 完全処理（fetch, organize, ai-support完了）
- `missing_in_clippings`: 情報表示のみ（処理スキップ）
- `orphaned_in_clippings`: ファイル情報表示のみ（処理スキップ）

---

このシステムにより、開発者は常に同一条件で統合テストを実行でき、システムの品質を確保できます。

---

**統合ワークフロー仕様書バージョン**: 3.1.0