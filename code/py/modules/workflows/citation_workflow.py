"""
引用文献取得ワークフロー

BibTeX解析からDOI抽出、引用文献取得までの一連のワークフローを管理します。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

from ..shared.bibtex_parser import BibTeXParser
from ..shared.utils import ProgressTracker
from ..citation_fetcher.fallback_strategy import FallbackStrategy, create_fallback_strategy_from_config
from ..citation_fetcher.reference_formatter import ReferenceFormatter


class CitationWorkflow:
    """引用文献取得ワークフロー"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config = config_manager.get_citation_fetcher_config()
        self.logger = logger.get_logger('CitationWorkflow')
        
        # コンポーネントの初期化
        self.bibtex_parser = BibTeXParser()
        self.fallback_strategy = create_fallback_strategy_from_config(self.config)
        self.reference_formatter = ReferenceFormatter(
            max_authors=self.config.get('max_authors', 3)
        )
        
    def execute(self, **options) -> Tuple[bool, Dict[str, Any]]:
        """
        引用文献取得ワークフローを実行
        
        Args:
            **options: 実行オプション
            
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        self.logger.info("Starting citation fetching workflow")
        
        results = {
            "stage": "initialization",
            "success": False,
            "statistics": {}
        }
        
        try:
            # Stage 1: BibTeX解析
            results["stage"] = "bibtex_parsing"
            bib_entries = self._parse_bibtex_file()
            results["bib_entries_count"] = len(bib_entries)
            self.logger.info(f"Parsed {len(bib_entries)} BibTeX entries")
            
            if not bib_entries:
                results["error"] = "No BibTeX entries found"
                return False, results
            
            # Stage 2: DOI抽出
            results["stage"] = "doi_extraction"
            dois = self._extract_dois(bib_entries)
            results["dois_count"] = len(dois)
            self.logger.info(f"Extracted {len(dois)} DOIs")
            
            if not dois:
                results["error"] = "No DOIs found in BibTeX entries"
                return False, results
            
            # Stage 3: 引用文献取得
            results["stage"] = "citation_fetching"
            citation_results = self._fetch_citations(dois, options)
            results.update(citation_results)
            
            # Stage 4: 結果保存
            results["stage"] = "saving_results"
            save_results = self._save_results(citation_results, options)
            results.update(save_results)
            
            results["success"] = True
            self.logger.info("Citation fetching workflow completed successfully")
            return True, results
            
        except Exception as e:
            self.logger.error(f"Citation fetching workflow failed: {e}")
            results["error"] = str(e)
            return False, results
    
    def _parse_bibtex_file(self) -> Dict[str, Dict[str, str]]:
        """
        BibTeXファイル解析の実行
        
        Returns:
            解析されたBibTeXエントリ
        """
        bibtex_file = self.config.get('bibtex_file')
        if not bibtex_file:
            raise ValueError("BibTeX file path not configured")
        
        if not Path(bibtex_file).exists():
            raise FileNotFoundError(f"BibTeX file not found: {bibtex_file}")
        
        self.logger.info(f"Parsing BibTeX file: {bibtex_file}")
        return self.bibtex_parser.parse_file(bibtex_file)
    
    def _extract_dois(self, bib_entries: Dict[str, Dict[str, str]]) -> List[str]:
        """
        DOI抽出の実行
        
        Args:
            bib_entries: BibTeXエントリ
            
        Returns:
            DOIのリスト
        """
        self.logger.info("Extracting DOIs from BibTeX entries")
        return self.bibtex_parser.extract_dois(bib_entries)
    
    def _fetch_citations(self, dois: List[str], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        引用文献取得の実行
        
        Args:
            dois: DOIのリスト
            options: 実行オプション
            
        Returns:
            取得結果の詳細
        """
        self.logger.info(f"Fetching citations for {len(dois)} DOIs")
        
        # 進捗追跡の初期化
        progress = ProgressTracker(len(dois), "Fetching citations")
        
        results = {
            "total_dois": len(dois),
            "successful_fetches": 0,
            "failed_fetches": 0,
            "crossref_successes": 0,
            "opencitations_successes": 0,
            "fetched_references": {},
            "api_sources": {},
            "errors": []
        }
        
        # ドライランモードのチェック
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        
        for i, doi in enumerate(dois):
            try:
                progress.update(i + 1, f"Processing {doi}")
                
                if dry_run:
                    # ドライランモードでは実際のAPI呼び出しは行わない
                    self.logger.info(f"[DRY RUN] Would fetch references for {doi}")
                    results["successful_fetches"] += 1
                    results["crossref_successes"] += 1  # 仮の成功
                    continue
                
                # フォールバック戦略で引用文献を取得
                references, source = self.fallback_strategy.get_references_with_fallback(doi)
                
                if references:
                    results["fetched_references"][doi] = references
                    results["api_sources"][doi] = source
                    results["successful_fetches"] += 1
                    
                    # ソース別の統計
                    if source == "CrossRef":
                        results["crossref_successes"] += 1
                    elif source == "OpenCitations":
                        results["opencitations_successes"] += 1
                        
                    self.logger.info(
                        f"Successfully fetched {len(references)} references "
                        f"for {doi} from {source}"
                    )
                else:
                    results["failed_fetches"] += 1
                    error_msg = f"No references found for {doi}"
                    results["errors"].append(error_msg)
                    self.logger.warning(error_msg)
                    
            except Exception as e:
                results["failed_fetches"] += 1
                error_msg = f"Failed to fetch references for {doi}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
                continue
        
        progress.finish(results["successful_fetches"], results["failed_fetches"])
        
        # 統計情報の計算
        total_references = sum(len(refs) for refs in results["fetched_references"].values())
        results["total_references"] = total_references
        
        self.logger.info(
            f"Citation fetching completed: "
            f"{results['successful_fetches']}/{results['total_dois']} DOIs processed, "
            f"{total_references} total references"
        )
        
        return results
    
    def _save_results(self, citation_results: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        結果の保存
        
        Args:
            citation_results: 引用文献取得結果
            options: 実行オプション
            
        Returns:
            保存結果の詳細
        """
        output_dir = Path(self.config.get('output_dir', './output/'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        save_results = {
            "saved_files": [],
            "save_errors": []
        }
        
        # ドライランモードのチェック
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        
        for doi, references in citation_results.get("fetched_references", {}).items():
            try:
                source = citation_results["api_sources"].get(doi, "unknown")
                
                # ファイル名を生成
                safe_doi = doi.replace('/', '_').replace(':', '_')
                filename = f"{source.lower()}_references_{safe_doi}.bib"
                output_file = output_dir / filename
                
                if dry_run:
                    self.logger.info(f"[DRY RUN] Would save {len(references)} references to {output_file}")
                    save_results["saved_files"].append(str(output_file))
                    continue
                
                # BibTeX形式に変換
                bibtex_content = self.reference_formatter.format_to_bibtex(
                    references, source, doi
                )
                
                # ファイルに保存
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(bibtex_content)
                
                save_results["saved_files"].append(str(output_file))
                self.logger.info(f"Saved {len(references)} references to {output_file}")
                
            except Exception as e:
                error_msg = f"Failed to save references for {doi}: {e}"
                save_results["save_errors"].append(error_msg)
                self.logger.error(error_msg)
        
        return save_results
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """
        ワークフローの統計情報を取得
        
        Returns:
            統計情報
        """
        return {
            "workflow_type": "citation_fetching",
            "configured_apis": ["CrossRef", "OpenCitations"],
            "max_retries": self.config.get('max_retries', 3),
            "request_delay": self.config.get('request_delay', 1.0),
            "output_format": self.config.get('output_format', 'bibtex')
        }


# ヘルパー関数
def validate_citation_workflow_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Citation Workflowの設定を検証
    
    Args:
        config: 設定辞書
        
    Returns:
        (妥当性, エラーメッセージリスト)
    """
    errors = []
    
    # 必須設定の確認
    required_configs = ['bibtex_file', 'output_dir']
    for key in required_configs:
        if key not in config:
            errors.append(f"Missing required config: {key}")
    
    # BibTeXファイルの存在確認
    if 'bibtex_file' in config:
        bibtex_file = config['bibtex_file']
        if not Path(bibtex_file).exists():
            errors.append(f"BibTeX file not found: {bibtex_file}")
    
    # 数値設定の検証
    numeric_configs = {
        'max_retries': (1, 10),
        'request_delay': (0.1, 10.0),
        'timeout': (5, 120)
    }
    
    for key, (min_val, max_val) in numeric_configs.items():
        if key in config:
            try:
                value = float(config[key])
                if not (min_val <= value <= max_val):
                    errors.append(f"{key} must be between {min_val} and {max_val}")
            except (TypeError, ValueError):
                errors.append(f"{key} must be a number")
    
    return len(errors) == 0, errors


def create_citation_workflow_summary(results: Dict[str, Any]) -> str:
    """
    Citation Workflowの結果サマリーを作成
    
    Args:
        results: ワークフロー実行結果
        
    Returns:
        サマリー文字列
    """
    lines = ["Citation Fetching Workflow Summary", "=" * 40]
    
    if results.get("success"):
        lines.append("Status: COMPLETED")
        
        # 基本統計
        total_dois = results.get("dois_count", 0)
        successful = results.get("successful_fetches", 0)
        failed = results.get("failed_fetches", 0)
        total_refs = results.get("total_references", 0)
        
        lines.extend([
            f"DOIs processed: {successful}/{total_dois}",
            f"Total references found: {total_refs}",
            f"Success rate: {(successful/total_dois*100):.1f}%" if total_dois > 0 else "Success rate: N/A"
        ])
        
        # API別統計
        crossref_success = results.get("crossref_successes", 0)
        opencitations_success = results.get("opencitations_successes", 0)
        
        if crossref_success > 0 or opencitations_success > 0:
            lines.append("\nAPI Usage:")
            lines.append(f"  CrossRef: {crossref_success} successes")
            lines.append(f"  OpenCitations: {opencitations_success} successes")
        
        # 保存ファイル
        saved_files = results.get("saved_files", [])
        if saved_files:
            lines.append(f"\nSaved files: {len(saved_files)}")
            for file_path in saved_files[:5]:  # 最初の5ファイルのみ表示
                lines.append(f"  - {Path(file_path).name}")
            if len(saved_files) > 5:
                lines.append(f"  ... and {len(saved_files) - 5} more files")
                
    else:
        lines.append("Status: FAILED")
        error = results.get("error", "Unknown error")
        lines.append(f"Error: {error}")
    
    # エラー詳細
    errors = results.get("errors", [])
    if errors:
        lines.append(f"\nErrors encountered: {len(errors)}")
        for error in errors[:3]:  # 最初の3エラーのみ表示
            lines.append(f"  - {error}")
        if len(errors) > 3:
            lines.append(f"  ... and {len(errors) - 3} more errors")
    
    return "\n".join(lines) 