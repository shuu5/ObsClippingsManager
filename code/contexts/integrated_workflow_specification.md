# 統合ワークフロー仕様書

## 概要
統合ワークフロー（Integrated Workflow）は、ObsClippingsManagerの中核機能。すべての処理を`run-integrated`コマンド一つで完結させるシンプルかつ効率的なシステム。状態管理により重複処理を自動回避し、デフォルト設定での引数なし実行を実現。

## 基本原理

### 単一コマンド統合
- **すべての機能**を`run-integrated`に集約
- **引数なし実行**でデフォルト動作（AI機能含む）
- **個別設定**は必要時のみ
- **AI理解支援**をデフォルトで有効化

### 状態管理による効率化
- **YAMLヘッダー**による処理状態追跡
- **自動スキップ**で完了済み処理を回避
- **失敗再実行**で必要な処理のみ実施
- **AI機能処理状態**の詳細追跡

### 統一ディレクトリ設定
- **workspace_path**一つでの全パス管理
- **自動導出**による設定シンプル化
- **個別指定**での柔軟性確保

## システム構成

### 処理フロー
```
organize → sync → fetch → section-parsing → ai-citation-support → enhanced-tagger → enhanced-translate → ochiai-format → final-sync
```

### メタデータ自動補完システム
- **デフォルト有効**: 全引用文献に対して自動的にメタデータ補完を実行
- **フォールバック戦略**: CrossRef → Semantic Scholar → OpenAlex → PubMed → OpenCitations
- **完全自動制御**: 十分な情報（title, author, journal, year）が得られた時点で後続API呼び出しを停止
- **API最適化**: 無駄なAPI呼び出しを削減し、効率的な処理を実現

### 依存関係
- 各ステップは**順次実行**
- **前段階完了**後に次段階実行
- **失敗時は後続ステップ停止**
- **AI機能**は**ai-citation-support完了後**に実行

### 状態追跡
- 各論文の`.md`ファイルYAMLヘッダーで状態管理
- ステップごとの処理状態を記録
- 完了/失敗/保留の状態管理
- **AI機能処理状態**の追跡

## 設定システム

### デフォルト設定
```yaml
# config/config.yaml
workspace_path: "/home/user/ManuscriptsManager"

# 自動導出パス
bibtex_file: "{workspace_path}/CurrentManuscript.bib"
clippings_dir: "{workspace_path}/Clippings"
output_dir: "{workspace_path}/Clippings"

# AI機能設定（デフォルト有効）
ai_generation:
  default_model: "claude-3-5-haiku-20241022"
  tagger:
    enabled: true
    batch_size: 8
  translate_abstract:
    enabled: true
    batch_size: 5
  ochiai_format:
    enabled: true
    batch_size: 3
  section_parsing:
    enabled: true
```

### 設定優先順位
1. **コマンドライン引数** (最高優先度)
2. **設定ファイル** (config.yaml)
3. **デフォルト値** (最低優先度)

## IntegratedWorkflow クラス

### クラス設計概要
統合ワークフローを管理する中核クラス。各モジュールを初期化し、順次実行を制御します。

### 主要処理フロー
1. **パス解決**: workspace_pathから全パス自動導出
2. **設定検証**: ファイル存在・エッジケース検出
3. **処理対象決定**: BibTeXとMarkdownの両方に存在する論文のみ
4. **ステップ実行**: 順次処理（前段階完了後に次段階）
5. **状態更新**: 各ステップ完了時の状態記録

## エッジケース処理仕様

### 概要
BibTeXファイルとClippingsディレクトリ間の不整合ケースに対する処理方針を定義します。

### エッジケース定義

#### 1. missing_in_clippings
- **定義**: BibTeXに記載されているがClippingsディレクトリに対応する.mdファイルが存在しない論文
- **処理方針**: **DOI情報表示のみ、処理スキップ**
- **ログレベル**: WARNING
- **表示内容**: Citation key、DOI（利用可能な場合）、クリック可能なDOIリンク

#### 2. orphaned_in_clippings  
- **定義**: Clippingsディレクトリに存在するがBibTeXファイルに記載されていない.mdファイル
- **処理方針**: **論文情報表示のみ、処理スキップ**
- **ログレベル**: WARNING  
- **表示内容**: ファイルパス、Citation key（ファイル名から推定）

### 処理対象論文の決定
エッジケースを除外した処理対象論文リストを生成します。

### 実行結果への影響
```python
execution_results = {
    'status': 'success',
    'executed_steps': [],
    'skipped_steps': [],
    'failed_steps': [],
    'total_papers_processed': 0,
    'skipped_papers': {
        'missing_in_clippings': [],
        'orphaned_in_clippings': []
    },
    'execution_time': 0
}
```

### 表示例
```
📊 Execution Summary:
Total papers in BibTeX: 15
Total markdown files: 12
Valid papers (both sources): 10
Skipped papers: 5
  - Missing markdown files: 3
  - Orphaned markdown files: 2

⚠️  Edge Cases Detected:
Missing markdown files for:
  - smith2023biomarkers (DOI: 10.1038/s41591-023-1234-5)
  - jones2024neural (DOI: 10.1126/science.xyz789)

Orphaned markdown files:
  - old_paper2022/old_paper2022.md
  - test_paper2021/test_paper2021.md
```

## 設計原則

### エッジケース処理の原則
1. **安全性優先**: 不完全なデータでの処理は行わない
2. **情報提供**: 問題の詳細を明確に報告
3. **処理継続**: 一部の問題で全体が停止しない
4. **ユーザビリティ**: DOIリンク等で問題解決を支援

### 情報提供の充実
1. **DOI表示**: 論文特定・取得支援のため
2. **クリック可能リンク**: ターミナルでの直接アクセス支援
3. **明確なメッセージ**: 問題の性質と対応方法の明示
4. **統計情報**: 全体的な処理状況の把握支援

## コマンドライン仕様

### 基本実行
```bash
# デフォルト実行（推奨・AI機能含む）
PYTHONPATH=code/py uv run python code/py/main.py run-integrated

# 実行計画確認
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --show-plan

# 強制再処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --force-reprocess
```

### AI機能制御
```bash
# AI機能無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-ai-features

# 特定AI機能のみ無効化
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --disable-tagger --disable-translate-abstract
```

### カスタム設定
```bash
# ワークスペース変更
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --workspace "/path/to/workspace"

# 特定論文のみ処理
PYTHONPATH=code/py uv run python code/py/main.py run-integrated --papers "paper1,paper2,paper3"
```