# Rename & MkDir Citation Key機能仕様書 v2.0

## 概要
Rename & MkDir Citation Key機能は、ObsClippingsManager v2.0 においてMarkdownファイルの整理とBibTeX参照キーとの連携を行う機能です。研究ノートやクリッピングファイルの管理を効率化し、学術文献との関連付けを自動化します。

**v2.0 の特徴:**
- 統合ワークフローシステムとの連携
- 高度FileMatcher による精密な照合
- 階層的例外処理によるエラーハンドリング向上
- IntegratedLoggerによる詳細ログ

## 機能目的
- `/home/user/ManuscriptsManager/Clippings/`内のMarkdownファイルを整理・編集
- BibTeXファイル（`/home/user/ManuscriptsManager/CurrentManuscript.bib`）との連携
- MarkdownファイルのYAML frontmatter内のdoiとBibTeX項目のdoiフィールドを照合
- 一致したファイルをcitation_keyベースのディレクトリ構造で整理

## モジュール構成

```
modules/rename_mkdir_citation_key/
├── __init__.py
├── file_matcher.py           # ファイル照合エンジン
├── markdown_manager.py       # Markdownファイル管理
└── directory_organizer.py    # ディレクトリ整理
```

## 入力・出力仕様

### 入力ファイル
- **BibTeXファイル**: `/home/user/ManuscriptsManager/CurrentManuscript.bib`
- **Markdownファイル群**: `/home/user/ManuscriptsManager/Clippings/*.md`

### 出力ディレクトリ構造
```
/home/user/ManuscriptsManager/Clippings/
├── {citation_key_1}/
│   └── {citation_key_1}.md          # 整理済み（処理対象外）
├── {citation_key_2}/
│   └── {citation_key_2}.md          # 整理済み（処理対象外）
├── 新しい論文.md                    # 新規追加ファイル（処理対象）
└── 未分類ファイル.md                # マッチしなかった場合
```

**処理対象**: ルートレベルの`.md`ファイルのみ
**処理対象外**: サブディレクトリ内の既に整理済みファイル

## 詳細機能仕様

### 1. ファイル照合機能 (`file_matcher.py`)
MarkdownファイルのYAML frontmatter内のdoiとBibTeX項目のdoiフィールドの照合を行います。

#### 主要機能
- **DOI照合**: MarkdownとBibTeXのDOI完全一致照合
- **DOI正規化**: プレフィックス除去・小文字変換・空白除去
- **タイトル照合**: DOI不存在時のフォールバック（オプション）
- **タイトル同期**: DOI照合成功時のタイトル自動同期
- **照合結果管理**: ファイル-citation_key対応表生成

#### DOI照合アルゴリズム
- **手法**: 完全一致（DOI正規化後）
- **正規化処理**: 
  - 小文字変換
  - "doi:" プレフィックス除去
  - "https://doi.org/" プレフィックス除去
  - 空白文字の除去
- **フォールバック**: DOIが存在しない場合のtitle照合（オプション）

#### タイトル同期処理
- **実行タイミング**: DOI照合成功後
- **比較対象**: MarkdownのYAML frontmatter内`title`フィールド vs BibTeXの`title`フィールド
- **正規化処理**: 
  - 前後空白の除去
  - BibTeX特殊記号（`{}`等）の除去
  - 改行文字の正規化
- **更新条件**: 正規化後の文字列が完全に異なる場合
- **確認動作**: `title_sync_prompt`設定に応じてユーザー確認
- **バックアップ**: 更新前のファイル内容を自動保存

### 2. Markdownファイル管理機能 (`markdown_manager.py`)
Markdownファイルの検索、移動、リネーム操作を管理します。

#### 主要機能
- **ファイル検索**: ルートレベルMarkdownファイルの取得
- **YAML frontmatter解析**: DOI・タイトル・その他メタデータ抽出
- **YAML frontmatter更新**: タイトル同期・メタデータ追加
- **ファイル移動**: citation_keyディレクトリへの移動・リネーム
- **バックアップ作成**: 操作前の自動バックアップ
- **整理状態チェック**: 既存整理済みファイルの判定

#### ファイル名正規化
- 無効文字の除去（`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`）
- 長さ制限（255文字以内）
- 拡張子の確保（`.md`）
- 重複名回避（連番付与）

### 3. ディレクトリ整理機能 (`directory_organizer.py`)
citation_keyベースのディレクトリ構造でファイルを整理します。

#### 主要機能
- **ディレクトリ作成**: citation_keyベースのディレクトリ自動作成
- **ファイル移動**: 元ファイルから目的ディレクトリへの移動
- **重複処理**: 同名ファイル存在時の重複回避
- **空ディレクトリクリーンアップ**: 移動後の空ディレクトリ削除（オプション）
- **権限管理**: ディレクトリ・ファイル権限の適切な設定

#### ディレクトリ命名規則
- **基本形式**: `{citation_key}/`
- **ファイル名**: `{citation_key}.md`
- **重複対応**: `{citation_key}_01.md`, `{citation_key}_02.md`

## 実行方法

