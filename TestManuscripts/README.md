# ObsClippingsManager テストデータセット

このディレクトリには、ObsClippingsManagerの機能テスト用に本番データから簡略化されたテストデータが含まれています。

## 構造

```
TestManuscripts/
├── CurrentManuscript.bib    # Zotero生成のBibTeXファイル（5論文）
├── Clippings/              # 変換前のMarkdownファイル（4論文）
│   ├── Cytokeratin 13 (CK13) expression in cancer...md
│   ├── KRT13 is upregulated in pancreatic cancer...md
│   ├── Keratin 13 expression reprograms bone...md
│   └── Keratin Profiling by Single-Cell RNA...md
└── README.md               # このファイル
```

## 特徴

### 本番環境の再現
- Zotero生成のBibTeXファイルそのまま
- Clippingsディレクトリに変換前のMarkdownファイル
- ファイル名に特殊文字やスペースを含む現実的な状況

### 引用形式の多様性
各.mdファイルには以下の引用形式が含まれています：

1. **URL付き引用**: `[1](https://example.com/...)`
2. **数字のみ引用**: `[1]`, `[2]`
3. **上付き数字**: `¹`, `²`, `³`
4. **範囲指定**: `[12-14]`, `[15-17]`
5. **著者年形式**: `(Johnson et al., 2021)`
6. **カンマ区切り**: `[8, 9]`
7. **セミコロン区切り**: `[7; 8]`
8. **ダッシュ範囲**: `[5] - [7]`

### データサイズ
- 本番データの約1/10のサイズに削減
- 各論文の引用数を10-50個程度に制限
- テスト実行時間の大幅短縮

## 使用方法

```bash
# EnhancedIntegratedWorkflowでテスト実行
cd /home/user/proj/ObsClippingsManager
uv run code/py/modules/workflows/enhanced_integrated_workflow.py /home/user/proj/ObsClippingsManager/TestManuscripts
```

## データ内容

### 論文リスト
1. **huWY2021IJMS**: Keratin Profiling by Single-Cell RNA-Sequencing...
2. **lennartzM2023APMIS**: Cytokeratin 13 Expression in Cancer... (軽量版、引用8件)
3. **liQ2016Oncotarget**: Keratin 13 expression reprograms bone and brain...
4. **takenakaW2023J.Radiat.Res.Tokyo**: KRT13 is upregulated in pancreatic cancer...
5. **yinL2022BreastCancerRes**: KRT13 Promotes Stemness... (BibTeXのみ、.mdなし)

### テストシナリオ
- 4つの論文は.mdファイルが存在（処理対象）
- 1つの論文は.mdファイルが未ダウンロード（スキップ対象）
- 様々な引用パターンの変換テスト
- 各APIでの引用情報取得テスト（CrossRef、PubMed、SemanticScholar等）
- ディレクトリ作成とファイル移動テスト
- メタデータ補完テスト

## 拡張性

新しい仕様やエッジケース追加時は：
1. 新しい引用形式を含む.mdファイルを追加
2. CurrentManuscript.bibに対応するエントリを追加
3. README.mdを更新

このテストデータセットにより、実際の本番環境での動作を高精度で検証できます。 