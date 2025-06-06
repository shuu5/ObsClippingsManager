# ObsClippingsManager

## ルール

このルールを読み込んだら「ObsClippingsManagerを読み込みました！」と発言して。

- このPython環境はuvで管理されているのでuvを使用してパッケージ管理を行って。
- コードの実行は必ずルートディレクトリをカレントディレクトリとして行って。
- 開発は以下のGit開発ワークフローに従って行って。

## Git開発ワークフロー

### 開発開始時
```bash
git checkout main
git pull origin main
git branch --merged main | grep -v main | xargs -n 1 git branch -d
git checkout -b feature/[機能名]
```

### 開発作業完了時
```bash
git add .
git commit -m "[feat/fix/docs]: 簡潔な説明"
git push -u origin $(git branch --show-current)
```

### テスト実行
```bash
cd /home/user/proj/ObsClippingsManager
uv run code/unittest/run_all_tests.py 
```

### 統合完了後
```bash
git checkout main
git pull origin main
git branch -d feature/[機能名]
git push origin --delete feature/[機能名]
```

### ブランチ命名規則
- `feature/機能名`: 新機能開発時に使用してください
- `fix/バグ名`: バグ修正時に使用してください  
- `docs/ドキュメント名`: ドキュメント更新時に使用してください
- `refactor/対象名`: リファクタリング時に使用してください

### コミットメッセージルール
以下の形式でコミットメッセージを作成してください：
```
[種類]: 変更内容の簡潔な説明（50文字以内）

詳細説明（必要な場合のみ）
- 具体的な変更点
- 影響範囲
```

#### 種類の指定
- `feat`: 新機能追加時に使用
- `fix`: バグ修正時に使用
- `docs`: ドキュメント更新時に使用
- `style`: コードフォーマット変更時に使用
- `refactor`: リファクタリング時に使用
- `test`: テスト追加・修正時に使用
- `chore`: その他の変更時に使用

### 必須ルール
- 新機能開発は必ずfeature/ブランチで行ってください
- コミット前に必ずテストを実行してください
- mainブランチへの直接pushは禁止です
- プルリクエスト経由でのみマージしてください
- 統合後は不要ブランチを即座に削除してください