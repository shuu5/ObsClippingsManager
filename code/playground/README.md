# Playground - 実験的機能

このディレクトリには、ObsClippingsManagerの実験的機能が含まれています。

## 引用文献統一機能

引用文献の表示形式を統一する機能です。

### 機能概要

- **範囲表記の展開**: `[2-4]`, `[4–8]` などを `[2,3,4]`, `[4,5,6,7,8]` に変換
- **連続引用の統合**: `[17], [18]` などを `[17,18]` に統合
- **統一形式**: すべての引用を `[数字]` 形式に統一

### ディレクトリ構成

```
code/playground/
├── citation_normalizer/          # メインモジュール
│   ├── __init__.py
│   └── citation_normalizer.py    # CitationNormalizerクラス
├── scripts/                      # 実行スクリプト
│   └── normalize_citations.py    # 引用統一処理スクリプト
├── tests/                        # テスト
│   └── test_citation_normalizer.py
├── run_tests.py                  # テスト実行スクリプト
└── README.md                     # このファイル
```

### 使用方法

#### 1. テストの実行

```bash
# playground配下のテストを実行
python code/playground/run_tests.py
```

#### 2. 引用統一処理の実行

```bash
# playground配下に移動
cd code/playground

# ドライランモード（変更内容の確認のみ）
uv run scripts/normalize_citations.py --dry-run

# 実際に変更を適用（バックアップ付き）
uv run scripts/normalize_citations.py --backup

# カスタムディレクトリを指定
uv run scripts/normalize_citations.py --directory /path/to/clippings
```

#### 3. プログラムから使用

```python
from citation_normalizer import CitationNormalizer

normalizer = CitationNormalizer()

# テキストの引用を統一
text = "研究 [4–8] と [10], [11] を参照"
normalized = normalizer.normalize_citations(text)
print(normalized)  # 研究 [4,5,6,7,8] と [10,11] を参照

# ファイルを処理
normalized_content = normalizer.process_file("example.md")

# ディレクトリを一括処理
results = normalizer.process_directory("./clippings", ".md")
```

### サポートしている引用パターン

#### 範囲表記（自動展開）
- `[2-4]` → `[2,3,4]` (ハイフン)
- `[4–8]` → `[4,5,6,7,8]` (エンダッシュ)
- `[10—13]` → `[10,11,12,13]` (エムダッシュ)

#### 連続引用（自動統合）
- `[17], [18]` → `[17,18]`
- `[1], [2], [3]` → `[1,2,3]`
- `[5] , [6] , [7]` → `[5,6,7]` (スペースあり)

#### 個別引用（そのまま）
- `[1]`, `[5]`, `[10]` → 変更なし

### 実行例

元のテキスト:
```
Pancreatic cancer is one of the most aggressive cancers [1]. 
Radiotherapy is an option for adjuvant therapy [2], [3]. 
Several studies have been conducted [4–8]. 
The proteasome activity is a common biologic property [14–21].
```

統一後:
```
Pancreatic cancer is one of the most aggressive cancers [1]. 
Radiotherapy is an option for adjuvant therapy [2,3]. 
Several studies have been conducted [4,5,6,7,8]. 
The proteasome activity is a common biologic property [14,15,16,17,18,19,20,21].
```

### 注意事項

- この機能は実験的なものです
- バックアップオプションの使用を推奨します
- 大きなファイルを処理する前は必ずドライランで確認してください 