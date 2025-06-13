"""
テスト環境管理

分離されたテスト環境の作成、設定、クリーンアップを担当。
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class TestEnvironmentManager:
    """テスト環境管理クラス"""
    
    def __init__(self, config_manager, logger):
        """
        テスト環境管理の初期化
        
        Args:
            config_manager: 設定管理オブジェクト
            logger: ログ出力オブジェクト
        """
        self.config_manager = config_manager
        self.logger = logger
        
        # 設定値の取得
        self.config = config_manager.get_config().get('integrated_testing', {})
        self.env_config = self.config.get('test_environment', {})
        
        self.logger.info("TestEnvironmentManager initialized")
    
    def create_isolated_environment(self, test_session_id):
        """
        分離されたテスト環境作成
        
        Args:
            test_session_id (str): テストセッションID
        
        Returns:
            Path: テストワークスペースパス
        """
        self.logger.info(f"Creating isolated environment for session: {test_session_id}")
        
        # ベースパスとプレフィックスの取得
        base_path = self.env_config.get('base_path', '/tmp')
        prefix = self.env_config.get('prefix', 'ObsClippingsManager_IntegratedTest')
        
        # テストワークスペースディレクトリ作成
        workspace_name = f"{prefix}_{test_session_id}"
        workspace_path = Path(base_path) / workspace_name
        
        # ディレクトリ作成
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 必要なサブディレクトリ作成
        (workspace_path / "Clippings").mkdir(exist_ok=True)
        (workspace_path / "backups").mkdir(exist_ok=True)
        (workspace_path / "logs").mkdir(exist_ok=True)
        
        # テストセッション情報ファイル作成
        session_info = {
            'test_session_id': test_session_id,
            'created_at': datetime.now().isoformat(),
            'workspace_path': str(workspace_path),
            'isolated': True
        }
        
        session_file = workspace_path / ".test_session_info.yaml"
        with open(session_file, 'w', encoding='utf-8') as f:
            import yaml
            yaml.dump(session_info, f, default_flow_style=False, allow_unicode=True)
        
        self.logger.info(f"Isolated environment created: {workspace_path}")
        return workspace_path
    
    def setup_test_workspace(self, workspace_path, test_data_path):
        """
        テストワークスペース構築
        
        Args:
            workspace_path (Path): ワークスペースパス
            test_data_path (Path): テストデータパス
        """
        self.logger.info(f"Setting up test workspace: {workspace_path}")
        
        # テストデータをワークスペースにコピー
        if test_data_path.exists():
            if (test_data_path / "CurrentManuscript.bib").exists():
                shutil.copy2(test_data_path / "CurrentManuscript.bib", workspace_path)
            
            clippings_src = test_data_path / "Clippings"
            if clippings_src.exists():
                clippings_dst = workspace_path / "Clippings"
                if clippings_dst.exists():
                    shutil.rmtree(clippings_dst)
                shutil.copytree(clippings_src, clippings_dst)
        
        self.logger.info("Test workspace setup completed")
    
    def cleanup_environment(self, workspace_path, force=False):
        """
        テスト環境クリーンアップ
        
        Args:
            workspace_path (Path): ワークスペースパス
            force (bool): 強制削除フラグ
        """
        self.logger.info(f"Cleaning up environment: {workspace_path}")
        
        # auto_cleanupが無効で強制でない場合はスキップ
        if not force and not self.env_config.get('auto_cleanup', True):
            self.logger.info("Auto cleanup disabled, skipping cleanup")
            return
        
        # ワークスペースディレクトリの削除
        if workspace_path.exists():
            try:
                shutil.rmtree(workspace_path)
                self.logger.info(f"Environment cleanup completed: {workspace_path}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup environment: {e}")
                raise
        else:
            self.logger.warning(f"Workspace path does not exist: {workspace_path}") 