# YAML Template Manager 仕様書

## 概要
- **責務**: 全モジュールが準拠すべきマスターYAML構造の定義と初期化テンプレート提供
- **依存**: 共有モジュール（ConfigManager, IntegratedLogger）
- **実行**: 統合ワークフローで自動実行

## 設計原則

### 1. **階層化設計**
- **メタデータ層**: システム共通情報（ルートレベル）
- **モジュール層**: 各機能の専用セクション
- **状態管理層**: 処理状態追跡

### 2. **初期化優先方式**
各モジュールは既存テンプレートに値を「追加・更新」のみ実行し、構造は変更しない

### 3. **名前空間分離**
モジュール間のキー衝突を防ぐため、モジュール専用セクションを事前定義

## マスターYAMLテンプレート

### 初期化テンプレート（空論文用）
```yaml
---
# === システムメタデータ（ルートレベル）===
citation_key: null                    # 必須：論文識別子
workflow_version: '3.2'              # 必須：システムバージョン
last_updated: null                    # 必須：最終更新日時
created_at: null                      # 必須：作成日時

# === 処理状態管理セクション ===
processing_status:
  # 基本ワークフロー
  organize: 'pending'
  sync: 'pending'
  fetch: 'pending'
  
  # AI機能ワークフロー
  section_parsing: 'pending'
  ai_citation_support: 'pending'
  tagger: 'pending' 
  translate_abstract: 'pending'
  ochiai_format: 'pending'
  
  # 統合処理
  final_sync: 'pending'

# === モジュール専用セクション ===
# Citation Management（引用文献管理）
citation_metadata:
  last_updated: null
  mapping_version: null
  source_bibtex: null
  total_citations: 0

citations: {}

# Paper Structure（論文構造）
paper_structure:
  parsed_at: null
  total_sections: 0
  sections: []
  section_types_found: []

# AI Generated Content（AI生成コンテンツ）
ai_content:
  # タグ生成
  tags:
    generated_at: null
    count: 0
    keywords: []
  
  # 要約翻訳
  abstract_japanese:
    generated_at: null
    content: null
  
  # 落合フォーマット
  ochiai_format:
    generated_at: null
    questions:
      what_is_this: null
      what_is_superior: null
      technical_key: null
      validation_method: null
      discussion_points: null
      next_papers: null

# === 統合ワークフロー実行記録 ===
execution_summary:
  executed_at: null
  total_execution_time: 0
  steps_executed: []
  steps_summary: {}
  edge_cases: {}

# === エラー・バックアップ情報 ===
error_history: []
backup_information:
  last_backup_at: null
  backup_location: null
  recovery_available: false
---
```

## モジュール別責任範囲

### 1. **ベースモジュール（StatusManager）**
```yaml
# 初期化時に設定
citation_key: "smith2023test"
created_at: "2025-01-15T09:00:00.123456+00:00"
last_updated: "2025-01-15T09:00:00.123456+00:00"
processing_status:
  organize: "pending"
  # 他の状態は変更せず
```

### 2. **引用文献パーサー（AICitationSupportWorkflow）**
```yaml
# citation_metadata と citations セクションのみ更新
citation_metadata:
  last_updated: "2025-01-15T10:30:00.123456"
  mapping_version: "2.0"
  source_bibtex: "references.bib"
  total_citations: 2

citations:
  1:
    citation_key: "jones2022biomarkers"
    title: "Advanced Biomarker Techniques"
    # ... 詳細情報

processing_status:
  ai_citation_support: "completed"  # 状態のみ更新
```

### 3. **セクション分割（SectionParsingWorkflow）**
```yaml
# paper_structure セクションのみ更新
paper_structure:
  parsed_at: "2025-01-15T10:35:00.123456"
  total_sections: 5
  sections:
    - title: "Abstract"
      level: 2
      # ... セクション詳細

processing_status:
  section_parsing: "completed"  # 状態のみ更新
```

