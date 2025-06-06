# Git 開発手順書

このドキュメントは、ObsClippingsManagerプロジェクトでの次回以降の開発に際して行うべきGitの手順をまとめたものです。

## 前提条件

- git init、remote設定、初回commit、pushが完了済み
- リモートリポジトリ: https://github.com/shuu5/ObsClippingsManager.git
- メインブランチ: main

## 基本的な開発ワークフロー

### 1. 開発開始前の準備

```bash
# 作業ディレクトリに移動
cd /home/user/proj/ObsClippingsManager

# 最新の変更をリモートから取得
git fetch origin

# mainブランチに移動し、最新の状態に更新
git checkout main
git pull origin main
```

### 2. 新機能開発用ブランチの作成

```bash
# 新しいブランチを作成して移動
git checkout -b feature/機能名
# 例: git checkout -b feature/add-pdf-parser
```

### 3. 開発作業

```bash
# 変更したファイルの確認
git status

# 変更内容の詳細確認
git diff

# 特定のファイルの変更を確認
git diff ファイル名
```

### 4. 変更のステージングとコミット

```bash
# 特定のファイルをステージング
git add ファイル名

# すべての変更をステージング
git add .

# 修正したファイルのみステージング（新規ファイルは除く）
git add -u

# コミット
git commit -m "明確なコミットメッセージ"
```

### 5. リモートへのプッシュ

```bash
# 初回プッシュ（上流ブランチを設定）
git push -u origin feature/機能名

# 2回目以降のプッシュ
git push
```

### 6. プルリクエスト作成とマージ

1. GitHubでプルリクエストを作成
2. レビュー・テスト
3. mainブランチにマージ
4. ローカルでの後処理

```bash
# mainブランチに戻る
git checkout main

# 最新の状態に更新
git pull origin main

# 不要になったブランチを削除
git branch -d feature/機能名

# リモートの不要ブランチも削除
git push origin --delete feature/機能名
```


## コミットメッセージの書き方

### 推奨フォーマット

```
[種類]: 簡潔な説明

詳細な説明（必要に応じて）
```

### 種類の例

- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント更新
- `style`: フォーマット変更
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: その他の変更

### 例

```
feat: PDFファイルのパース機能を追加

- pypdfライブラリを使用してPDF解析を実装
- エラーハンドリングを追加
- 単体テストを追加
```

## ブランチ命名規則

- `feature/機能名`: 新機能開発
- `fix/バグ名`: バグ修正
- `docs/ドキュメント名`: ドキュメント更新
- `refactor/対象名`: リファクタリング

## 注意事項

1. **必ずブランチを作成してから開発を行う**
2. **コミット前に必ず変更内容を確認する**
3. **プッシュ前にローカルでテストを実行する**
4. **プルリクエストでは明確な説明を記載する**
5. **mainブランチへの直接プッシュは避ける**

## 定期的なメンテナンス

```bash
# 不要なブランチのクリーンアップ
git branch --merged main | grep -v main | xargs -n 1 git branch -d

# リモートの削除されたブランチをローカルからも削除
git remote prune origin
```

---

このドキュメントは必要に応じて更新してください。 