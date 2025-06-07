# Citation Fetcher機能仕様書 v2.2

## 概要
Citation Fetcher機能は、ObsClippingsManager v2.2 において学術論文の引用文献を自動取得し、BibTeX形式で出力する機能です。CrossRef APIをメインとし、複数の無料APIを使った包括的なフォールバック戦略を採用します。

**v2.2 の特徴:**
- **多重APIフォールバック**: CrossRef → PubMed → Semantic Scholar → OpenAlex → OpenCitations
- **メタデータ補完**: 不完全なCrossRefデータを他のAPIで補完
- **無料APIのみ使用**: コスト制約なしで高品質なメタデータ取得
- **sync機能との連携**: CurrentManuscript.bibと{citation_key}/{citation_key}.mdの形で整理されて一致している論文のみを対象
- **個別保存機能**: 各論文の引用文献を{citation_key}/references.bibに保存
- 統合ワークフローシステムとの連携
- 階層的例外処理によるエラーハンドリング向上
- IntegratedLoggerによる詳細ログ
- ConfigManagerによる統合設定管理

## モジュール構成

```
modules/citation_fetcher/
├── __init__.py
├── crossref_client.py        # CrossRef API クライアント
├── pubmed_client.py          # PubMed API クライアント（新規）
├── semantic_scholar_client.py # Semantic Scholar API クライアント（新規）
├── openalex_client.py        # OpenAlex API クライアント（新規）
├── opencitations_client.py   # OpenCitations API クライアント
├── reference_formatter.py    # BibTeX変換・整形
├── metadata_enricher.py      # メタデータ補完機能（新規）
├── fallback_strategy.py      # 多重フォールバック戦略（拡張）
└── sync_integration.py       # sync機能との連携
```

## 機能要件

### 主要機能
- **sync連携**: 同期チェック機能との連携で一致している論文のみを対象とした処理
- CrossRef APIを使用した引用文献の取得
- OpenCitations APIを使用したフォールバック処理
- 取得した引用文献の個別BibTeX形式での出力（{citation_key}/references.bib）
- 取得失敗時の適切なエラーハンドリング

### 非機能要件
- **処理速度**: 1論文あたり平均2秒以内（CrossRef成功時は1秒以内）
- **成功率**: 95%以上の論文で引用文献取得成功
- **拡張性**: 追加APIソースへの対応が容易
- **保守性**: ログ出力とエラー追跡が可能
- **ファイル管理**: 論文ごとの個別ファイル管理
- **既存ファイル制御**: スキップ機能と強制上書き機能

## 詳細機能仕様

### 0. sync機能連携 (`sync_integration.py`)

#### 主要機能
- **同期状態確認**: CurrentManuscript.bibとClippings/ディレクトリの一致確認
- **対象論文特定**: 一致している論文のみのcitation_keyリスト生成
- **DOI取得**: 対象論文からのDOI情報抽出
- **ディレクトリ確認**: 各論文のClippingsディレクトリ存在確認

#### 処理フロー
```
1. 同期チェック実行
   ├── CurrentManuscript.bibの解析
   ├── Clippings/ディレクトリスキャン
   └── 一致論文のリスト生成

2. 対象論文の特定
   ├── 一致したcitation_keyのみを処理対象とする
   ├── 各論文のDOI情報を抽出
   └── 無効・重複DOIのフィルタリング

3. 処理準備
   ├── 各citation_keyのClippingsディレクトリパス確認
   ├── references.bib保存先ディレクトリの確認
   ├── 既存references.bibファイルのスキップ・上書き制御
   └── 既存references.bibファイルのバックアップ（オプション）
```

### 1. CrossRef APIクライアント (`crossref_client.py`)

#### 主要機能
- **引用文献取得**: DOIから論文の引用文献リストを取得
- **メタデータ取得**: 論文の詳細情報（著者、タイトル、ジャーナル等）取得
- **レート制限対応**: 1秒間隔でのリクエスト送信
- **エラーハンドリング**: HTTP エラー・タイムアウトの適切な処理

