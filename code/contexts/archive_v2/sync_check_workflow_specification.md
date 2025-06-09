# 同期チェックワークフロー仕様書 v2.0

## 概要
同期チェックワークフロー（`SyncCheckWorkflow`）は、ObsClippingsManager v2.0 において、ManuscriptsManager/CurrentManuscript.bibファイルとManuscriptsManager/Clippings/内のcitation_keyサブディレクトリの整合性を確認し、不一致を報告する機能です。

**v2.0 の特徴:**
- BibTeXファイルとClippingsディレクトリの双方向整合性チェック
- 不足論文の詳細情報表示（タイトル、DOI、ウェブリンク）
- ブラウザでのDOIリンク自動開放機能
- 統合ログシステムによる詳細な実行記録

## 機能目的
- CurrentManuscript.bibに記載された論文の存在確認
- Clippings/内のサブディレクトリとの一致性検証
- 不一致の詳細報告とユーザー通知
- 研究管理の整合性確保支援

## ワークフロー構成

```
modules/workflows/sync_check_workflow.py
└── SyncCheckWorkflow クラス
    ├── execute()                    # メイン実行メソッド
    ├── check_bib_to_clippings()     # .bib → Clippings チェック
    ├── check_clippings_to_bib()     # Clippings → .bib チェック
    ├── report_missing_papers()      # 不足論文の報告
    └── open_doi_links()            # DOIリンクの自動開放
```

## 入力・出力仕様

### 入力
- **BibTeXファイル**: `/home/user/ManuscriptsManager/CurrentManuscript.bib`
- **Clippingsディレクトリ**: `/home/user/ManuscriptsManager/Clippings/`

### 出力
1. **不一致レポート**: コンソール出力
2. **ログファイル**: 詳細な実行記録
3. **DOIリンク**: ブラウザでの自動開放（オプション）

### チェック対象
```
CurrentManuscript.bib          ←→  Clippings/
├── paper1 (citation_key)      ←→  ├── paper1/paper1.md
├── paper2 (citation_key)      ←→  ├── paper2/paper2.md
├── paper3 (citation_key)      ←→  ├── paper3/ (存在しない)
└── (存在しない)               ←→  └── orphan_paper/orphan_paper.md
```

## 主要機能

### 1. BibTeX → Clippings チェック
.bibファイルに記載された各citation_keyに対応するClippings/内のサブディレクトリの存在を確認します。

**処理内容:**
- BibTeX項目の解析
- citation_keyリストの抽出
- Clippings/内サブディレクトリとの照合
- 不足論文の詳細情報収集（タイトル、DOI、著者、年）

### 2. Clippings → BibTeX チェック
Clippings/内のサブディレクトリに対応するBibTeX項目の存在を確認します。

**処理内容:**
- Clippings/内サブディレクトリの一覧取得
- BibTeX項目との照合
- 孤立ディレクトリの検出
- Markdownファイル一覧の取得

### 3. 不足論文の報告
不一致情報を詳細に報告し、ユーザーに必要なアクションを提示します。

**報告内容:**
- **不足論文情報**: タイトル、著者、発行年、DOI
- **クリック可能DOIリンク**: ターミナルでクリック可能なリンク表示
- **統計情報**: DOI対応/未対応論文数、カバレッジ率
- **アクション提案**: 追加すべき論文やファイルの詳細

### 4. DOIリンク自動開放機能（新機能）
不足論文のDOIリンクを自動でブラウザ開放し、論文取得を支援します。

**機能詳細:**
- 有効なDOIの検証
- `https://doi.org/` 形式でのURL生成
- システムデフォルトブラウザでの自動開放
- リンク開放の成功・失敗ログ

## 実行方法

### 基本実行
```bash
# 基本的な同期チェック
PYTHONPATH=code/py uv run python code/py/main.py sync-check

# ドライラン実行
PYTHONPATH=code/py uv run python code/py/main.py sync-check --dry-run

# 詳細ログ付き実行
PYTHONPATH=code/py uv run python code/py/main.py sync-check --verbose
```

