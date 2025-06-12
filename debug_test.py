import tempfile
import os
import sys
sys.path.append('code/py')

from click.testing import CliRunner
from unittest.mock import Mock, patch
import main

# テストデータ設定
config_content = '''
{
  "common": {
    "workspace_path": "/tmp/test",
    "bibtex_file": "/tmp/test/test.bib",
    "clippings_dir": "/tmp/test/Clippings",
    "output_dir": "/tmp/test/Clippings",
    "dry_run": false,
    "backup_enabled": false
  },
  "citation_fetcher": {
    "enable_enrichment": true
  }
}
'''

# 一時ファイル作成
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    f.write(config_content)
    config_file = f.name

runner = CliRunner()

# モックパッチでテスト実行
with patch('main.IntegratedWorkflow') as mock_workflow, \
     patch('main.IntegratedLogger') as mock_logger:
    
    # モック設定
    mock_logger_instance = Mock()
    mock_workflow_instance = Mock()
    
    mock_logger.return_value = mock_logger_instance
    mock_workflow.return_value = mock_workflow_instance
    
    # ワークフロー実行の成功をモック - 'success'キーを追加
    mock_workflow_instance.execute.return_value = {
        'status': 'success',
        'success': True,
        'completed_steps': ['organize', 'sync', 'fetch'],
        'processed_papers': 3
    }
    
    # テスト実行
    result = runner.invoke(main.cli, [
        '--config', config_file,
        'run-integrated',
        '--sync-first',
        '--fetch-citations',
        '--auto-approve'
    ])
    
    print(f'Exit code: {result.exit_code}')
    print(f'Output: {result.output}')
    print(f'Exception: {result.exception}')
    if result.exception:
        import traceback
        traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

# クリーンアップ
os.unlink(config_file) 