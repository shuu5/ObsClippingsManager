# Enhanced Integrated Workflow 仕様書 v2.2

## 概要
Enhanced Integrated Workflow（拡張統合ワークフロー）は、ObsClippingsManager v2.2で導入された状態管理ベースの効率的な論文処理システムです。各論文の処理状態をBibTeXファイル内で追跡し、必要な処理のみを実行することで、大幅な処理時間短縮を実現します。

## アーキテクチャ

### システム構成
```
Enhanced Integrated Workflow
├── StatusManager              # 状態管理システム
│   ├── BibTeX状態フィールド追跡
│   ├── 処理ステップ状態管理
│   └── 整合性チェック機能
├── EnhancedIntegratedWorkflow # 実行エンジン
│   ├── Smart Skip Logic実装
│   ├── 依存関係解決
│   └── 段階的実行制御
└── CLI Integration           # コマンドライン統合
    ├── Enhanced Modeオプション
    ├── 実行計画表示
    └── 強制再生成機能
```

## 状態管理システム（StatusManager）

### 状態フィールド定義
BibTeXファイル内の各エントリに以下のカスタムフィールドを追加：

```bibtex
@article{smith2023,
    title = {Example Paper},
    author = {Smith, John},
    year = {2023},
    doi = {10.1000/example.doi},
    obsclippings_organize_status = {completed},
    obsclippings_sync_status = {completed},
    obsclippings_fetch_status = {pending},
    obsclippings_parse_status = {pending}
}
```

### 状態値定義
- **pending**: 処理が必要（初期状態・失敗後の再処理待ち）
- **completed**: 処理完了
- **failed**: 処理失敗（次回実行時に再処理対象）

### 処理フロー
1. **organize**: ファイル整理（Markdownファイル → citation keyディレクトリ）
2. **sync**: 同期チェック（BibTeX ↔ Clippingsディレクトリ対応確認）
3. **fetch**: 引用文献取得（DOI → references.bib生成）
4. **parse**: 引用文献解析（Markdownファイル内の引用パース）

### 依存関係
```
organize → sync → fetch → parse
```
- 前段階が完了していない場合、後段階は実行されない
- 失敗した段階以降は全て再実行対象となる

### 主要メソッド

#### StatusManager.load_bib_statuses(bibtex_file)
```python
def load_bib_statuses(self, bibtex_file: str) -> Dict[str, Dict[str, str]]:
    """
    BibTeXファイルから処理状態を読み込み
    
    Returns:
        {
            "citation_key": {
                "organize": "completed",
                "sync": "pending",
                "fetch": "pending", 
                "parse": "pending"
            }
        }
    """
```

#### StatusManager.update_status(bibtex_file, citation_key, step, status)
```python
def update_status(self, bibtex_file: str, citation_key: str, 
                 step: str, status: ProcessStatus) -> bool:
    """
    特定論文の特定ステップの状態を更新
    
    Args:
        step: "organize" | "sync" | "fetch" | "parse"
        status: ProcessStatus.COMPLETED | ProcessStatus.FAILED
    """
```

#### StatusManager.reset_statuses(bibtex_file, target_papers=None)
```python
def reset_statuses(self, bibtex_file: str, 
                  target_papers: Optional[List[str]] = None) -> bool:
    """
    強制再生成：指定論文（またはすべて）の状態をpendingにリセット
    """
```

#### StatusManager.check_status_consistency(bibtex_file, clippings_dir)
```python
def check_status_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict:
    """
    BibTeXエントリとClippingsディレクトリの整合性チェック
    
    Returns:
        {
            "missing_in_clippings": ["key1", "key2"],  # BibにあってClippingsにない
            "orphaned_directories": ["key3", "key4"],  # Clippingsにあって BibTeXにない
            "status_inconsistencies": [...]             # 状態と実際の乖離
        }
    """
```

## Enhanced統合ワークフロー（EnhancedIntegratedWorkflow）

### Smart Skip Logic
処理状態に基づいて、必要な処理のみを効率的に実行します。

#### 実行判定ロジック
```python
def analyze_paper_status(self, bibtex_file: str) -> Dict:
    """
    各論文の処理必要性を分析
    
    例：
    論文A: organize(completed) → sync(pending) → fetch(pending) → parse(pending)
    論文B: organize(pending) → sync(pending) → fetch(pending) → parse(pending)
    
    結果：
    {
        "organize": ["論文B"],           # 論文Bのみorganize実行
        "sync": ["論文A", "論文B"],       # 両方sync実行
        "fetch": ["論文A", "論文B"],      # 両方fetch実行  
        "parse": ["論文A", "論文B"]       # 両方parse実行
    }
    """
```

