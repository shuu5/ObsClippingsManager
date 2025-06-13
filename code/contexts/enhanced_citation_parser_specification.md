# AI理解支援引用文献パーサー機能仕様書

## 概要
- **責務**: references.bibの内容をYAMLヘッダーに統合しAI理解支援機能を提供
- **依存**: organize → sync → fetch
- **実行**: 統合ワークフローで自動実行

## 処理フロー図
```mermaid
flowchart TD
    A["入力データ"] --> B["AI引用解析処理開始"]
    B --> C["データ検証"]
    C --> D["BibTeXファイル読み込み"]
    D --> E["BibTeXエントリー解析"]
    E --> F["引用マッピング作成"]
    F --> G["YAMLヘッダー統合"]
    G --> H["結果出力"]
    H --> I["完了"]
    
    C -->|エラー| J["エラーハンドリング"]
    D -->|ファイル不正| K["BibTeX修復"]
    E -->|解析失敗| L["パース再試行"]
    J --> M["失敗ログ記録"]
    K --> D
    L --> E
```

## モジュール関係図
```mermaid
graph LR
    A["基本機能"] --> B["AI引用解析"]
    
    C["BibTeXファイル"] -.-> B
    D["設定ファイル"] -.-> B
    E["ログシステム"] -.-> B
    
    B --> F["セクション分割"]
    B --> G["AIタグ付け"]
    B --> H["要約翻訳"]
    B --> I["落合フォーマット"]
    B --> J["統合ワークフロー"]
```

## YAMLヘッダー形式

### 入力
```yaml
---
citation_key: smith2023test
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai_citation_support: pending
---
```

### 出力
```yaml
---
citation_key: smith2023test
citation_metadata:
  last_updated: '2025-01-15T10:30:00.123456'
  mapping_version: '2.0'
  source_bibtex: references.bib
  total_citations: 2
citations:
  1:
    authors: Smith
    citation_key: smith2023test
    doi: 10.1158/0008-5472.CAN-23-0123
    journal: Cancer Research
    title: Novel Method for Cancer Cell Analysis
    year: 2023
  2:
    authors: Jones
    citation_key: jones2022biomarkers
    doi: 10.1038/s41591-022-0456-7
    journal: Nature Medicine
    title: Advanced Biomarker Techniques in Oncology
    year: 2022
processing_status:
  organize: completed
  sync: completed
  fetch: completed
  ai_citation_support: completed
workflow_version: '3.2'
---
```

## 実装
```python
class AICitationSupportWorkflow:
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('AICitationSupportWorkflow')
        self.bibtex_parser = BibTeXParser(logger.get_logger('BibTeXParser'))
        
    def process_items(self, input_dir, target_items=None):
        """論文の一括AI理解支援処理"""
        status_manager = StatusManager(self.config_manager, self.logger)
        papers_needing_processing = status_manager.get_papers_needing_processing(
            input_dir, 'ai_citation_support', target_items
        )
        
        # BibTeXファイルを読み込み
        bibtex_file = self.config_manager.get_bibtex_file()
        bibtex_entries = self.bibtex_parser.parse_file(bibtex_file)
        
        for paper_path in papers_needing_processing:
            try:
                citation_mapping = self.create_citation_mapping(bibtex_entries)
                self.update_yaml_with_citations(paper_path, citation_mapping)
                status_manager.update_status(input_dir, paper_path, 'ai_citation_support', 'completed')
            except Exception as e:
                self.logger.error(f"Failed to add citation support for {paper_path}: {e}")
                status_manager.update_status(input_dir, paper_path, 'ai_citation_support', 'failed')
    
    def create_citation_mapping(self, bibtex_entries):
        """BibTeXエントリーから引用マッピングを作成"""
        citations = {}
        citation_metadata = {
            'last_updated': datetime.now().isoformat(),
            'mapping_version': '2.0',
            'source_bibtex': 'references.bib',
            'total_citations': len(bibtex_entries)
        }
        
        for index, (citation_key, entry) in enumerate(bibtex_entries.items(), 1):
            citations[index] = {
                'citation_key': citation_key,
                'title': entry.get('title', ''),
                'authors': entry.get('author', ''),
                'year': entry.get('year', ''),
                'journal': entry.get('journal', ''),
                'doi': entry.get('doi', '')
            }
            
        return {
            'citation_metadata': citation_metadata,
            'citations': citations
        }
```

## 設定
```yaml
ai_citation_support:
  enabled: true
  mapping_version: "2.0"
  preserve_existing_citations: true
  update_existing_mapping: true
  batch_size: 10
  retry_attempts: 3
  error_handling:
    validate_bibtex_before_processing: true
    backup_on_mapping_failure: true
    retry_on_api_errors: true
    max_retry_attempts: 3
  backup_strategy:
    backup_before_citation_integration: true
    keep_mapping_history: true
    backup_bibtex_source: true
```

## マッピングルール

### シンプルマッピング原則
1. **順序保持**: references.bibのエントリー順序をそのまま維持
2. **重複包含**: 重複エントリーも含めて全て処理（BibTeXファイルの構造保持）
3. **1:1対応**: BibTeXエントリー番号 = 引用番号（1から開始）
4. **プレースホルダーなし**: 存在しないエントリーに対する自動生成なし

### データ一貫性
- `total_citations` = BibTeXファイルのエントリー数
- `citations` の最大キー = `total_citations`
- 欠番なし（1からtotal_citationsまで連続）

## テスト仕様

### マッピング作成テスト
マッピング機能の正確性とデータ一貫性を検証します。

### 重複処理テスト
重複を含むBibTeXファイルでも全エントリーを正確に処理することを確認します。