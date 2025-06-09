# ObsClippingsManager 開発ルール

## AI開発アシスタント向けガイドライン

このルールを読み込んだら「ObsClippingsManagerを読み込みました！」と発言して。

## 🛠️ 基本環境

- **Python環境**: uvで管理 - 必ずuvを使用
- **実行ディレクトリ**: 必ずルートディレクトリ(`/home/user/proj/ObsClippingsManager`)から実行
- **ブランチ**: 常にmainブランチで開発
- **開発方針**: TDDアプローチ必須

## 🔄 開発フロー（必須手順）

### 1. 開発前チェック
```bash
cd /home/user/proj/ObsClippingsManager
uv run code/unittest/run_all_tests.py
```

### 2. TDD開発手順
1. **テスト先行作成** - 新機能/修正に対応するunit-testを先に作成
2. **Red** - テストが失敗することを確認
3. **Green** - テストが成功するように最小限のコードを実装
4. **Refactor** - 必要に応じてコード品質向上

### 3. 開発完了チェック
```bash
# 全テスト実行（必須）
uv run code/unittest/run_all_tests.py
```
**重要**: 全テストが成功してから次に進む

### 4. 仕様書同期
- 実装と仕様書(`code/contexts/*.md`, `README.md`)の整合性確認
- 不整合があれば仕様書を更新

### 5. Git操作
```bash
git add -A
git commit -m "[種類]: 変更内容（50文字以内）"
git push
```

## 📝 コミットメッセージ

### 形式
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

## ⚠️ 重要ルール

### 品質保証
- **テスト失敗時**: 必ず原因特定して修正してから進む
- **リグレッション防止**: 既存テストが失敗した場合は実装見直し
- **Python 3.x互換性**: `from e` 構文NG、`__cause__` 使用

### エラー対応
```bash
# 構文チェック
uv run python -m py_compile [ファイル]

# 個別テスト実行
uv run python -m unittest [テストクラス]
```

### 例外処理
- ObsClippingsManagerError基底クラス使用
- IntegratedLoggerで適切なログレベル設定

---

**重要**: TDD必須、テスト100%成功維持