#### 実行計画生成
```python
def get_execution_plan(self, bibtex_file: str, target_papers: Optional[List[str]] = None) -> Dict:
    """
    実行計画を生成（実際には実行しない）
    
    Returns:
        {
            "total_papers": 5,
            "total_tasks": 15,
            "execution_steps": {
                "organize": ["paper1", "paper2"],
                "sync": ["paper1", "paper2", "paper3"],
                "fetch": ["paper2", "paper3"],
                "parse": ["paper2", "paper3"]
            }
        }
    """
```

### 実行メソッド

#### execute_step_by_step()
```python
def execute_step_by_step(self, bibtex_file: str, clippings_dir: str,
                        target_papers: Optional[List[str]] = None) -> Dict:
    """
    ステップ別統合ワークフロー実行
    
    1. 現在の状態を解析
    2. 各ステップを順番に実行
    3. 実行後に状態を更新
    4. 失敗時は適切な状態に設定
    """
```

#### execute_force_regenerate()
```python
def execute_force_regenerate(self, bibtex_file: str, clippings_dir: str,
                           target_papers: Optional[List[str]] = None) -> Dict:
    """
    強制再生成モード実行
    
    1. 対象論文の全状態をpendingにリセット
    2. 通常の step_by_step 実行
    """
```

#### check_consistency()
```python
def check_consistency(self, bibtex_file: str, clippings_dir: str) -> Dict:
    """
    整合性チェック
    
    Returns:
        {
            "status": "success" | "warning" | "error",
            "details": {
                "missing_in_clippings": [...],
                "orphaned_directories": [...],
                "status_inconsistencies": [...]
            }
        }
    """
```

## CLI統合

### Enhanced Modeオプション
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated [OPTIONS]
```

#### 基本オプション
- `--enhanced-mode`: Enhanced統合ワークフローを有効化
- `-b, --bibtex-file PATH`: BibTeXファイルパス（必須）
- `-d, --clippings-dir PATH`: Clippingsディレクトリパス（必須）

#### 制御オプション
- `--force-regenerate`: 全処理状態フラグをリセットして実行
- `--papers TEXT`: カンマ区切りで特定論文のみ処理（citation key指定）

#### 情報表示オプション
- `--show-execution-plan`: 実行計画のみ表示（実際には実行しない）
- `--check-consistency`: BibTeXファイルとClippingsディレクトリの整合性チェック

### 使用例

#### 1. 実行計画確認
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --show-execution-plan \
  -b /home/user/ManuscriptsManager/CurrentManuscript.bib \
  -d /home/user/ManuscriptsManager/Clippings

# 出力例
📋 Analyzing execution plan...
📊 Execution Plan: 20 tasks across 4 steps
📄 Total papers: 5 papers

organize: 2 papers
  Target papers: smith2023, jones2024

sync: 5 papers  
  Target papers: smith2023, jones2024, wang2022, brown2021, davis2020

fetch: 3 papers
  Target papers: jones2024, wang2022, brown2021

parse: 3 papers
  Target papers: jones2024, wang2022, brown2021
```

#### 2. 整合性チェック
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --check-consistency \
  -b /home/user/ManuscriptsManager/CurrentManuscript.bib \
  -d /home/user/ManuscriptsManager/Clippings

# 出力例
🔍 Checking consistency between BibTeX and Clippings directory...
✅ Consistency check completed

📊 Results:
- BibTeX entries: 5
- Clippings directories: 5
- Perfect match: All entries have corresponding directories
```

#### 3. Enhanced Mode実行
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode \
  -b /home/user/ManuscriptsManager/CurrentManuscript.bib \
  -d /home/user/ManuscriptsManager/Clippings

# 出力例
🚀 Starting Enhanced Integrated Workflow...
📊 Execution Plan: 15 tasks across 4 steps

Step 1/4: organize (2 papers)
✅ organize: smith2023 - completed
✅ organize: jones2024 - completed

Step 2/4: sync (5 papers)  
✅ sync: smith2023 - completed
✅ sync: jones2024 - completed
⏭️  sync: wang2022 - skipped (already completed)
⏭️  sync: brown2021 - skipped (already completed)
⏭️  sync: davis2020 - skipped (already completed)

# ... 他のステップも同様に表示
```

#### 4. 特定論文のみ処理
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode \
  --papers "smith2023,jones2024" \
  -b /home/user/ManuscriptsManager/CurrentManuscript.bib \
  -d /home/user/ManuscriptsManager/Clippings
```

#### 5. 強制再生成
```bash
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --enhanced-mode --force-regenerate \
  -b /home/user/ManuscriptsManager/CurrentManuscript.bib \
  -d /home/user/ManuscriptsManager/Clippings

