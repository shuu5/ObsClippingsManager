"""
引用文献パーサーワークフロー

様々な形式の引用文献を統一フォーマットに変換し、
リンク付き引用からの対応表生成を行うワークフローを提供します。
"""

import time
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import click

from ..shared.exceptions import (
    CitationParserError, InvalidCitationPatternError, CitationParseTimeoutError
)
from ..citation_parser.citation_parser import CitationParser


class CitationParserWorkflow:
    """引用文献パーサーワークフロー"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config_manager = config_manager
        self.logger = logger.get_logger('Workflows.CitationParser')
        self.config = config_manager.get_citation_parser_config()
        
        # Citation Parserの初期化
        # 設定辞書から一時的な設定ファイルを作成するか、直接初期化する
        self.parser = CitationParser()
        
    def execute(self, input_file: str = None, clippings_dir: str = None, **options) -> Tuple[bool, Dict[str, Any]]:
        """
        引用文献パーサーワークフローを実行
        
        Args:
            input_file: 入力Markdownファイルパス（単一ファイル処理用）
            clippings_dir: Clippingsディレクトリパス（ディレクトリ処理用）
            **options: 実行オプション
                - output_file: 出力ファイルパス（省略時は標準出力）
                - pattern_type: パース対象パターン（basic|advanced|all）
                - output_format: 出力フォーマット（unified|table|json）
                - enable_link_extraction: リンク抽出有効化
                - expand_ranges: 範囲引用展開
                - dry_run: ドライラン実行
                - verbose: 詳細出力
        
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        start_time = time.time()
        
        try:
            # 入力の検証とモード決定
            if clippings_dir:
                # ディレクトリ処理モード
                return self._execute_directory_mode(clippings_dir, options, start_time)
            elif input_file:
                # 単一ファイル処理モード
                return self._execute_single_file_mode(input_file, options, start_time)
            else:
                raise ValueError("Either input_file or clippings_dir must be specified")
                
        except Exception as e:
            self.logger.error(f"Citation parser workflow failed: {e}")
            return False, {"error": str(e), "processing_time": time.time() - start_time}
    
    def _execute_single_file_mode(self, input_file: str, options: Dict, start_time: float) -> Tuple[bool, Dict[str, Any]]:
        """単一ファイル処理モード"""
        self.logger.info("Starting citation parser workflow")
        self.logger.info(f"Input file: {input_file}")
        
        # 実行オプションのマージ
        execution_options = {**self.config, **options}
        
        # 設定を一時的に更新
        original_config = self.config.copy()
        self.config.update(execution_options)
        
        try:
            # 結果辞書の初期化
            results = {
                "input_file": input_file,
                "execution_options": execution_options,
                "statistics": {},
                "processing_time": 0
            }
            
            # 入力ファイル検証
            self.logger.info("Validating input file")
            if not self.validate_inputs(input_file):
                raise CitationParserError(f"Input validation failed for: {input_file}")
            
            # ドライラン処理
            if execution_options.get('dry_run', False):
                results.update(self._execute_dry_run(input_file, execution_options))
                return True, results
            
            # ファイル読み込み
            self.logger.info("Reading input file")
            with open(input_file, 'r', encoding='utf-8') as f:
                input_text = f.read()
            
            # 引用文献パース実行
            self.logger.info("Processing citations")
            parse_result = self.parser.parse_document(input_text)
            
            # 結果の処理
            results.update({
                "converted_text": parse_result.converted_text,
                "link_table": parse_result.link_table,
                "statistics": {
                    "total_citations": parse_result.statistics.total_citations,
                    "converted_citations": parse_result.statistics.converted_citations,
                    "error_count": len(parse_result.errors),
                    "processing_time": time.time() - start_time
                },
                "errors": parse_result.errors
            })
            
            # 出力ファイル処理
            output_file = execution_options.get('output_file')
            if output_file:
                self.logger.info(f"Writing output to: {output_file}")
                self._write_output_file(output_file, parse_result, execution_options)
                results["output_file"] = output_file
            else:
                # 標準出力への表示
                self._display_results(parse_result, execution_options)
            
            # 統計情報のログ出力
            stats = results["statistics"]
            self.logger.info(f"Processed {stats['total_citations']} citations")
            self.logger.info(f"Converted {stats['converted_citations']} citations")
            if stats['error_count'] > 0:
                self.logger.warning(f"Encountered {stats['error_count']} errors")
            
            results["processing_time"] = time.time() - start_time
            self.logger.info(f"Citation parser workflow completed in {results['processing_time']:.2f} seconds")
            
            return True, results
            
        finally:
            # 設定を復元
            self.config = original_config
    
    def _execute_directory_mode(self, clippings_dir: str, options: Dict, start_time: float) -> Tuple[bool, Dict[str, Any]]:
        """ディレクトリ処理モード：Clippingsディレクトリ内の全.mdファイルを処理"""
        from pathlib import Path
        import glob
        
        self.logger.info(f"Starting citation parser workflow for directory: {clippings_dir}")
        
        clippings_path = Path(clippings_dir)
        if not clippings_path.exists():
            raise ValueError(f"Clippings directory does not exist: {clippings_dir}")
        
        # .mdファイルを検索
        md_files = glob.glob(str(clippings_path / "*" / "*.md"))
        
        if not md_files:
            self.logger.warning(f"No .md files found in {clippings_dir}")
            return True, {
                "success": True,
                "clippings_dir": clippings_dir,
                "processed_files": [],
                "total_files": 0,
                "processing_time": time.time() - start_time
            }
        
        self.logger.info(f"Found {len(md_files)} .md files to process in {clippings_dir}")
        
        # 実行オプションのマージ
        execution_options = {**self.config, **options}
        
        processed_files = []
        total_citations = 0
        total_converted = 0
        total_errors = 0
        
        for md_file in md_files:
            try:
                self.logger.info(f"Processing: {md_file}")
                
                # ドライランモードでない場合のみ実際に処理
                if not execution_options.get('dry_run', False):
                    # ファイル読み込み
                    with open(md_file, 'r', encoding='utf-8') as f:
                        input_text = f.read()
                    
                    # 引用文献パース実行
                    parse_result = self.parser.parse_document(input_text)
                    
                    # インプレース更新（元ファイルを更新）
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(parse_result.converted_text)
                    
                    # 統計情報を更新
                    total_citations += parse_result.statistics.total_citations
                    total_converted += parse_result.statistics.converted_citations
                    total_errors += len(parse_result.errors)
                    
                    processed_files.append({
                        "file": md_file,
                        "citations_found": parse_result.statistics.total_citations,
                        "citations_converted": parse_result.statistics.converted_citations,
                        "errors": len(parse_result.errors)
                    })
                    
                    self.logger.info(f"Converted {parse_result.statistics.converted_citations}/{parse_result.statistics.total_citations} citations in {md_file}")
                else:
                    # ドライランの場合
                    processed_files.append({
                        "file": md_file,
                        "status": "dry_run_detected"
                    })
                
            except Exception as e:
                self.logger.error(f"Failed to process {md_file}: {e}")
                processed_files.append({
                    "file": md_file,
                    "error": str(e)
                })
                total_errors += 1
        
        # 結果の構成
        results = {
            "success": True,
            "clippings_dir": clippings_dir,
            "processed_files": processed_files,
            "total_files": len(md_files),
            "statistics": {
                "total_citations": total_citations,
                "converted_citations": total_converted,
                "error_count": total_errors,
                "processing_time": time.time() - start_time
            },
            "processing_time": time.time() - start_time
        }
        
        self.logger.info(f"Directory processing completed: {len(processed_files)} files processed, {total_converted}/{total_citations} citations converted")
        
        return True, results
    
    def validate_inputs(self, input_file: str) -> bool:
        """
        入力ファイルの妥当性チェック
        
        Args:
            input_file: 入力ファイルパス
            
        Returns:
            bool: 妥当性チェック結果
            
        Raises:
            CitationParserError: 入力ファイルに問題がある場合
        """
        try:
            input_path = Path(input_file)
            
            # ファイル存在チェック
            if not input_path.exists():
                raise CitationParserError(f"Input file does not exist: {input_file}")
            
            # ファイル読み取り権限チェック
            if not input_path.is_file():
                raise CitationParserError(f"Input path is not a file: {input_file}")
            
            # ファイルサイズチェック
            max_size_mb = self.config.get('max_file_size_mb', 10)
            file_size_mb = input_path.stat().st_size / (1024 * 1024)
            if file_size_mb > max_size_mb:
                raise CitationParserError(
                    f"File size ({file_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)"
                )
            
            # ファイル拡張子チェック（推奨）
            if input_path.suffix.lower() not in ['.md', '.txt', '.markdown']:
                self.logger.warning(f"Input file extension '{input_path.suffix}' is not typical for text processing")
            
            self.logger.debug(f"Input validation passed for: {input_file}")
            return True
            
        except CitationParserError:
            raise
        except Exception as e:
            raise CitationParserError(f"Validation error: {e}")
    
    def _execute_dry_run(self, input_file: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        ドライラン実行
        
        Args:
            input_file: 入力ファイルパス
            options: 実行オプション
            
        Returns:
            Dict[str, Any]: ドライラン結果
        """
        self.logger.info("Executing dry run - no actual changes will be made")
        
        try:
            # ファイル読み込み（実際の処理）
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 簡易分析
            line_count = len(content.splitlines())
            char_count = len(content)
            
            # 引用パターンの簡易検出
            import re
            patterns = [
                r'\[\d+\]',           # [1]
                r'\[\d+,\s*\d+\]',    # [1, 2]
                r'\[\d+-\d+\]',       # [1-3]
                r'\[\^\d+\]',         # [^1]
                r'\[\d+\]\([^)]+\)'   # [1](URL)
            ]
            
            detected_citations = []
            for pattern in patterns:
                matches = re.findall(pattern, content)
                detected_citations.extend(matches)
            
            dry_run_result = {
                "dry_run": True,
                "dry_run_analysis": {
                    "file_stats": {
                        "line_count": line_count,
                        "character_count": char_count,
                        "file_size_kb": len(content.encode('utf-8')) / 1024
                    },
                    "detected_citations": {
                        "count": len(detected_citations),
                        "samples": detected_citations[:10]  # 最初の10個を表示
                    },
                    "processing_options": {
                        "pattern_type": options.get('pattern_type', 'all'),
                        "output_format": options.get('output_format', 'unified'),
                        "enable_link_extraction": options.get('enable_link_extraction', False),
                        "expand_ranges": options.get('expand_ranges', True)
                    }
                }
            }
            
            # ドライラン結果の表示
            click.echo("\n🔍 Citation Parser Dry Run Analysis")
            click.echo("=" * 50)
            click.echo(f"📄 File: {input_file}")
            click.echo(f"📊 Lines: {line_count}, Characters: {char_count}")
            click.echo(f"📝 Detected citations: {len(detected_citations)}")
            if detected_citations:
                click.echo(f"📋 Sample citations: {', '.join(detected_citations[:5])}")
            
            return dry_run_result
            
        except Exception as e:
            raise CitationParserError(f"Dry run failed: {e}")
    
    def _write_output_file(self, output_file: str, parse_result, options: Dict[str, Any]) -> None:
        """
        出力ファイルを書き込み
        
        Args:
            output_file: 出力ファイルパス
            parse_result: パース結果
            options: 実行オプション
        """
        try:
            output_path = Path(output_file)
            
            # ディレクトリが存在しない場合は作成
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            encoding = options.get('output_encoding', 'utf-8')
            output_format = options.get('output_format', 'unified')
            
            with open(output_file, 'w', encoding=encoding) as f:
                if output_format == 'json':
                    import json
                    output_data = {
                        "converted_text": parse_result.converted_text,
                        "link_table": [
                            {"citation_number": entry.citation_number, "url": entry.url}
                            for entry in parse_result.link_table
                        ],
                        "statistics": {
                            "total_citations": parse_result.statistics.total_citations,
                            "converted_citations": parse_result.statistics.converted_citations,
                            "error_count": len(parse_result.errors)
                        }
                    }
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                elif output_format == 'table':
                    # テーブル形式での出力
                    f.write(parse_result.converted_text)
                    if parse_result.link_table:
                        f.write("\n\n## 引用文献リンク対応表\n\n")
                        f.write("| 引用番号 | URL |\n")
                        f.write("|---------|-----|\n")
                        for entry in parse_result.link_table:
                            f.write(f"| {entry.citation_number} | {entry.url} |\n")
                
                else:  # unified (default)
                    f.write(parse_result.converted_text)
                    if parse_result.link_table:
                        f.write("\n\n<!-- Citation Links -->\n")
                        for entry in parse_result.link_table:
                            f.write(f"<!-- [{entry.citation_number}]: {entry.url} -->\n")
            
            self.logger.info(f"Output written to: {output_file}")
            
        except Exception as e:
            raise CitationParserError(f"Failed to write output file: {e}")
    
    def _display_results(self, parse_result, options: Dict[str, Any]) -> None:
        """
        結果を標準出力に表示
        
        Args:
            parse_result: パース結果
            options: 実行オプション
        """
        output_format = options.get('output_format', 'unified')
        verbose = options.get('verbose', False)
        
        if verbose:
            click.echo("\n📝 Citation Parser Results")
            click.echo("=" * 50)
            click.echo(f"Total citations: {parse_result.statistics.total_citations}")
            click.echo(f"Converted citations: {parse_result.statistics.converted_citations}")
            click.echo(f"Errors: {len(parse_result.errors)}")
            click.echo("\n📄 Converted Text:")
            click.echo("-" * 30)
        
        click.echo(parse_result.converted_text)
        
        if parse_result.link_table and verbose:
            click.echo("\n🔗 Link Table:")
            click.echo("-" * 30)
            for entry in parse_result.link_table:
                click.echo(f"[{entry.citation_number}]: {entry.url}")
        
        if parse_result.errors and verbose:
            click.echo("\n⚠️  Errors:")
            click.echo("-" * 30)
            for error in parse_result.errors:
                click.echo(f"• {error}")
    
    def generate_report(self, result: Dict[str, Any]) -> str:
        """
        実行結果レポートを生成
        
        Args:
            result: 実行結果辞書
            
        Returns:
            str: レポート文字列
        """
        if result.get('dry_run', False):
            # ドライランレポート
            analysis = result.get('dry_run_analysis', {})
            file_stats = analysis.get('file_stats', {})
            citations = analysis.get('detected_citations', {})
            
            report = f"""
Citation Parser Workflow - Dry Run Report
==========================================

📄 Input File: {result.get('input_file', 'Unknown')}

📊 File Statistics:
  • Lines: {file_stats.get('line_count', 0)}
  • Characters: {file_stats.get('character_count', 0)}
  • Size: {file_stats.get('file_size_kb', 0):.1f} KB

📝 Citation Detection:
  • Found: {citations.get('count', 0)} citations
  • Samples: {', '.join(citations.get('samples', [])[:5])}

🔧 Processing Options:
  • Pattern Type: {analysis.get('processing_options', {}).get('pattern_type', 'all')}
  • Output Format: {analysis.get('processing_options', {}).get('output_format', 'unified')}
  • Link Extraction: {analysis.get('processing_options', {}).get('enable_link_extraction', False)}
  • Range Expansion: {analysis.get('processing_options', {}).get('expand_ranges', True)}

⚠️  Note: This was a dry run - no actual processing was performed.
"""
        else:
            # 通常実行レポート
            stats = result.get('statistics', {})
            
            report = f"""
Citation Parser Workflow Report
===============================

📄 Input File: {result.get('input_file', 'Unknown')}
📤 Output File: {result.get('output_file', 'Standard Output')}

📊 Processing Statistics:
  • Total citations found: {stats.get('total_citations', 0)}
  • Successfully converted: {stats.get('converted_citations', 0)}
  • Errors encountered: {stats.get('error_count', 0)}
  • Processing time: {stats.get('processing_time', 0):.2f} seconds

🔧 Options Used:
  • Output Format: {result.get('execution_options', {}).get('output_format', 'unified')}
  • Link Extraction: {result.get('execution_options', {}).get('enable_link_extraction', False)}
  • Range Expansion: {result.get('execution_options', {}).get('expand_ranges', True)}
"""
            
            if stats.get('error_count', 0) > 0:
                report += f"\n⚠️  {stats['error_count']} errors occurred during processing."
            else:
                report += "\n✅ Processing completed successfully!"
        
        return report.strip() 