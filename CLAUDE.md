# ObsClippingsManager v3.2.0 - Claude Code開発ガイド

## ⚠️ 重要ルール
- ユーザーとは日本語で会話して
- テスト必須
- 進捗管理連携
- テスト100%成功維持
- 仕様書同期更新

## 🎯 システム概要

学術研究における文献管理とMarkdownファイル整理を自動化する統合システム。**シンプル設定**と**状態管理による重複処理回避**が特徴。

## 🛠️ 開発環境

- **Python環境**: uvで管理 - 必ずuvを使用
- **実行ディレクトリ**: プロジェクトルート (`/home/user/proj/ObsClippingsManager`)
- **ブランチ**: 常にmainブランチで開発
- **開発方針**: TDDアプローチ必須
- **進捗管理**: `code/contexts/PROGRESS.md`で段階的進行を管理

## ⚡ よく使用するコマンド

### テスト実行
```bash
# 全ユニットテスト実行（開発前後必須）
uv run code/unittest/run_all_tests.py

# 統合テスト実行（AI機能無効化でAPI料金節約）
uv run python code/scripts/run_integrated_test.py --disable-ai

# 統合テスト実行（全機能有効）
uv run python code/scripts/run_integrated_test.py

# 特定AI機能のみ有効化テスト
uv run python code/scripts/run_integrated_test.py --enable-only-tagger
```

### 開発用コマンド
```bash
# 構文チェック
uv run python -m py_compile [ファイルパス]

# 個別テスト実行
uv run python -m unittest [テストクラス名]

# 進捗状況確認
cat code/contexts/PROGRESS.md
```

## 🔄 TDD開発ワークフロー

### 1. 開発前チェック
```bash
uv run code/unittest/run_all_tests.py
```
**重要**: 全テストが成功していることを確認

### 2. 進捗管理連携TDD開発手順
1. **進捗確認** - `code/contexts/PROGRESS.md`で現在のステップ確認
2. **ステップ開始** - 該当タスクを `[ ]` → `[進行中]` に変更
3. **テスト先行作成** - 新機能/修正に対応するunit-testを先に作成
4. **Red** - テストが失敗することを確認
5. **Green** - テストが成功するように最小限のコードを実装
6. **Refactor** - 必要に応じてコード品質向上
7. **ステップ完了** - 全テスト成功後 → `[完了]` に変更

### 3. 開発完了チェック
```bash
# 全テスト実行（必須）
uv run code/unittest/run_all_tests.py
```

### 4. Git操作
```bash
git add -A
git commit -m "[種類]: 変更内容（50文字以内）"
git push
```

## 📁 プロジェクト構造

```
code/py/modules/
├── shared_modules/         # 共通基盤（config, logger, parser, utils）
├── citation_fetcher/       # 引用文献取得（CrossRef → Semantic Scholar → OpenCitations）
├── file_organizer/         # Citation keyベースのファイル整理
├── sync_checker/           # BibTeX ↔ Clippings整合性確認
├── section_parsing/        # Markdownセクション構造解析
├── ai_citation_support/    # AI理解支援・引用文献統合
├── ai_tagging_translation/ # AI論文解析（タグ生成・翻訳・要約）
└── status_management_yaml/ # YAML状態管理システム
```

## 🧪 テスト体系

### 2層テスト構成
1. **ユニットテスト**: 個別モジュールの単体テスト (`code/unittest/`)
2. **統合テスト**: マスターテストデータによるエンドツーエンドテスト (`code/integrated_test/`)

### テスト環境の安全性
- **テスト専用ディレクトリ**: `/tmp/ObsClippingsManager_Test`での動作検証
- **本番環境への影響回避**: テスト実行時の完全分離
- **自動クリーンアップ**: テスト環境の自動削除

## 📋 進捗管理ルール

### ステータス管理
- `[ ]`: 未着手
- `[進行中]`: 作業中
- `[完了]`: 完了・テスト成功・git push済み
- `[問題]`: 問題発生・要対応
- `[スキップ]`: 当該フェーズでは不要

## 📝 コミットメッセージ形式

```
[種類]: 変更内容の簡潔な説明（50文字以内）
```

### 種類
- `feat`: 新機能追加
- `fix`: バグ修正
- `docs`: ドキュメント更新
- `test`: テスト追加・修正
- `refactor`: リファクタリング
- `style`: コードフォーマット
- `chore`: その他
- `progress`: 進捗管理ファイル更新

## 🔧 設定ファイル

### メイン設定
- `config/config.yaml`: システム全体設定
- `.env`: 環境変数（API Keys等）

### 重要な環境変数
```bash
# API Keys
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Workspace Configuration
WORKSPACE_PATH=/home/user/ManuscriptsManager
```

## 📊 統合ワークフロー処理順序

```
organize → sync → fetch → section_parsing → ai_citation_support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
```

## 🚨 トラブルシューティング

### よくある問題と解決方法
| 問題 | 解決方法 |
|------|----------|
| テスト失敗 | 原因特定して修正、リグレッション防止 |
| ワークスペース不明 | `--workspace`でパス指定 |
| 処理スキップ | `--force`で強制実行 |
| YAMLエラー | `--repair-headers`で修復 |
| API接続エラー | 設定でリトライ回数調整 |

### ログ確認
```bash
tail -f logs/obsclippings.log
```

## ⚠️ 重要ルール

### 品質保証
- **テスト失敗時**: 必ず原因特定して修正してから進む
- **リグレッション防止**: 既存テストが失敗した場合は実装見直し
- **Python互換性**: Python 3.12+対応
- **進捗記録**: ステップ完了を忘れずに`PROGRESS.md`に反映

### AI機能制御
```bash
# デフォルト実行（全機能有効）
uv run python code/scripts/run_integrated_test.py

# 全AI機能無効化（API利用料金削減）
uv run python code/scripts/run_integrated_test.py --disable-ai

# 特定AI機能のみ有効化
uv run python code/scripts/run_integrated_test.py --enable-only-tagger
```

## 📖 仕様書システム

### 統一テンプレート準拠
- 個別モジュール仕様書: `code/contexts/[モジュール名]_specification.md`
- YAMLヘッダー形式遵守
- 具体的データ例必須
- processing_status記録必須

### 必須要件
- **実装変更時**: 必ず仕様書も同期更新
- **YAMLヘッダー整合性**: 最優先事項
- **具体例記載**: 抽象的でなく実際の値使用

---

**重要**: TDD必須、進捗管理連携、テスト100%成功維持、仕様書同期更新