# 全論文の全ステップが pending 状態にリセットされて実行
```

## パフォーマンス最適化

### Smart Skip Logicによる効率化
- **従来モード**: 全論文・全ステップを毎回実行
- **Enhanced Mode**: 必要な処理のみを実行

#### 処理時間比較例
```
5論文の処理時間（概算）:

従来モード:
- organize: 5論文 × 30秒 = 150秒
- sync: 5論文 × 10秒 = 50秒  
- fetch: 5論文 × 60秒 = 300秒
- parse: 5論文 × 20秒 = 100秒
合計: 600秒 (10分)

Enhanced Mode（2回目以降実行時）:
- organize: 0論文（全て完了済み） = 0秒
- sync: 1論文（新規追加のみ） × 10秒 = 10秒
- fetch: 1論文（新規追加のみ） × 60秒 = 60秒 
- parse: 1論文（新規追加のみ） × 20秒 = 20秒
合計: 90秒 (1.5分) - 約85%短縮
```

### メモリ使用量最適化
- 処理対象論文の絞り込みによるメモリ使用量削減
- 段階的処理による最大メモリ使用量の平準化

## エラーハンドリング

### 状態管理エラー
- **BibTeXファイル読み込み失敗**: ファイル存在・権限確認
- **状態更新失敗**: BibTeX構文エラー・書き込み権限エラー
- **整合性チェック失敗**: Clippingsディレクトリ不存在・権限エラー

### ワークフロー実行エラー
- **ステップ実行失敗**: 該当ステップを"failed"状態に更新
- **依存関係違反**: 前段階未完了時の適切なエラーメッセージ
- **ファイルシステムエラー**: 適切なリトライ・フォールバック処理

### エラー復旧戦略
1. **自動復旧**: 一時的なネットワークエラー等のリトライ
2. **状態復旧**: 失敗状態からの適切な再開
3. **手動復旧**: 構成問題等のユーザー介入が必要な場合の明確なガイダンス

## テスト仕様

### テストカバレッジ
- **StatusManager**: 10個のテスト
- **EnhancedIntegratedWorkflow**: 9個のテスト
- **CLI統合**: 既存のmain_cliテストに追加

### テストケース詳細

#### StatusManagerテスト
```python
# test_status_management.py
- test_load_empty_bibtex()           # 空BibTeXファイル処理
- test_load_bibtex_with_status()     # 状態付きBibTeX読み込み
- test_load_bibtex_without_status()  # 状態なしBibTeX読み込み
- test_update_status_success()       # 正常な状態更新
- test_update_status_nonexistent()   # 存在しない論文への状態更新
- test_reset_statuses_all()         # 全論文状態リセット
- test_reset_statuses_specific()    # 特定論文状態リセット
- test_consistency_check_perfect()  # 完全整合性
- test_consistency_check_missing()  # 不整合検出
- test_bibtex_syntax_preservation() # BibTeX構文保持
```

#### EnhancedIntegratedWorkflowテスト
```python  
# test_enhanced_run_integrated.py
- test_workflow_initialization()                    # ワークフロー初期化
- test_analyze_paper_status()                      # 論文状態分析
- test_get_execution_plan()                        # 実行計画生成
- test_smart_skip_logic()                          # Smart Skip Logic
- test_execute_step_by_step()                      # ステップ別実行
- test_execute_with_status_tracking()              # 状態追跡付き実行
- test_force_regenerate_mode()                     # 強制再生成モード
- test_consistency_check_with_missing_directories() # ディレクトリ不足時整合性
- test_consistency_check_with_orphaned_directories() # 孤立ディレクトリ整合性
```

### Mock/Stubテスト戦略
- **WorkflowManager**: 各ワークフローの実行結果をMock化
- **ファイルシステム**: 一時ディレクトリでのテスト実行
- **BibTeX操作**: 実際のパース・更新処理をテスト

## 互換性・移行ガイド

### 既存システムとの互換性
- **従来モード完全維持**: Enhanced Modeは追加機能として実装
- **BibTeX互換性**: カスタムフィールドは標準BibTeX構文に準拠
- **既存ワークフロー**: 全て既存APIを維持

### 移行ステップ
1. **現在のBibTeXファイルバックアップ**
2. **Enhanced Mode試行**: `--show-execution-plan`で動作確認
3. **段階的移行**: 小規模データセットでの動作確認
4. **本格移行**: 全データでのEnhanced Mode運用開始

### 移行時の注意点
- **初回実行**: 状態フィールド未設定のため、全論文が処理対象
- **BibTeXファイル変更**: カスタムフィールドが追加される
- **バージョン管理**: BibTeXファイルの変更履歴管理推奨

---

**Enhanced Integrated Workflow仕様書バージョン**: 2.2.0  
**実装日**: 2024年  
**対応システム**: ObsClippingsManager v2.2  
**Smart Skip Logic**: 実装済み・テスト済み 