#### API仕様
- **エンドポイント**: `https://api.crossref.org/works/{doi}`
- **メソッド**: GET
- **ヘッダー**: User-Agent必須
- **レスポンス**: JSON形式の論文メタデータ
- **制限**: 礼儀正しい使用（1秒間隔推奨）

### 2. OpenCitations APIクライアント (`opencitations_client.py`)

#### 主要機能
- **引用関係取得**: DOIから引用論文のDOIリストを取得
- **マルチエンドポイント**: 複数のOpenCitations エンドポイント対応
- **メタデータ補完**: 引用論文の詳細情報取得
- **フォールバック**: CrossRef 失敗時の代替手段

#### API仕様
- **プライマリ**: `https://opencitations.net/index/api/v1/references/{doi}`
- **セカンダリ**: `https://w3id.org/oc/index/coci/api/v1/references/{doi}`
- **メソッド**: GET
- **レスポンス**: JSON形式の引用関係リスト
- **制限**: 公開API、制限なし

### 3. BibTeX変換・整形 (`reference_formatter.py`)

#### 主要機能
- **BibTeX変換**: JSON形式のメタデータをBibTeX形式に変換
- **Citation Key生成**: 著者名・年・タイトルからユニークなキー生成
- **フィールド正規化**: 著者名・タイトル・ジャーナル名の標準化
- **特殊文字処理**: BibTeX特殊文字のエスケープ処理

#### BibTeX出力形式
```bibtex
@article{entry_id,
  title = {論文タイトル},
  author = {著者名1 and 著者名2 and others},
  journal = {ジャーナル名},
  year = {発行年},
  volume = {ボリューム},
  number = {号},
  pages = {ページ範囲},
  doi = {DOI},
  note = {データソース情報}
}
```

### 4. 引用文献取得とメタデータ補完戦略

#### 主要機能
- **引用文献取得**: CrossRef → OpenCitations のフォールバック戦略
- **メタデータ補完**: 不完全な引用文献情報の段階的補完
- **効率的処理**: 完全な情報が得られた時点で後続API呼び出しを停止
- **自動リトライ**: 一時的エラー時の自動再試行
- **統計追跡**: 各APIの成功率・応答時間・補完率追跡

#### 実行フロー
```
1. 引用文献取得フェーズ
   ├── CrossRef API で引用文献リスト取得
   │   ├── 成功 → 引用文献リスト獲得
   │   └── 失敗 → OpenCitations API でフォールバック
   │
   └── 引用文献リスト確定

2. メタデータ補完フェーズ（enable_enrichment有効時のみ）
   ├── 各引用文献の情報完全性チェック
   │   ├── 完全 → 補完スキップ
   │   └── 不完全 → 補完処理へ
   │
   ├── 不完全な引用文献のみ対象として順次API呼び出し
   │   ├── CrossRef API 試行
   │   ├── PubMed API 試行
   │   ├── Semantic Scholar API 試行
   │   ├── OpenAlex API 試行
   │   └── OpenCitations API 試行
   │
   └── 十分な情報が得られた時点で当該引用文献の処理終了

3. 結果処理
   ├── 補完された引用文献をBibTeX変換
   ├── {citation_key}/references.bib 出力
   └── 補完統計記録
```

#### 効率的処理の特徴
- **完全な引用文献はスキップ**: title, author, year, journal等が既に揃っている場合は補完処理をスキップ
- **段階的補完**: 各引用文献ごとに必要な情報が揃った時点で後続APIの呼び出しを停止
- **API使用量最適化**: 無駄なAPI呼び出しを削減し、実行時間を大幅短縮

#### APIカバレッジ最適化
実データ分析（288引用文献）に基づく最適化された API優先順位：

**カバレッジ統計:**
- CrossRef: 61.1% (176件) - 最も高いカバレッジ
- OpenCitations: 21.5% (62件) - 補完効果が高い
- OpenAlex: 17.4% (50件) - 学術データベースとして信頼性が高い
- PubMed: 生命科学分野で強い
- Semantic Scholar: コンピュータサイエンス分野で強い

