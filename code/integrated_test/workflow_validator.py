"""
ワークフロー検証

統合テストでの処理結果の妥当性検証を担当。
"""

import yaml
from pathlib import Path


class WorkflowValidator:
    """ワークフロー検証クラス"""
    
    def __init__(self, config_manager, logger):
        """
        ワークフロー検証の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger("workflow_validator")
        
        self.logger.info("WorkflowValidator initialized")
    
    def validate_processing_results(self, workspace_path):
        """
        処理結果の妥当性検証
        
        Args:
            workspace_path (Path): ワークスペースパス
        
        Returns:
            dict: 検証結果
        """
        self.logger.info(f"Validating processing results in: {workspace_path}")
        
        validation_result = {
            'workspace_path': str(workspace_path),
            'yaml_headers_valid': False,
            'file_structure_correct': False,
            'citation_data_complete': False,
            'validation_errors': [],
            'validation_warnings': []
        }
        
        try:
            # YAMLヘッダー検証
            yaml_result = self.validate_yaml_headers(workspace_path / "Clippings")
            validation_result['yaml_headers_valid'] = yaml_result['valid']
            validation_result['validation_errors'].extend(yaml_result.get('errors', []))
            
            # ファイル構造検証
            structure_result = self.validate_file_structure(workspace_path)
            validation_result['file_structure_correct'] = structure_result['valid']
            validation_result['validation_errors'].extend(structure_result.get('errors', []))
            
            # 引用データ検証
            citation_result = self._validate_citation_data(workspace_path)
            validation_result['citation_data_complete'] = citation_result['valid']
            validation_result['validation_errors'].extend(citation_result.get('errors', []))
            
            # 全体結果判定
            validation_result['overall_valid'] = (
                validation_result['yaml_headers_valid'] and
                validation_result['file_structure_correct'] and
                validation_result['citation_data_complete']
            )
            
            self.logger.info(f"Validation completed: {'PASSED' if validation_result['overall_valid'] else 'FAILED'}")
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Validation failed with exception: {e}")
            validation_result['validation_errors'].append(f"Validation exception: {str(e)}")
            validation_result['overall_valid'] = False
            return validation_result
    
    def validate_yaml_headers(self, clippings_dir):
        """
        YAMLヘッダー形式検証
        
        Args:
            clippings_dir (Path): Clippingsディレクトリパス
        
        Returns:
            dict: 検証結果
        """
        self.logger.info(f"Validating YAML headers in: {clippings_dir}")
        
        result = {
            'valid': True,
            'checked_files': 0,
            'valid_files': 0,
            'errors': [],
            'warnings': []
        }
        
        if not clippings_dir.exists():
            result['valid'] = False
            result['errors'].append(f"Clippings directory not found: {clippings_dir}")
            return result
        
        # Markdownファイルのチェック
        md_files = list(clippings_dir.glob("*.md"))
        result['checked_files'] = len(md_files)
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # YAMLヘッダーの存在チェック
                if content.startswith('---'):
                    # YAMLブロックの抽出
                    yaml_end = content.find('---', 3)
                    if yaml_end > 0:
                        yaml_content = content[3:yaml_end].strip()
                        try:
                            yaml_data = yaml.safe_load(yaml_content)
                            if isinstance(yaml_data, dict):
                                result['valid_files'] += 1
                            else:
                                result['errors'].append(f"Invalid YAML structure in {md_file.name}")
                                result['valid'] = False
                        except yaml.YAMLError as e:
                            result['errors'].append(f"YAML parsing error in {md_file.name}: {e}")
                            result['valid'] = False
                    else:
                        result['errors'].append(f"Incomplete YAML header in {md_file.name}")
                        result['valid'] = False
                else:
                    result['warnings'].append(f"No YAML header found in {md_file.name}")
                    
            except Exception as e:
                result['errors'].append(f"Failed to read {md_file.name}: {e}")
                result['valid'] = False
        
        self.logger.info(f"YAML header validation: {result['valid_files']}/{result['checked_files']} files valid")
        return result
    
    def validate_file_structure(self, workspace_path):
        """
        ファイル構造検証
        
        Args:
            workspace_path (Path): ワークスペースパス
        
        Returns:
            dict: 検証結果
        """
        self.logger.info(f"Validating file structure in: {workspace_path}")
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'structure_checks': {}
        }
        
        # 必須ファイル・ディレクトリのチェック
        required_items = {
            'CurrentManuscript.bib': 'file',
            'Clippings': 'directory',
            'backups': 'directory',
            'logs': 'directory'
        }
        
        for item_name, item_type in required_items.items():
            item_path = workspace_path / item_name
            if item_type == 'file':
                exists = item_path.is_file()
            else:
                exists = item_path.is_dir()
            
            result['structure_checks'][item_name] = exists
            
            if not exists:
                if item_name in ['CurrentManuscript.bib', 'Clippings']:
                    result['errors'].append(f"Required {item_type} missing: {item_name}")
                    result['valid'] = False
                else:
                    result['warnings'].append(f"Optional {item_type} missing: {item_name}")
        
        # Clippingsディレクトリの内容チェック
        clippings_dir = workspace_path / "Clippings"
        if clippings_dir.exists():
            md_files = list(clippings_dir.glob("*.md"))
            result['structure_checks']['markdown_files_count'] = len(md_files)
            
            if len(md_files) == 0:
                result['warnings'].append("No Markdown files found in Clippings directory")
        
        self.logger.info(f"File structure validation: {'PASSED' if result['valid'] else 'FAILED'}")
        return result
    
    def _validate_citation_data(self, workspace_path):
        """
        引用データ検証
        
        Args:
            workspace_path (Path): ワークスペースパス
        
        Returns:
            dict: 検証結果
        """
        self.logger.info("Validating citation data")
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'bibtex_entries': 0,
            'markdown_files': 0
        }
        
        # BibTeXファイルの検証
        bib_file = workspace_path / "CurrentManuscript.bib"
        if bib_file.exists():
            try:
                with open(bib_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    result['bibtex_entries'] = content.count('@')
                    
                    if result['bibtex_entries'] == 0:
                        result['errors'].append("No BibTeX entries found")
                        result['valid'] = False
                        
            except Exception as e:
                result['errors'].append(f"Failed to read BibTeX file: {e}")
                result['valid'] = False
        else:
            result['errors'].append("CurrentManuscript.bib not found")
            result['valid'] = False
        
        # Markdownファイルの検証
        clippings_dir = workspace_path / "Clippings"
        if clippings_dir.exists():
            md_files = list(clippings_dir.glob("*.md"))
            result['markdown_files'] = len(md_files)
            
            if len(md_files) == 0:
                result['errors'].append("No Markdown files found")
                result['valid'] = False
        else:
            result['errors'].append("Clippings directory not found")
            result['valid'] = False
        
        self.logger.info(f"Citation data validation: {'PASSED' if result['valid'] else 'FAILED'}")
        return result 