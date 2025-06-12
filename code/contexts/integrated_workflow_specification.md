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

## 統一設定システム

### デフォルト設定
```yaml
# config/config.yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"

# AI機能設定
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

### パス解決
```python
def resolve_paths(workspace_path: str = None, **kwargs) -> Dict[str, str]:
    """統一パス解決システム"""
    if not workspace_path:
        workspace_path = "/home/user/ManuscriptsManager"
    
    paths = {
        'workspace_path': workspace_path,
        'bibtex_file': kwargs.get('bibtex_file', f"{workspace_path}/CurrentManuscript.bib"),
        'clippings_dir': kwargs.get('clippings_dir', f"{workspace_path}/Clippings"),
        'output_dir': kwargs.get('output_dir', f"{workspace_path}/Clippings")
    }
    
    return paths
```

## メインクラス: IntegratedWorkflow

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

### 主要メソッド

#### execute() - 統合実行
```python
def execute(self, **options) -> Dict[str, Any]:
    """
    統合ワークフロー実行
    
    Args:
        workspace_path: ワークスペースパス
        papers: 対象論文リスト (カンマ区切り文字列)
        skip_steps: スキップステップリスト
        force_reprocess: 強制再処理フラグ
        show_plan: 実行計画表示フラグ
        enable_tagger: タグ生成機能有効化
        enable_translate_abstract: 要約翻訳機能有効化
        **kwargs: 個別設定パラメータ
    
    Returns:
        実行結果辞書
    """
    # 1. パス解決
    paths = self._resolve_paths(**options)
    
    # 2. 設定検証
    validation_result = self._validate_configuration(paths)
    if not validation_result['valid']:
        return {'status': 'error', 'details': validation_result}
    
    # 3. 実行計画生成
    if options.get('show_plan'):
        return self.show_execution_plan(**options)
    
    # 4. 強制再処理モード
    if options.get('force_reprocess'):
        return self.force_reprocess(**options)
    
    # 5. 通常実行
    return self._execute_workflow(paths, **options)