**最適化された優先順位:**
```
生命科学分野: CrossRef → OpenCitations → OpenAlex → Semantic Scholar → PubMed
コンピュータサイエンス: CrossRef → OpenCitations → OpenAlex → Semantic Scholar → PubMed
一般分野: CrossRef → OpenCitations → OpenAlex → Semantic Scholar → PubMed
```

**段階的補完の特徴:**
- 各引用文献ごとに十分な情報が得られた時点で後続API呼び出しを停止
- Semantic Scholar・PubMedは最終補完手段として機能（実際にはほとんど呼び出されない）
- 専門分野での追加情報取得機会を維持しつつ、パフォーマンスを最適化

### 5. 既存ファイル制御機能

#### 主要機能
- **スキップ機能**: 既存references.bibファイルがある場合の自動スキップ
- **強制上書き**: `--force-overwrite`オプションによる強制上書き
- **スキップ統計**: スキップされたファイル数の統計情報
- **動作ログ**: スキップ・上書き判定の詳細ログ

#### 動作フロー
```
1. ファイル存在チェック
   ├── references.bibファイルの存在確認
   ├── force_overwriteオプションの確認
   └── 処理方針の決定

2. 処理判定
   ├── ファイル存在 + force_overwrite=False → スキップ
   ├── ファイル存在 + force_overwrite=True → 上書き
   └── ファイル未存在 → 新規作成

3. 統計・ログ更新
   ├── スキップ数カウント
   ├── 処理結果ログ出力
   └── ユーザーへの結果表示
```

#### CLIオプション
- `--force-overwrite`: 既存ファイルを強制的に上書き
- デフォルト動作: 既存ファイルはスキップ

#### 修復された問題
この機能は、**lennartzM2023APMIS論文のreferences.bib問題**の修復に直接使用されました：

**修復前**: 
- 6個のBibTeXエントリ（91%が欠損）
- `'NoneType' object has no attribute 'strip'`エラーによる変換失敗

**修復後**:
- 67個すべてのBibTeXエントリが正常生成
- ReferenceFormatterのNoneチェック機能追加
- `--force-overwrite`による問題ファイルの強制再生成

## 実行方法

### 基本実行
```bash
# 引用文献取得ワークフロー実行（sync連携）
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations

# ドライラン実行
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --dry-run

# 詳細ログ付き実行
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --verbose
```

### カスタム設定
```bash
# リクエスト間隔調整
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --request-delay 2.0

# リトライ回数調整
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --max-retries 5

# タイムアウト調整
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --timeout 60

# 既存references.bibのバックアップ作成
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --backup-existing

# 既存references.bibを強制上書き
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --force-overwrite
```

### メタデータ補完機能（v2.2新機能）
```bash
# メタデータ補完機能を有効化
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --enable-enrichment

# 生命科学分野向けAPI優先順位でメタデータ補完
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --enable-enrichment --enrichment-field-type life_sciences

# 計算機科学分野向けAPI優先順位でメタデータ補完
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --enable-enrichment --enrichment-field-type computer_science

# 品質スコア閾値を指定してメタデータ補完
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --enable-enrichment --enrichment-quality-threshold 0.9

# 最大API試行回数を制限
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations --enable-enrichment --enrichment-max-attempts 5
```

### sync機能併用
```bash
# 同期チェック後の引用文献取得
PYTHONPATH=code/py uv run python code/py/main.py sync-check
PYTHONPATH=code/py uv run python code/py/main.py fetch-citations

# 統合実行（デフォルト: 整理 → 同期確認 → 引用取得）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated
```

## 出力仕様

### 出力ファイル構造
```
ManuscriptsManager/Clippings/
├── paper1/
│   ├── paper1.md
│   └── references.bib              # 新規：個別引用文献
├── paper2/
│   ├── paper2.md
│   └── references.bib              # 新規：個別引用文献
└── paper3/
    ├── paper3.md
    └── references.bib              # 新規：個別引用文献

References/（廃止）
└── （従来の一括出力ファイルは廃止）

Logs/
├── failed_dois_YYYYMMDD_HHMMSS.txt   # 取得失敗DOIリスト
└── statistics_YYYYMMDD_HHMMSS.json   # 実行統計情報
```

