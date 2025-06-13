"""
統合テスト実行スクリプト

コマンドライン経由で統合テストを実行する。
Click ベースのCLIインターフェース。
"""

import click
import sys
from pathlib import Path

# プロジェクトルートを追加
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from code.py.modules.shared.config_manager import ConfigManager
from code.py.modules.shared.integrated_logger import IntegratedLogger
from code.integrated_test.integrated_test_runner import IntegratedTestRunner


@click.command()
@click.option('--test-type', default='full', 
              type=click.Choice(['full', 'regression', 'performance']),
              help='統合テストの種類')
@click.option('--reset-environment', is_flag=True,
              help='テスト環境の強制リセット')
@click.option('--keep-environment', is_flag=True,
              help='テスト完了後の環境保持（デバッグ用）')
@click.option('--specific-modules', 
              help='特定モジュールのみテスト（カンマ区切り）')
@click.option('--disable-ai-features', is_flag=True,
              help='AI機能を無効化してテスト実行')
@click.option('--verbose', is_flag=True,
              help='詳細ログ出力')
@click.option('--report-format', default='json',
              type=click.Choice(['json', 'html', 'text']),
              help='テストレポート形式')
def run_integrated_test(test_type, reset_environment, keep_environment,
                       specific_modules, disable_ai_features, verbose, report_format):
    """統合テスト実行コマンド"""
    
    click.echo(f"🔄 Starting integrated test (type: {test_type})")
    
    try:
        # 設定管理とロガーの初期化
        config_manager = ConfigManager()
        logger = IntegratedLogger(config_manager)
        
        if verbose:
            logger.set_level("DEBUG")
        
        # 統合テストランナーの初期化
        test_runner = IntegratedTestRunner(config_manager, logger)
        
        # テストオプションの準備
        test_options = {
            'reset_environment': reset_environment,
            'keep_environment': keep_environment,
            'disable_ai_features': disable_ai_features,
            'verbose': verbose,
            'report_format': report_format
        }
        
        # テストタイプ別実行
        if test_type == 'full':
            click.echo("📋 Executing full integration test...")
            result = test_runner.run_full_integration_test(test_options)
            
        elif test_type == 'regression':
            modules = []
            if specific_modules:
                modules = [m.strip() for m in specific_modules.split(',')]
            
            click.echo(f"🔍 Executing regression test for modules: {modules or 'all'}")
            result = test_runner.run_regression_test(modules)
            
        elif test_type == 'performance':
            click.echo("⚡ Executing performance test...")
            result = test_runner.run_performance_test()
        
        # 結果表示
        _display_test_result(result, report_format)
        
        # 終了コード設定
        if result['status'] == 'passed':
            click.echo("✅ Integrated test completed successfully")
            sys.exit(0)
        else:
            click.echo("❌ Integrated test failed")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"💥 Error during integrated test execution: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


def _display_test_result(result, report_format):
    """
    テスト結果の表示
    
    Args:
        result (dict): テスト結果
        report_format (str): レポート形式
    """
    click.echo("\n" + "="*60)
    click.echo("📊 INTEGRATED TEST RESULT")
    click.echo("="*60)
    
    # 基本情報
    click.echo(f"Session ID: {result.get('test_session_id', 'unknown')}")
    click.echo(f"Status: {result.get('status', 'unknown')}")
    click.echo(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")
    
    # エラー情報
    if 'error' in result:
        click.echo(f"❌ Error: {result['error']}")
    
    # 詳細情報（JSON形式）
    if report_format == 'json':
        click.echo("\n📄 Detailed Result (JSON):")
        import json
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 検証結果（利用可能な場合）
    if 'validation_result' in result:
        validation = result['validation_result']
        click.echo(f"\n🔍 Validation Results:")
        click.echo(f"  - YAML Headers: {'✅' if validation.get('yaml_headers_valid') else '❌'}")
        click.echo(f"  - File Structure: {'✅' if validation.get('file_structure_correct') else '❌'}")
        click.echo(f"  - Citation Data: {'✅' if validation.get('citation_data_complete') else '❌'}")
        
        if validation.get('validation_errors'):
            click.echo("\n❌ Validation Errors:")
            for error in validation['validation_errors']:
                click.echo(f"  - {error}")
    
    click.echo("="*60)


if __name__ == '__main__':
    run_integrated_test() 