### 4. **AI機能（TaggerWorkflow, TranslateWorkflow, OchiaiWorkflow）**
```yaml
# ai_content 配下の該当セクションのみ更新
ai_content:
  tags:
    generated_at: "2025-01-15T11:15:00.123456"
    count: 15
    keywords: ["oncology", "biomarkers", ...]
  
  abstract_japanese:
    generated_at: "2025-01-15T11:20:00.123456"
    content: "本研究では..."
  
  ochiai_format:
    generated_at: "2025-01-15T11:30:00.123456"
    questions:
      what_is_this: "KRT13タンパク質の..."

processing_status:
  tagger: "completed"
  translate_abstract: "completed"
  ochiai_format: "completed"
```

### 5. **統合ワークフロー（IntegratedWorkflow）**
```yaml
# execution_summary セクションのみ更新
execution_summary:
  executed_at: "2025-01-15T12:00:00.123456"
  total_papers_processed: 3
  total_execution_time: 180.5
  steps_executed: ["organize", "sync", ...]
  steps_summary:
    organize:
      status: "completed"
      papers_processed: 3
      execution_time: 15.2
  edge_cases:
    missing_in_clippings: 2
```

## 実装方針

### 1. **テンプレート初期化クラス**
```python
class YAMLTemplateManagerWorkflow:
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger.get_logger('YAMLTemplateManager')
    
    def initialize_template(self, citation_key):
        """新規論文用のマスターYAMLテンプレートを生成"""
        template = self._load_master_template()
        template['citation_key'] = citation_key
        template['created_at'] = datetime.now().isoformat()
        template['last_updated'] = datetime.now().isoformat()
        return template
    
    def validate_structure(self, yaml_header):
        """YAML構造の妥当性を検証"""
        required_sections = [
            'citation_key', 'processing_status', 'citation_metadata',
            'paper_structure', 'ai_content', 'execution_summary'
        ]
        return all(section in yaml_header for section in required_sections)
    
    def repair_structure(self, yaml_header):
        """不完全なYAML構造を修復"""
        master_template = self._load_master_template()
        return self._merge_preserving_data(master_template, yaml_header)
```

### 2. **モジュール基底クラス**
```python
class BaseWorkflow:
    def __init__(self, config_manager, logger):
        self.config_manager = config_manager
        self.logger = logger
        self.template_manager = YAMLTemplateManager(config_manager, logger)
    
    def update_yaml_section(self, file_path, section_path, new_data):
        """指定セクションのみを安全に更新"""
        yaml_header, content = self._load_yaml_and_content(file_path)
        
        # 構造検証・修復
        if not self.template_manager.validate_structure(yaml_header):
            yaml_header = self.template_manager.repair_structure(yaml_header)
        
        # 指定セクションのみ更新
        self._update_nested_dict(yaml_header, section_path, new_data)
        
        # 共通メタデータ更新
        yaml_header['last_updated'] = datetime.now().isoformat()
        
        self._save_yaml_and_content(file_path, yaml_header, content)
```

## 設定

### テンプレート管理設定
```yaml
yaml_template:
  enabled: true
  auto_initialize: true
  auto_repair: true
  validation_strict: true
  backup_before_repair: true
  
  template_version: "3.2"
  compatibility_check: true
  migration_support: true
  
  error_handling:
    validate_before_update: true
    backup_on_structure_change: true
    retry_on_validation_failure: true
```

## 利点

### 1. **構造の一貫性保証**
- 全モジュールが同じ構造に準拠
- キー衝突の完全回避
- 階層構造の統一

### 2. **安全性向上**
- 初期化テンプレートによる構造保証
- モジュール責任範囲の明確化
- 段階的データ追加による破綻回避

### 3. **保守性向上** 
- 新モジュール追加時の影響範囲限定
- YAML構造変更時の一元管理
- バージョン管理・マイグレーション対応

### 4. **デバッグ容易性**
- 構造検証による早期エラー発見
- セクション別の問題特定
- データ整合性チェック自動化

---

**重要**: このテンプレート仕様に基づき、既存の全仕様書を更新し、各モジュールの実装を段階的に改修してください。 