### 個別references.bibファイル例
```bibtex
% References for citation_key: smith2023deep
% Generated on: 2024-01-15 14:30:45
% Total references: 42

@article{brown2022machine,
  title = {Machine Learning Applications in Research},
  author = {Brown, Alice and White, Bob},
  journal = {Nature Machine Intelligence},
  year = {2022},
  volume = {3},
  number = {4},
  pages = {123--145},
  doi = {10.1038/s42256-022-12345-0},
  note = {Retrieved from CrossRef API}
}

@inproceedings{jones2021neural,
  title = {Neural Network Architectures for Scientific Computing},
  author = {Jones, Robert and Davis, Carol},
  booktitle = {Proceedings of the International Conference on Machine Learning},
  year = {2021},
  pages = {567--578},
  doi = {10.48550/arXiv.2101.12345},
  note = {Retrieved from OpenCitations API}
}
```

### 統計情報例
```json
{
  "total_synced_papers": 12,
  "successful_papers": 11,
  "failed_papers": 1,
  "total_references": 287,
  "crossref_success": 10,
  "opencitations_success": 1,
  "average_references_per_paper": 26.1,
  "average_response_time": 1.3,
  "execution_time": 32.1,
  "sync_integration": {
    "total_papers_in_bib": 15,
    "total_directories_in_clippings": 14,
    "synced_papers": 12,
    "sync_rate": 80.0
  }
}
```

## エラーハンドリング

### エラー分類
- **同期エラー**: CurrentManuscript.bibとClippingsディレクトリの不一致
- **ネットワークエラー**: タイムアウト・接続エラー
- **APIエラー**: 404, 429, 500エラー等
- **データエラー**: 不正なDOI・解析エラー
- **ファイルシステムエラー**: ディレクトリ作成・ファイル書き込みエラー

### エラー対応
- **同期エラー**: sync-checkの実行を推奨・処理対象の明確化
- **一時的エラー**: 自動リトライ（指数バックオフ）
- **恒久的エラー**: ログ記録・統計更新
- **重大エラー**: 実行停止・詳細エラーレポート

## パフォーマンス仕様

### 処理時間目標
- **同期チェック**: 1000項目/秒
- **CrossRef API**: 論文あたり1秒以内
- **OpenCitations API**: 論文あたり2秒以内
- **BibTeX変換・保存**: 100エントリ/秒

### リソース使用量
- **メモリ使用量**: 150MB以下（大量引用文献取得時）
- **ネットワーク**: 控えめなAPI使用（1秒間隔）
- **ディスク容量**: 論文あたり約1-5KB（引用文献数に依存）

## 統合機能

### ワークフロー統合
```bash
# デフォルト統合実行（整理 → 同期確認 → 引用取得）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# カスタム実行（同期確認 → 引用取得のみ）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --sync-first --fetch-citations

# 部分実行（整理後の引用取得のみ）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --organize-first --fetch-citations
```

### 設定統合
Citation Fetcher固有の設定は ConfigManager の `citation_fetcher` セクションで管理され、統合ワークフローからアクセス可能です。

## v2.1 の改善点

### アーキテクチャ改善
- **sync機能連携**: 整理済み論文のみを対象とした効率的処理
- **個別ファイル管理**: 論文ごとの引用文献管理
- **統合ログ**: IntegratedLogger による一元ログ管理

### 機能強化
- **同期状態確認**: ファイル整理状況の事前確認
- **個別保存**: {citation_key}/references.bib への個別保存
- **バックアップ機能**: 既存ファイルの安全な保護
- **詳細統計**: sync連携情報を含む統計

### データ管理改善
- **構造化保存**: 論文ディレクトリ内への体系的保存
- **トレーサビリティ**: 引用文献の取得ソース明記
- **メンテナンス性**: 個別管理による更新・削除の容易化

---

**Citation Fetcher機能仕様書バージョン**: 2.1.0  
**対応システム**: ObsClippingsManager v2.1 