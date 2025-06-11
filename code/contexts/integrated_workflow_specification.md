# 統合ワークフロー仕様書 v4.0

## 概要
統合ワークフロー（Integrated Workflow）は、ObsClippingsManager v4.0の中核機能であり、すべての処理を`run-integrated`コマンド一つで完結させるシンプルかつ効率的なシステムです。状態管理により重複処理を自動回避し、デフォルト設定での引数なし実行を実現します。

**v4.0新機能**: AI理解支援引用文献パーサー機能により、AIアシスタント（ChatGPT、Claude等）が論文の引用文献を完全に理解できる自己完結型ファイル生成機能を追加。

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
- **AI理解支援処理状態**の追跡

### 統一ディレクトリ設定
- **workspace_path**一つでの全パス管理
- **自動導出**による設定シンプル化
- **個別指定**での柔軟性確保

## システム構成

### 処理フロー v4.0
```
1. organize  →  2. sync  →  3. fetch  →  4. ai-citation-support
    ↓             ↓           ↓            ↓
 ファイル整理   同期チェック  引用取得    AI理解支援統合
```

### 依存関係
- 各ステップは**順次実行**
- **前段階完了**後に次段階実行
- **失敗時は後続ステップ停止**
- **ai-citation-support**は**fetch完了後**に実行

### 状態追跡
- 各論文の`.md`ファイルYAMLヘッダーで状態管理
- ステップごとの処理状態を記録
- 完了/失敗/保留の状態管理
- **AI理解支援処理状態**の追跡

## 統一設定システム

### デフォルト設定
```yaml
# config/config.yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"

# AI理解支援設定（v4.0新機能）
ai_citation_support:
  enabled: false                    # デフォルトは無効
  complete_mapping: true            # 完全統合マッピング作成
  update_yaml_header: true          # YAMLヘッダー更新
  backup_original: true             # 元ファイルバックアップ
  include_abstracts: true           # 要約情報の含有
```

### 設定優先順位
1. **コマンドライン引数** (最高優先度)
2. **設定ファイル** (config.yaml)
3. **デフォルト値** (最低優先度)

### パス解決
```python
def resolve_paths(workspace_path: str = None, **kwargs) -> Dict[str, str]:
    """
    統一パス解決システム
    
    Args:
        workspace_path: ワークスペースルートパス
        **kwargs: 個別指定パス (bibtex_file, clippings_dir等)
    
    Returns:
        解決済みパス辞書
    """
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
        self.ai_citation_support_workflow = AICitationSupportWorkflow(config_manager, logger)  # v4.0新機能
    
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
            skip_steps: スキップステップリスト (カンマ区切り文字列)
            force_reprocess: 強制再処理フラグ
            show_plan: 実行計画表示フラグ
            enable_ai_citation_support: AI理解支援機能有効化（v4.0新機能）
            ai_output_dir: AI用ファイル出力ディレクトリ（v4.0新機能）
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
    """
    results = {
        'status': 'success',
        'completed_steps': [],
        'skipped_steps': [],
        'failed_steps': [],
        'total_papers': 0,
        'processed_papers': 0
    }
    
    # 対象論文決定
    target_papers = self._determine_target_papers(paths, options.get('papers'))
    results['total_papers'] = len(target_papers)
    
    # スキップステップ処理
    skip_steps = self._parse_skip_steps(options.get('skip_steps', ''))
    
    # ステップ実行（v4.0ではai-citation-supportステップを追加）
    steps = ['organize', 'sync', 'fetch']
    
    # AI理解支援機能が有効な場合はai-citation-supportステップを追加
    if options.get('enable_ai_citation_support'):
        steps.append('ai-citation-support')
    
    for step in steps:
        if step in skip_steps:
            self.logger.info(f"Skipping step: {step}")
            results['skipped_steps'].append(step)
            continue
        
        # 処理が必要な論文を特定
        papers_needing_processing = self.status_manager.get_papers_needing_processing(
            paths['clippings_dir'], step, target_papers
        )
        
        if not papers_needing_processing:
            self.logger.info(f"Step {step}: All papers already processed")
            results['skipped_steps'].append(step)
            continue
        
        # ステップ実行
        step_result = self._execute_step(step, papers_needing_processing, paths, **options)
        
        if step_result['status'] == 'success':
            results['completed_steps'].append(step)
            results['processed_papers'] += step_result.get('processed_count', 0)
        else:
            results['failed_steps'].append(step)
            results['status'] = 'partial_failure'
            # 失敗時は後続ステップを停止
            break
    
    return results
```

