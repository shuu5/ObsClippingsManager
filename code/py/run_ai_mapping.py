#!/usr/bin/env python3
"""
AI理解支援引用文献統合実行ツール v4.0

AIアシスタント（ChatGPT、Claude等）が引用文献を完全に理解できる
統合ファイルを生成します。

Usage:
    python run_ai_mapping.py --markdown-file paper.md --references-bib references.bib
    python run_ai_mapping.py --markdown-file paper.md --references-bib references.bib --no-ai-file
    python run_ai_mapping.py --markdown-file paper.md --references-bib references.bib --dry-run
"""

import argparse
import sys
import logging
from pathlib import Path

# プロジェクトルートを追加
sys.path.append(str(Path(__file__).parent))

from modules.shared.config_manager import ConfigManager
from modules.shared.logger import get_integrated_logger
from modules.ai_citation_support.ai_mapping_workflow import AIMappingWorkflow


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="AI理解支援引用文献統合ツール v4.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  %(prog)s --markdown-file paper.md --references-bib references.bib
  %(prog)s --markdown-file paper.md --references-bib references.bib --output-file paper_AI.md
  %(prog)s --markdown-file paper.md --references-bib references.bib --dry-run
  %(prog)s --markdown-file paper.md --references-bib references.bib --no-ai-file

注意:
  このツールは、Markdownファイル内の引用番号 [1], [2], [3] を
  references.bibファイルのcitation_keyとマッピングし、
  AIアシスタントが理解できる統合ファイルを生成します。
        """
    )
    
    # 必須引数
    parser.add_argument(
        '--markdown-file', '-m',
        required=True,
        help='対象のMarkdownファイル'
    )
    
    parser.add_argument(
        '--references-bib', '-r',
        required=True,
        help='対応するreferences.bibファイル'
    )
    
    # オプション引数
    parser.add_argument(
        '--output-file', '-o',
        help='AI用ファイルの出力先（省略時は自動生成）'
    )
    
    # --no-ai-fileオプションは削除されました
    # 仕様書に従い、常にYAMLヘッダー統合のみを実行
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='ドライラン実行（実際のファイル更新は行わない）'
    )
    
    # ログレベル設定
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='ログレベル（デフォルト: INFO）'
    )
    
    parser.add_argument(
        '--config',
        help='設定ファイルパス（省略時はデフォルト設定）'
    )
    
    parser.add_argument(
        '--preview',
        action='store_true',
        help='引用情報のプレビュー表示のみ実行'
    )
    
    args = parser.parse_args()
    
    # ログ設定
    logger = get_integrated_logger()
    logger.setup_loggers()
    main_logger = logger.get_logger("RunAIMapping")
    
    try:
        main_logger.info("=== AI理解支援引用文献統合ツール v4.0 開始 ===")
        
        # 設定管理初期化
        config_manager = ConfigManager(args.config)
        
        # ワークフロー初期化
        ai_workflow = AIMappingWorkflow(config_manager)
        
        # 入力ファイル検証
        markdown_path = Path(args.markdown_file)
        bib_path = Path(args.references_bib)
        
        if not markdown_path.exists():
            main_logger.error(f"Markdownファイルが見つかりません: {args.markdown_file}")
            return 1
        
        if not bib_path.exists():
            main_logger.error(f"references.bibファイルが見つかりません: {args.references_bib}")
            return 1
        
        main_logger.info(f"📄 Markdown: {markdown_path.name}")
        main_logger.info(f"📚 References: {bib_path.name}")
        
        # プレビューモード
        if args.preview:
            main_logger.info("🔍 引用情報プレビューモード")
            
            from modules.ai_citation_support.ai_assistant_file_generator import AIAssistantFileGenerator
            file_generator = AIAssistantFileGenerator(config_manager)
            
            preview = file_generator.generate_citation_preview(str(markdown_path))
            print("\n" + preview)
            return 0
        
        # ドライランモード
        if args.dry_run:
            main_logger.info("🧪 ドライランモード - 実際のファイル更新は行いません")
            
            dry_run_report = ai_workflow.dry_run_ai_mapping(
                str(markdown_path), str(bib_path)
            )
            
            print("\n" + "=" * 60)
            print(dry_run_report)
            print("=" * 60)
            
            main_logger.info("ドライラン完了")
            return 0
        
        # 実際の実行
        main_logger.info("🚀 AI理解支援引用文献統合を開始します...")
        
        # 仕様書に従い、AI用ファイル生成は行わない
        result = ai_workflow.execute_ai_mapping(
            markdown_file=str(markdown_path),
            references_bib=str(bib_path),
            generate_ai_file=False,
            output_file=None
        )
        
        # 結果表示
        print("\n" + "=" * 60)
        print("📊 AI理解支援引用文献統合結果")
        print("=" * 60)
        
        if result.success:
            print("✅ 処理が正常に完了しました")
            
            if result.statistics:
                stats = result.statistics
                print(f"📈 統計情報:")
                print(f"   作成されたマッピング: {stats.created_mappings}")
                print(f"   処理された引用数: {stats.total_citations_mapped}")
                print(f"   処理時間: {stats.processing_time:.2f}秒")
            
            # AI用ファイルは生成されません（仕様書に従い）
            print("📄 YAMLヘッダーに引用マッピングが統合されました")
            
            if result.warnings:
                print("⚠️  警告:")
                for warning in result.warnings:
                    print(f"   - {warning}")
            
            # 統計情報表示
            workflow_stats = ai_workflow.get_workflow_statistics()
            print(f"\n📊 ワークフロー統計:")
            print(f"   総処理ファイル数: {workflow_stats['total_files_processed']}")
            print(f"   マッピング成功率: {workflow_stats['mapping_success_rate']:.1%}")
            # AI用ファイル生成は行わないため、generation関連統計は表示しない
            
        else:
            print("❌ 処理に失敗しました")
            print(f"エラー: {result.error_message}")
            
            if result.warnings:
                print("警告:")
                for warning in result.warnings:
                    print(f"   - {warning}")
        
        print("=" * 60)
        
        main_logger.info("=== AI理解支援引用文献統合ツール v4.0 終了 ===")
        
        return 0 if result.success else 1
        
    except Exception as e:
        main_logger.error(f"予期しないエラーが発生しました: {e}")
        main_logger.error("詳細情報:", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 