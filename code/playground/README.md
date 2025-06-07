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

## 🆕 BibTeX引用番号マッピング機能

論文本文の引用番号（[1], [2], [^1], [^2]等）をreferences.bibファイル内の文献エントリに`citation_number`プロパティとして追加する機能です。

### 特徴

- **引用番号の自動検出**: 論文本文から通常の引用番号（[1], [2]）と脚注形式（[^1], [^2]）の両方を検出
- **統合後形式への対応**: 引用統一処理後の形式（[1,2,3]）からも個別番号を抽出
- **自動マッピング**: 検出された引用番号をBibTeXエントリの出現順序に対応付け
- **citation_numberプロパティ追加**: 各BibTeXエントリに`citation_number = {番号}`を追加
- **安全な処理**: バックアップ作成とドライラン機能

### 使用方法

```bash
# 全論文に対してcitation_numberを追加（バックアップ付き）
uv run scripts/map_citations_to_bib.py --backup

# 特定の論文のみ処理
uv run scripts/map_citations_to_bib.py --paper-dir Clippings/論文名 --backup

# ドライラン（変更内容の確認のみ）
uv run scripts/map_citations_to_bib.py --dry-run
```

### 出力例

BibTeXファイルに以下のようにcitation_numberが追加されます：

```bibtex
@article{Sung2021CCJ,
  title = {Global cancer statistics 2020: GLOBOCAN estimates...},
  author = {Sung},
  year = {2021},
  journal = {CA Cancer J Clin},
  volume = {71},
  pages = {209},
  doi = {10.3322/caac.21660},
  note = {Retrieved from CrossRef}
  citation_number = {1}
}
```

これにより、論文本文の引用[1]がSung2021CCJ論文を指していることが明確になります。

### 対応する引用形式

- 通常の引用番号: `[1]`, `[2]`, `[3]` 
- 脚注形式: `[^1]`, `[^2]`, `[^3]`
- 統合後形式: `[1,2,3]`, `[^4,^5,^6]`
- 範囲展開後: `[4,5,6,7,8]` (元々は`[4-8]`) 