#### _execute_step() - 個別ステップ実行
```python
def _execute_step(self, step: str, papers: List[str], paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    個別ステップの実行
    
    Args:
        step: 実行ステップ名 ('organize'|'sync'|'fetch'|'ai-citation-support')
        papers: 対象論文リスト
        paths: 解決済みパス辞書
        **options: 実行オプション
    
    Returns:
        ステップ実行結果
    """
    self.logger.info(f"Executing step: {step} for {len(papers)} papers")
    
    try:
        if step == 'organize':
            result = self._execute_organize_step(papers, paths, **options)
        elif step == 'sync':
            result = self._execute_sync_step(papers, paths, **options)
        elif step == 'fetch':
            result = self._execute_fetch_step(papers, paths, **options)
        elif step == 'ai-citation-support':  # v4.0新機能
            result = self._execute_ai_citation_support_step(papers, paths, **options)
        else:
            raise ValueError(f"Unknown step: {step}")
        
        # 成功時状態更新
        if result.get('status') == 'success':
            for paper in result.get('successful_papers', []):
                self.status_manager.update_status(
                    paths['clippings_dir'], paper, step, ProcessStatus.COMPLETED
                )
        
        # 失敗時状態更新
        for paper in result.get('failed_papers', []):
            self.status_manager.update_status(
                paths['clippings_dir'], paper, step, ProcessStatus.FAILED
            )
        
        return result
        
    except Exception as e:
        self.logger.error(f"Step {step} failed: {str(e)}")
        
        # 全論文を失敗状態に設定
        for paper in papers:
            self.status_manager.update_status(
                paths['clippings_dir'], paper, step, ProcessStatus.FAILED
            )
        
        return {
            'status': 'error',
            'error': str(e),
            'failed_papers': papers
        }
```

## 各ステップの実装

### 1. organize ステップ
```python
def _execute_organize_step(self, papers: List[str], paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    ファイル整理ステップ実行
    
    機能:
    - Markdownファイルをcitation keyディレクトリに整理
    - BibTeX DOIとの照合
    - ディレクトリ構造の作成
    """
    organize_options = {
        'bibtex_file': paths['bibtex_file'],
        'clippings_dir': paths['clippings_dir'],
        'target_papers': papers,
        **self._extract_organize_options(**options)
    }
    
    return self.organize_workflow.execute(organize_options)
```

### 2. sync ステップ
```python
def _execute_sync_step(self, papers: List[str], paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    同期チェックステップ実行
    
    機能:
    - BibTeX ↔ Clippingsディレクトリ整合性確認
    - 不足論文の検出
    - 整合性レポート生成
    """
    sync_options = {
        'bibtex_file': paths['bibtex_file'],
        'clippings_dir': paths['clippings_dir'],
        'target_papers': papers,
        **self._extract_sync_options(**options)
    }
    
    return self.sync_workflow.execute(sync_options)
```

### 3. fetch ステップ
```python
def _execute_fetch_step(self, papers: List[str], paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    引用文献取得ステップ実行
    
    機能:
    - DOIから引用文献を取得
    - references.bib生成
    - メタデータ補完
    """
    fetch_options = {
        'bibtex_file': paths['bibtex_file'],
        'output_dir': paths['output_dir'],
        'target_papers': papers,
        **self._extract_fetch_options(**options)
    }
    
    return self.fetch_workflow.execute(fetch_options)
```

