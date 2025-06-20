# コード実装・修正・デバッグ専用ルール

## 🛠️ 環境・前提条件

- **実行ディレクトリ**: `/home/user/proj/ObsClippingsManager`
- **Python環境**: uvコマンド必須
- **開発方針**: TDD必須、`code/contexts/PROGRESS.md`進捗管理連携

## 🔄 TDD開発ワークフロー

### 1. 開発前チェック
```bash
cd /home/user/proj/ObsClippingsManager
uv run code/unittest/run_all_tests.py
```

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
**重要**: 全テストが成功してから次に進む

### 4. 進捗同期とGit操作
```bash
# PROGRESS.md更新確認（ステップを[完了]に変更済みか確認）
git add -A
git commit -m "[種類]: 変更内容（50文字以内）"
git push
```

### 5. 仕様書同期
- 実装と仕様書(`code/contexts/*.md`, README.md)の整合性確認
- 不整合があれば仕様書を更新（spec-rule.md参照）

## 📝 PROGRESS.md進捗管理ルール

### ステータス更新タイミング
- **ステップ開始時**: `[ ]` → `[進行中]`
- **ステップ完了時**: `[進行中]` → `[完了]`（全テスト成功後）
- **問題発生時**: `[問題]`で記録、原因と対策を併記

### 新機能開発時
1. PROGRESS.mdに新ステップ追加（3-5個のサブステップに分割）
2. 各ステップでTDDフロー実行
3. 完了後に次期計画更新

## ⚠️ 実装時の注意点

### 品質保証
- **テスト失敗時**: 必ず原因特定・修正後に進む
- **Python 3.x互換性**: `from e`構文NG、`__cause__`使用
- **例外処理**: ObsClippingsManagerError基底クラス、IntegratedLogger使用

### 大規模ファイル編集指針
1. **スコープ限定**: 関数・クラス単位で具体的に指定
2. **変更量削減**: 関連性の高い1-2個ずつ分割実行
3. **適切なコンテキスト**: 変更箇所特定に必要な最小限の周辺コード含める

---

**重要**: TDD必須、進捗管理連携、テスト100%成功維持