```

#### _execute_workflow() - ワークフロー実行
```python
def _execute_workflow(self, paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    実際のワークフロー実行
    
    処理順序:
    1. organize: ファイル整理
    2. sync: 同期チェック
    3. fetch: 引用文献取得
    4. ai-citation-support: AI理解支援統合
    5. tagger: タグ生成 (有効時)
    6. translate_abstract: 要約翻訳 (有効時)
    7. final-sync: 最終同期
    """
    
    execution_results = {
        'status': 'success',
        'executed_steps': [],
        'skipped_steps': [],
        'failed_steps': [],
        'total_papers_processed': 0,
        'execution_time': 0
    }
    
    try:
        start_time = time.time()
        
        # 処理対象論文の決定
        target_papers = self._determine_target_papers(paths, options)
        
        # ステップ実行
        steps = [
            ('organize', self.organize_workflow),
            ('sync', self.sync_workflow),
            ('fetch', self.fetch_workflow),
            ('ai-citation-support', self.ai_citation_support_workflow),
            ('tagger', self.tagger_workflow),
            ('translate_abstract', self.translate_abstract_workflow),
            ('final-sync', self.sync_workflow)
        ]
        
        for step_name, workflow in steps:
            if self._should_skip_step(step_name, options):
                execution_results['skipped_steps'].append(step_name)
                continue
                
            if self._execute_step(step_name, workflow, paths, target_papers, options):
                execution_results['executed_steps'].append(step_name)
            else:
                execution_results['failed_steps'].append(step_name)
                execution_results['status'] = 'partial_failure'
                break
        
        execution_results['execution_time'] = time.time() - start_time
        return execution_results
        
    except Exception as e:
        self.logger.error(f"Workflow execution failed: {str(e)}")
        execution_results['status'] = 'error'
        execution_results['error'] = str(e)
        return execution_results
```

#### _execute_step() - 個別ステップ実行
```python
def _execute_step(self, step_name: str, workflow: Any, paths: Dict[str, str], 
                 target_papers: List[str], options: Dict[str, Any]) -> bool:
    """
    個別ステップの実行
    
    Args:
        step_name: ステップ名
        workflow: ワークフローオブジェクト
        paths: パス設定
        target_papers: 対象論文リスト
        options: 実行オプション
    
    Returns:
        実行成功時 True
    """
    
    try:
        self.logger.info(f"Starting step: {step_name}")
        
        # 処理対象論文の取得
        papers_needing_processing = self.status_manager.get_papers_needing_processing(
            paths['clippings_dir'], step_name, target_papers
        )
        
        if not papers_needing_processing:
            self.logger.info(f"No papers need processing for step: {step_name}")
            return True
        
        # ステップ別処理実行
        if step_name == 'organize':
            result = workflow.process_papers(paths['clippings_dir'], papers_needing_processing)
        elif step_name in ['sync', 'final-sync']:
            result = workflow.check_sync(paths['bibtex_file'], paths['clippings_dir'])
        elif step_name == 'fetch':
            result = workflow.fetch_citations(paths['bibtex_file'], papers_needing_processing)
        elif step_name == 'ai-citation-support':
            result = workflow.process_papers(paths['clippings_dir'], papers_needing_processing)
        elif step_name == 'tagger':
            if options.get('enable_tagger', False):
                result = workflow.process_papers(paths['clippings_dir'], papers_needing_processing)
            else:
                self.logger.info("Tagger disabled, skipping")
                return True
        elif step_name == 'translate_abstract':
            if options.get('enable_translate_abstract', False):
                result = workflow.process_papers(paths['clippings_dir'], papers_needing_processing)
            else:
                self.logger.info("Abstract translation disabled, skipping")
                return True
        
        # 結果に基づく状態更新
        if result.get('status') == 'success':
            for paper in papers_needing_processing:
                self.status_manager.update_status(
                    paths['clippings_dir'], paper, step_name, ProcessStatus.COMPLETED
                )
            self.logger.info(f"Step {step_name} completed successfully")
            return True
        else:
            for paper in papers_needing_processing:
                self.status_manager.update_status(
                    paths['clippings_dir'], paper, step_name, ProcessStatus.FAILED
                )
            self.logger.error(f"Step {step_name} failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        self.logger.error(f"Step {step_name} execution failed: {str(e)}")
        return False
```

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
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-tagger --enable-translate-abstract
```

### 個別設定
```bash
# ワークスペース指定
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --papers "smith2023,jones2024"

# 特定ステップをスキップ
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --skip-steps "sync,final-sync"
```

## エラーハンドリング

### 段階的エラー処理
- **設定エラー**: 実行前に設定検証、エラー時は実行停止
- **ステップエラー**: 失敗ステップで実行停止、状態は失敗として記録
- **部分的失敗**: 一部論文の失敗時は続行、全体結果に反映

### 復旧機能
- **状態リセット**: `--force-reprocess`での全状態初期化
- **個別再実行**: 失敗論文のみの再処理
- **依存関係チェック**: 前段階未完了時の自動スキップ

## 実行結果形式

### 成功時
```python
{
    'status': 'success',
    'executed_steps': ['organize', 'sync', 'fetch', 'ai-citation-support'],
    'skipped_steps': ['tagger', 'translate_abstract'],
    'failed_steps': [],
    'total_papers_processed': 5,
    'execution_time': 120.5,
    'details': {
        'organize': {'processed': 2, 'skipped': 3},
        'sync': {'status': 'consistent'},
        'fetch': {'fetched': 15, 'failed': 0},
        'ai-citation-support': {'processed': 5, 'citations_added': 47}
    }
}
```

### 失敗時
```python
{
    'status': 'error',
    'executed_steps': ['organize', 'sync'],
    'skipped_steps': [],
    'failed_steps': ['fetch'],
    'error': 'API connection failed',
    'execution_time': 45.2
}
```

## パフォーマンス最適化

### 並列処理
- **AI機能**: バッチ処理による並列API呼び出し
- **ファイル操作**: 複数論文の同時処理
- **ネットワーク**: 非同期API通信

### キャッシュ機能
- **設定情報**: 実行中の設定キャッシュ
- **状態情報**: メモリ内状態管理
- **API結果**: 一時的な結果キャッシュ

### リソース管理
- **メモリ使用量**: 大量論文処理時の最適化
- **API制限**: レート制限の適切な管理
- **ディスク容量**: 一時ファイルの適切な削除

---

**統合ワークフロー仕様書バージョン**: 3.1.0