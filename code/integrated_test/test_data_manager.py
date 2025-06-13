"""
テストデータ管理

テストデータマスターの複製、管理、検証を担当。
"""

import shutil
from pathlib import Path


class TestDataManager:
    """テストデータ管理クラス"""
    
    def __init__(self, config_manager, logger):
        """
        テストデータ管理の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger("test_data_manager")
        
        # 設定値の取得
        self.config = config_manager.get_config().get('integrated_testing', {})
        self.data_config = self.config.get('test_data', {})
        
        # テストデータマスターパス
        self.master_path = Path(self.data_config.get('master_path', 'code/test_data_master'))
        
        self.logger.info("TestDataManager initialized")
    
    def setup_test_data(self, test_workspace):
        """
        テストデータのセットアップ
        
        Args:
            test_workspace (Path): テストワークスペースパス
        """
        self.logger.info(f"Setting up test data for workspace: {test_workspace}")
        
        # テストデータマスターの存在確認
        if not self.master_path.exists():
            raise FileNotFoundError(f"Test data master not found: {self.master_path}")
        
        # バックアップ作成（オプション）
        if self.data_config.get('backup_original', True):
            self._backup_original_data(test_workspace)
        
        # テストデータコピー
        self._copy_test_data(test_workspace)
        
        # データ検証（オプション）
        if self.data_config.get('validation_enabled', True):
            self._validate_test_data(test_workspace)
        
        self.logger.info("Test data setup completed")
    
    def _backup_original_data(self, test_workspace):
        """
        元データのバックアップ作成
        
        Args:
            test_workspace (Path): テストワークスペースパス
        """
        self.logger.info("Creating backup of original data")
        
        backup_dir = test_workspace / "backups" / "original"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # CurrentManuscript.bibのバックアップ
        bib_file = test_workspace / "CurrentManuscript.bib"
        if bib_file.exists():
            shutil.copy2(bib_file, backup_dir / "CurrentManuscript.bib")
        
        # Clippingsディレクトリのバックアップ
        clippings_dir = test_workspace / "Clippings"
        if clippings_dir.exists():
            shutil.copytree(clippings_dir, backup_dir / "Clippings", dirs_exist_ok=True)
        
        self.logger.info("Original data backup completed")
    
    def _copy_test_data(self, test_workspace):
        """
        テストデータのコピー
        
        Args:
            test_workspace (Path): テストワークスペースパス
        """
        self.logger.info("Copying test data from master")
        
        # CurrentManuscript.bibのコピー
        master_bib = self.master_path / "CurrentManuscript.bib"
        if master_bib.exists():
            shutil.copy2(master_bib, test_workspace / "CurrentManuscript.bib")
            self.logger.info("Copied CurrentManuscript.bib")
        
        # Clippingsディレクトリのコピー
        master_clippings = self.master_path / "Clippings"
        if master_clippings.exists():
            target_clippings = test_workspace / "Clippings"
            if target_clippings.exists():
                shutil.rmtree(target_clippings)
            shutil.copytree(master_clippings, target_clippings)
            self.logger.info("Copied Clippings directory")
        
        self.logger.info("Test data copy completed")
    
    def _validate_test_data(self, test_workspace):
        """
        テストデータの検証
        
        Args:
            test_workspace (Path): テストワークスペースパス
        """
        self.logger.info("Validating test data")
        
        validation_errors = []
        
        # CurrentManuscript.bibの存在確認
        bib_file = test_workspace / "CurrentManuscript.bib"
        if not bib_file.exists():
            validation_errors.append("CurrentManuscript.bib not found")
        else:
            # BibTeXファイルの基本チェック
            try:
                with open(bib_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content.strip():
                        validation_errors.append("CurrentManuscript.bib is empty")
                    elif '@' not in content:
                        validation_errors.append("CurrentManuscript.bib does not contain BibTeX entries")
            except Exception as e:
                validation_errors.append(f"Failed to read CurrentManuscript.bib: {e}")
        
        # Clippingsディレクトリの存在確認
        clippings_dir = test_workspace / "Clippings"
        if not clippings_dir.exists():
            validation_errors.append("Clippings directory not found")
        elif not any(clippings_dir.iterdir()):
            validation_errors.append("Clippings directory is empty")
        else:
            # Markdownファイルの基本チェック
            md_files = list(clippings_dir.glob("*.md"))
            if not md_files:
                validation_errors.append("No Markdown files found in Clippings directory")
        
        # 検証結果
        if validation_errors:
            error_msg = "Test data validation failed: " + "; ".join(validation_errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info("Test data validation passed")
    
    def get_test_data_summary(self, test_workspace):
        """
        テストデータの概要取得
        
        Args:
            test_workspace (Path): テストワークスペースパス
        
        Returns:
            dict: テストデータ概要
        """
        summary = {
            'workspace_path': str(test_workspace),
            'has_bibtex': False,
            'bibtex_entries': 0,
            'has_clippings': False,
            'clippings_count': 0,
            'markdown_files': []
        }
        
        # BibTeXファイル情報
        bib_file = test_workspace / "CurrentManuscript.bib"
        if bib_file.exists():
            summary['has_bibtex'] = True
            try:
                with open(bib_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    summary['bibtex_entries'] = content.count('@')
            except Exception:
                pass
        
        # Clippingsディレクトリ情報
        clippings_dir = test_workspace / "Clippings"
        if clippings_dir.exists():
            summary['has_clippings'] = True
            md_files = list(clippings_dir.glob("*.md"))
            summary['clippings_count'] = len(md_files)
            summary['markdown_files'] = [f.name for f in md_files]
        
        return summary 