### 基本実行
```bash
# ファイル整理ワークフロー実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files

# ドライラン実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files --dry-run

# 詳細ログ付き実行
PYTHONPATH=code/py uv run python code/py/main.py organize-files --verbose
```

### 主要オプション
```bash
# 自動承認（確認なし）
PYTHONPATH=code/py uv run python code/py/main.py organize-files --auto-approve

# タイトル照合閾値調整
PYTHONPATH=code/py uv run python code/py/main.py organize-files --threshold 0.9

# DOI照合無効化（タイトル照合のみ）
PYTHONPATH=code/py uv run python code/py/main.py organize-files --disable-doi-matching --threshold 0.8

# タイトル自動同期無効化
PYTHONPATH=code/py uv run python code/py/main.py organize-files --disable-title-sync

# 同期チェック併用
PYTHONPATH=code/py uv run python code/py/main.py organize-files --sync-check
```

## ワークフロー

### 処理フロー
```
1. 入力ファイル確認
   ├── BibTeXファイル存在確認
   ├── Clippingsディレクトリ存在確認
   └── Markdownファイル検索

2. ファイル照合処理
   ├── DOI照合（メイン処理）
   │   ├── YAML frontmatter解析
   │   ├── DOI正規化・照合
   │   └── citation_key特定
   ├── タイトル照合（フォールバック、オプション）
   │   ├── タイトル正規化・類似度計算
   │   └── 閾値以上でマッチング
   └── 照合結果整理

3. タイトル同期処理（DOI照合成功時）
   ├── MarkdownとBibTeXタイトル比較
   ├── 差分確認・ユーザー承認
   └── タイトル更新・バックアップ作成

4. ファイル整理処理
   ├── citation_keyディレクトリ作成
   ├── ファイル移動・リネーム
   ├── 重複処理・バックアップ作成
   └── 空ディレクトリクリーンアップ

5. 結果報告
   ├── 成功・失敗統計
   ├── 詳細ログ出力
   └── 同期チェック（オプション）
```

## 設定オプション

### 主要設定項目
```python
ORGANIZATION_CONFIG = {
    "similarity_threshold": 0.8,          # タイトル照合類似度閾値
    "auto_approve": False,                # 自動承認フラグ
    "create_directories": True,           # ディレクトリ自動作成
    "cleanup_empty_dirs": True,           # 空ディレクトリクリーンアップ
    "file_extensions": [".md", ".txt"],   # 処理対象拡張子
    "exclude_patterns": ["*.tmp", ".*"],  # 除外パターン
    "title_sync_enabled": True,           # タイトル自動同期
    "title_sync_prompt": True,            # 同期時ユーザー確認
    "backup_enabled": True,               # バックアップ作成
    "doi_matching_enabled": True          # DOI照合有効/無効
}
```

## パフォーマンス仕様

### 処理時間目標
- **ファイル照合**: 100ファイル/分（DOI照合時）
- **タイトル照合**: 50ファイル/分（文字列類似度計算時）
- **ファイル移動**: 200ファイル/分

### リソース使用量
- **メモリ使用量**: 50MB以下（通常使用時）
- **ディスク容量**: バックアップファイル分の追加容量
- **CPU使用率**: タイトル照合時のみ高負荷

## エラーハンドリング

### エラー分類
- **設定エラー**: 必須ファイル・ディレクトリ不存在
- **権限エラー**: ファイル・ディレクトリアクセス権限不足
- **データエラー**: YAML frontmatter解析エラー
- **ファイルシステムエラー**: ディスク容量不足・I/Oエラー

### エラー対応
- **設定エラー**: 詳細メッセージ・対処方法表示
- **権限エラー**: 権限確認・パス修正指示
- **データエラー**: ファイルスキップ・ログ記録
- **重大エラー**: 処理停止・状態復旧

## 統合機能

### 同期チェックとの連携
```bash
# ファイル整理 + 同期チェック
PYTHONPATH=code/py uv run python code/py/main.py organize-files --sync-check --dry-run
```

### 統合ワークフローでの使用
```bash
# 引用取得 → ファイル整理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --citation-first

# ファイル整理 → 引用取得
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --organize-first
```

## v2.0 の改善点

### アーキテクチャ改善
- **モジュラー設計**: 明確な役割分離
- **統合ログ**: IntegratedLogger による一元ログ管理
- **設定管理**: ConfigManager による統合設定

### 機能強化
- **DOI照合による高精度マッチング**: タイトル照合からの大幅改善
- **タイトル自動同期**: BibTeXとの情報一致保証
- **バックアップ機能**: 操作前の自動バックアップ
- **同期チェック連携**: 整合性確認の統合

### ユーザビリティ改善
- **柔軟なオプション**: DOI照合・タイトル同期の個別制御
- **詳細ログ**: 処理内容の透明性向上
- **エラーガイダンス**: 具体的な対処方法提示

### パフォーマンス改善
- **効率的DOI照合**: 正規化による高速マッチング
- **並列処理**: 複数ファイルの並行処理
- **メモリ効率**: 大量ファイルの適切な処理

---

**Rename & MkDir Citation Key機能仕様書バージョン**: 2.0.0  
**対応システム**: ObsClippingsManager v2.0 