### 主要オプション
```bash
# DOIリンクの自動開放
PYTHONPATH=code/py uv run python code/py/main.py sync-check --open-doi-links

# 特定の不一致のみ表示
PYTHONPATH=code/py uv run python code/py/main.py sync-check --show-missing-in-clippings
PYTHONPATH=code/py uv run python code/py/main.py sync-check --show-missing-in-bib

# DOI統計情報なし
PYTHONPATH=code/py uv run python code/py/main.py sync-check --no-show-doi-stats
```

## 出力例

### 正常ケース
```
✅ All papers in bib file have corresponding clippings directories
✅ All clippings directories have corresponding bib entries

📊 DOI Statistics:
==================================================
Total papers in bib: 45
Papers with DOI: 42
Papers without DOI: 3
DOI coverage: 93.3%
```

### 不一致ケース
```
📚 Papers in CurrentManuscript.bib but missing in Clippings/ (3 papers):
================================================================================

1. Citation Key: smith2023deep
   Title: Deep Learning for Academic Research
   Authors: Smith, John and Brown, Alice
   Year: 2023
   DOI: 10.1038/s41586-023-12345-0
   🔗 Link: https://doi.org/10.1038/s41586-023-12345-0

2. Citation Key: jones2024neural
   Title: Neural Networks in Scientific Discovery
   Authors: Jones, Robert
   Year: 2024
   DOI: ❌ Not available
   🔗 Link: Cannot generate DOI link

📁 Directories in Clippings/ but missing in CurrentManuscript.bib (2 directories):
================================================================================

1. Directory: old_paper2022
   Markdown files (1):
     - old_paper2022.md

2. Directory: draft_analysis
   Markdown files (3):
     - draft_analysis.md
     - notes.md
     - summary.md

📊 DOI Statistics:
==================================================
Total papers in bib: 45
Papers with DOI: 42
Papers without DOI: 3
DOI coverage: 93.3%
Missing papers with DOI: 2
Missing papers without DOI: 1
```

## パフォーマンス仕様

### 処理時間目標
- **同期チェック実行**: 1000項目/秒
- **DOIリンク開放**: 100ms/リンク
- **統計情報生成**: < 1秒

### リソース使用量
- **メモリ使用量**: 30MB以下（通常使用時）
- **ディスク容量**: ログファイル 100KB/実行
- **ネットワーク**: DOIリンク開放時のみ

## エラーハンドリング

### 想定エラーと対処
- **BibTeXファイル不存在**: エラーメッセージとパス確認指示
- **Clippingsディレクトリ不存在**: エラーメッセージとディレクトリ作成指示
- **アクセス権限エラー**: 権限確認とパス修正指示
- **DOIリンク開放失敗**: ログ記録（実行継続）

### 例外クラス
- `SyncCheckError`: 同期チェック専用エラー
- `BibTeXParsingError`: BibTeX解析エラー
- `FileOperationError`: ファイル操作エラー

## 統合機能

### ファイル整理ワークフローとの連携
```bash
# ファイル整理と同期チェックの併用実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files --sync-check --dry-run
```

### 統合ワークフローでの使用
```bash
# 統合実行後の同期チェック
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
PYTHONPATH=code/py uv run python code/py/main.py sync-check --verbose
```

## v2.0 の改善点

### 機能強化
- **DOIリンク自動開放**: ブラウザでの論文アクセス支援
- **詳細統計情報**: DOIカバレッジの可視化
- **クリック可能リンク**: ターミナルでの直接アクセス
- **統合ログシステム**: 実行記録の永続化

### ユーザビリティ改善
- **わかりやすい出力**: 絵文字とフォーマットによる視認性向上
- **アクション指向**: 具体的な対処方法の提示
- **選択的表示**: 必要な情報のみの表示オプション

### パフォーマンス改善
- **高速チェック**: 効率的なディレクトリスキャン
- **メモリ効率**: 大量データの適切な処理
- **並列処理**: DOIリンク開放の並列実行

---

**同期チェックワークフロー仕様書バージョン**: 2.0.0  
**対応システム**: ObsClippingsManager v2.0 