### 4. ai-citation-support ステップ（v4.0新機能）
```python
def _execute_ai_citation_support_step(self, papers: List[str], paths: Dict[str, str], **options) -> Dict[str, Any]:
    """
    AI理解支援統合ステップ実行（v4.0新機能）
    
    機能:
    - YAMLヘッダーに軽量引用マッピング追加
    - AI理解用統合ファイル生成
    - Citation Reference Table作成
    - AI最適化フォーマット出力
    """
    ai_citation_support_options = {
        'clippings_dir': paths['clippings_dir'],
        'bibtex_file': paths['bibtex_file'],
        'ai_output_dir': options.get('ai_output_dir', f"{paths['workspace_path']}/AI_Ready"),
        'target_papers': papers,
        'generate_mapping': options.get('generate_mapping', True),
        'generate_unified_file': options.get('generate_unified_file', True),
        'backup_original': options.get('backup_original', True),
        'complete_mapping': options.get('complete_mapping', True),
        'update_yaml_header': options.get('update_yaml_header', True),
        'include_abstracts': options.get('include_abstracts', True),
        **self._extract_ai_citation_support_options(**options)
    }
    
    return self.ai_citation_support_workflow.execute(ai_citation_support_options)
```

## 実行計画システム

### show_execution_plan() - 実行計画表示
```python
def show_execution_plan(self, **options) -> Dict[str, Any]:
    """
    実行計画の表示（実際には実行しない）
    
    Returns:
        {
            'total_papers': 10,
            'execution_plan': {
                'organize': {
                    'papers_to_process': ['smith2023', 'jones2024'],
                    'papers_completed': ['brown2022'],
                    'estimated_time': '2 minutes'
                },
                'sync': {...},
                'fetch': {...},
                'ai-citation-support': {...}
            },
            'estimated_total_time': '15 minutes'
        }
    """
    paths = self._resolve_paths(**options)
    target_papers = self._determine_target_papers(paths, options.get('papers'))
    skip_steps = self._parse_skip_steps(options.get('skip_steps', ''))
    
    plan = {
        'total_papers': len(target_papers),
        'execution_plan': {},
        'estimated_total_time': '0 minutes'
    }
    
    steps = ['organize', 'sync', 'fetch', 'ai-citation-support']
    total_estimated_seconds = 0
    
    for step in steps:
        if step in skip_steps:
            plan['execution_plan'][step] = {
                'status': 'skipped',
                'reason': 'User requested skip'
            }
            continue
        
        papers_needing_processing = self.status_manager.get_papers_needing_processing(
            paths['clippings_dir'], step, target_papers
        )
        
        papers_completed = [p for p in target_papers if p not in papers_needing_processing]
        
        estimated_seconds = len(papers_needing_processing) * self._get_step_time_estimate(step)
        total_estimated_seconds += estimated_seconds
        
        plan['execution_plan'][step] = {
            'papers_to_process': papers_needing_processing,
            'papers_completed': papers_completed,
            'papers_count': len(papers_needing_processing),
            'estimated_time': f"{estimated_seconds // 60} minutes {estimated_seconds % 60} seconds"
        }
    
    plan['estimated_total_time'] = f"{total_estimated_seconds // 60} minutes {total_estimated_seconds % 60} seconds"
    
    return plan
```

## CLI統合

### コマンドライン定義
```python
@click.command('run-integrated')
@click.option('-w', '--workspace', 'workspace_path', 
              help='ワークスペースパス (デフォルト: /home/user/ManuscriptsManager)')
@click.option('--bibtex-file', help='BibTeXファイルパス (個別指定)')
@click.option('--clippings-dir', help='Clippingsディレクトリパス (個別指定)')
@click.option('--output-dir', help='出力ディレクトリパス (個別指定)')
@click.option('--papers', help='対象論文 (カンマ区切り)')
@click.option('--skip-steps', help='スキップステップ (カンマ区切り)')
@click.option('--show-plan', is_flag=True, help='実行計画表示')
@click.option('--force-reprocess', is_flag=True, help='強制再処理')
@click.option('-n', '--dry-run', is_flag=True, help='ドライラン実行')
@click.option('-v', '--verbose', is_flag=True, help='詳細出力')
@click.option('-c', '--config', 'config_file', help='設定ファイルパス')
@click.option('-l', '--log-level', 
              type=click.Choice(['debug', 'info', 'warning', 'error']),
              default='info', help='ログレベル')
@click.option('--enable-ai-citation-support', is_flag=True, help='AI理解支援機能有効化（v4.0新機能）')
@click.option('--ai-output-dir', help='AI用ファイル出力ディレクトリ（v4.0新機能）')
@click.option('--generate-mapping', is_flag=True, default=True, help='引用マッピング生成（v4.0新機能）')
@click.option('--generate-unified-file', is_flag=True, default=True, help='AI用統合ファイル生成（v4.0新機能）')
def run_integrated(**options):
    """統合ワークフロー実行"""
    
    # 設定初期化
    config_manager = ConfigManager(options.get('config_file'))
    logger = IntegratedLogger(
        log_level=options.get('log_level', 'info'),
        verbose=options.get('verbose', False)
    )
    
    # ワークフロー実行
    workflow = IntegratedWorkflow(config_manager, logger)
    
    try:
        result = workflow.execute(**options)
        
        # 結果表示
        if result['status'] == 'success':
            click.echo(f"✅ 統合ワークフロー完了: {result['processed_papers']}/{result['total_papers']} 論文処理")
        elif result['status'] == 'partial_failure':
            click.echo(f"⚠️  部分的成功: {result['processed_papers']}/{result['total_papers']} 論文処理")
        else:
            click.echo(f"❌ 実行失敗: {result.get('error', '不明なエラー')}")
            
    except Exception as e:
        logger.get_logger('CLI').error(f"統合ワークフロー実行エラー: {str(e)}")
        click.echo(f"❌ エラー: {str(e)}")
```

## 使用例

### 基本実行
```bash
# デフォルト実行（引数なし）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 詳細ログ付き実行
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --verbose --log-level debug
```

### 個別制御
```bash
# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --papers "smith2023,jones2024"

# 特定ステップをスキップ
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --skip-steps "fetch"

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess

# AI理解支援機能有効化（v4.0新機能）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-ai-citation-support

# AI理解支援機能（カスタム出力ディレクトリ）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --enable-ai-citation-support \
    --ai-output-dir "/path/to/ai_ready_files"
```

### ワークスペース変更
```bash
# 異なるワークスペース
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/project"

# 個別ファイル指定
PYTHONPATH=code/py uv run python code/py/main.py run-integrated \
    --bibtex-file "/path/to/manuscript.bib" \
    --clippings-dir "/path/to/clippings" \
    --output-dir "/path/to/output"
```

---

## v4.0の革新ポイント

### AI理解支援機能の追加
- **ai-citation-supportステップ**: 引用文献パース後にAI理解用ファイルを自動生成
- **軽量マッピング**: YAMLヘッダーに最小限の引用情報を追加
- **統合ファイル生成**: AIが完全に理解できるCitation Reference Table付きファイル作成
- **シームレス統合**: run-integratedコマンドで全機能を一括実行

### 使用シナリオ
```bash
# 論文執筆完了後、AI用ファイルを自動生成
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enable-ai-citation-support

# 生成されたファイルをAIアシスタントに提供
# → AIが[1],[2],[3]の引用文献を完全理解
# → 高品質な論文執筆・要約・分析が可能
```

### 期待される効果
- **AIアシスタント活用の革命的改善**: 引用文献理解によるAI論文支援の飛躍的向上
- **作業効率向上**: 人間のAI論文執筆依頼準備時間の大幅短縮  
- **データ品質維持**: 軽量設計による情報重複回避と整合性確保

---

**統合ワークフロー仕様書バージョン**: 4.0.0