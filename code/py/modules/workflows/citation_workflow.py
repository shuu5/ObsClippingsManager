"""
引用文献取得ワークフロー v2.1

sync機能と連携し、論文ごとの個別references.bib保存を行う
引用文献取得ワークフローを管理します。
"""

import logging
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

from ..shared.bibtex_parser import BibTeXParser
from ..shared.utils import ProgressTracker
from ..citation_fetcher.fallback_strategy import FallbackStrategy, create_fallback_strategy_from_config
from ..citation_fetcher.reference_formatter import ReferenceFormatter
from ..citation_fetcher.sync_integration import SyncIntegration
from ..citation_fetcher.metadata_enricher import MetadataEnricher


class CitationWorkflow:
    """引用文献取得ワークフロー v2.1"""
    
    def __init__(self, config_manager, logger):
        """
        Args:
            config_manager: 設定管理インスタンス
            logger: 統合ロガーインスタンス
        """
        self.config_manager = config_manager
        self.config = config_manager.get_citation_fetcher_config()
        self.logger = logger.get_logger('CitationWorkflow')
        
        # コンポーネントの初期化
        self.bibtex_parser = BibTeXParser()
        self.fallback_strategy = create_fallback_strategy_from_config(self.config)
        self.reference_formatter = ReferenceFormatter(
            max_authors=self.config.get('max_authors', 3)
        )
        # v2.1の新機能: sync連携
        self.sync_integration = SyncIntegration(config_manager, logger)
        
        # v2.2の新機能: メタデータ補完
        self.metadata_enricher = MetadataEnricher(config_manager)
        
    def execute(self, **options) -> Tuple[bool, Dict[str, Any]]:
        """
        引用文献取得ワークフローを実行 (v2.1: sync連携対応)
        
        Args:
            **options: 実行オプション
                - use_sync_integration: sync機能との連携を使用 (default: True)
                - backup_existing: 既存references.bibのバックアップ作成 (default: False)
                - dry_run: ドライラン実行
                - verbose: 詳細ログ
            
        Returns:
            (成功フラグ, 実行結果詳細)
        """
        self.logger.info("Starting citation fetching workflow v2.1")
        
        results = {
            "stage": "initialization",
            "success": False,
            "statistics": {},
            "sync_integration": {}
        }
        
        try:
            # Stage 1: sync連携による対象論文特定
            use_sync = options.get('use_sync_integration', True)
            
            if use_sync:
                results["stage"] = "sync_integration"
                target_papers = self._get_target_papers_from_sync()
                results["sync_integration"]["target_papers_count"] = len(target_papers)
                
                if not target_papers:
                    results["error"] = "No synchronized papers with valid DOIs found"
                    return False, results
                    
                # sync統計情報を追加
                sync_stats = self.sync_integration.get_sync_statistics()
                results["sync_integration"].update(sync_stats)
                
            else:
                # 従来方式: 全BibTeXエントリを対象
                results["stage"] = "bibtex_parsing"
                target_papers = self._get_target_papers_legacy()
                
            self.logger.info(f"Target papers identified: {len(target_papers)}")
            
            # Stage 2: バックアップ処理（オプション）
            if options.get('backup_existing', False) and use_sync:
                results["stage"] = "backup_preparation"
                backup_results = self._prepare_backups(target_papers)
                results["backup_results"] = backup_results
            
            # Stage 3: 引用文献取得
            results["stage"] = "citation_fetching"
            citation_results = self._fetch_citations_for_papers(target_papers, options)
            results.update(citation_results)
            
            # Stage 4: 個別保存
            results["stage"] = "individual_saving"
            if use_sync:
                save_results = self._save_individual_references(target_papers, citation_results, options)
            else:
                save_results = self._save_results_legacy(citation_results, options)
            results.update(save_results)
            
            # Stage 5: 統計情報の生成
            results["stage"] = "statistics_generation"
            self._generate_comprehensive_statistics(results, target_papers)
            
            results["success"] = True
            self.logger.info("Citation fetching workflow v2.1 completed successfully")
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
            "enriched_successes": 0,
            "fetched_references": {},
            "api_sources": {},
            "errors": []
        }
        
        # ドライランモードのチェック
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        enable_enrichment = options.get('enable_enrichment', False)
        
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
                
                # 引用文献の取得が成功した場合
                if references:
                    # メタデータ補完機能が有効な場合は各引用文献の情報を補完
                    if enable_enrichment:
                        field_type = options.get('enrichment_field_type', 'general')
                        enriched_references = self._enrich_references_metadata(references, field_type)
                        if enriched_references:
                            references = enriched_references
                            source = f"{source} (enriched)"
                            results["enriched_successes"] += 1
                            self.logger.info(f"Enriched metadata for {len(references)} references from {doi}")
                    
                    results["fetched_references"][doi] = references
                    results["api_sources"][doi] = source
                    results["successful_fetches"] += 1
                    
                    # ソース別の統計
                    if source == "CrossRef" or source.startswith("CrossRef"):
                        results["crossref_successes"] += 1
                    elif source == "OpenCitations" or source.startswith("OpenCitations"):
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
        
        # 統計メッセージにメタデータ補完情報を追加
        log_msg = (
            f"Citation fetching completed: "
            f"{results['successful_fetches']}/{results['total_dois']} DOIs processed, "
            f"{total_references} total references"
        )
        if results.get('enriched_successes', 0) > 0:
            log_msg += f" (including {results['enriched_successes']} DOIs with enriched references)"
        
        self.logger.info(log_msg)
        
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
    
    # === v2.1 新機能: sync連携メソッド ===
    
    def _get_target_papers_from_sync(self) -> List[Dict[str, str]]:
        """
        sync連携により対象論文リストを取得
        
        Returns:
            対象論文のリスト
        """
        success, target_papers = self.sync_integration.get_target_papers_for_citation_fetching()
        
        if not success:
            raise ValueError("Failed to get target papers from sync integration")
        
        self.logger.info(f"Sync integration identified {len(target_papers)} target papers")
        return target_papers
    
    def _get_target_papers_legacy(self) -> List[Dict[str, str]]:
        """
        従来方式により対象論文リストを取得（sync非使用）
        
        Returns:
            対象論文のリスト
        """
        bib_entries = self._parse_bibtex_file()
        dois = self._extract_dois(bib_entries)
        
        target_papers = []
        for doi in dois:
            # citation_keyを逆引きで特定（簡易版）
            citation_key = None
            for key, entry in bib_entries.items():
                if entry.get('doi', '').strip().replace('\n', '').replace('\r', '') == doi:
                    citation_key = key
                    break
            
            target_papers.append({
                'citation_key': citation_key or f"unknown_{doi}",
                'doi': doi,
                'has_valid_doi': True,
                'directory_path': None,
                'references_file_path': None
            })
        
        return target_papers
    
    def _prepare_backups(self, target_papers: List[Dict[str, str]]) -> Dict[str, bool]:
        """
        既存references.bibファイルのバックアップを準備
        
        Args:
            target_papers: 対象論文リスト
            
        Returns:
            バックアップ結果
        """
        self.logger.info("Preparing backups for existing references.bib files")
        return self.sync_integration.prepare_backup_existing_references(target_papers)
    
    def _fetch_citations_for_papers(self, target_papers: List[Dict[str, str]], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        論文リストに対して引用文献を取得
        
        Args:
            target_papers: 対象論文リスト
            options: 実行オプション
            
        Returns:
            取得結果の詳細
        """
        # DOIのみを抽出して従来の_fetch_citationsメソッドを使用
        dois = [paper['doi'] for paper in target_papers if paper.get('doi')]
        
        # 元のメソッドを呼び出し
        citation_results = self._fetch_citations(dois, options)
        
        # 結果にcitation_key情報を追加
        citation_key_mapping = {paper['doi']: paper['citation_key'] for paper in target_papers}
        citation_results['citation_key_mapping'] = citation_key_mapping
        
        return citation_results
    
    def _save_individual_references(self, target_papers: List[Dict[str, str]], 
                                   citation_results: Dict[str, Any], 
                                   options: Dict[str, Any]) -> Dict[str, Any]:
        """
        各論文のディレクトリにreferences.bibを個別保存
        
        Args:
            target_papers: 対象論文リスト
            citation_results: 引用文献取得結果
            options: 実行オプション
            
        Returns:
            保存結果の詳細
        """
        self.logger.info(f"Saving individual references.bib files for {len(target_papers)} papers")
        
        save_results = {
            "saved_files": [],
            "save_errors": [],
            "individual_saves": {}
        }
        
        # ドライランモードのチェック
        dry_run = options.get('dry_run', self.config.get('dry_run', False))
        
        # 論文ごとの処理
        for paper in target_papers:
            citation_key = paper['citation_key']
            doi = paper['doi']
            references_file_path = paper.get('references_file_path')
            
            try:
                # 引用文献データを取得
                references = citation_results.get("fetched_references", {}).get(doi)
                source = citation_results.get("api_sources", {}).get(doi, "unknown")
                
                if not references:
                    self.logger.warning(f"No references found for {citation_key} ({doi})")
                    save_results["individual_saves"][citation_key] = {
                        "status": "no_references",
                        "references_count": 0
                    }
                    continue
                
                if not references_file_path:
                    self.logger.error(f"No valid file path for {citation_key}")
                    save_results["save_errors"].append(f"No valid file path for {citation_key}")
                    continue
                
                # 既存ファイルチェック（force_overwriteが無効の場合）
                references_file = Path(references_file_path)
                force_overwrite = options.get('force_overwrite', False)
                
                if references_file.exists() and not force_overwrite:
                    self.logger.info(f"Skipping {citation_key}: references.bib already exists (use --force-overwrite to override)")
                    save_results["individual_saves"][citation_key] = {
                        "status": "skipped",
                        "references_count": 0,
                        "file_path": references_file_path,
                        "reason": "File already exists"
                    }
                    continue
                
                if dry_run:
                    action = "overwrite" if references_file.exists() else "create"
                    self.logger.info(f"[DRY RUN] Would {action} {len(references)} references to {references_file_path}")
                    save_results["saved_files"].append(references_file_path)
                    save_results["individual_saves"][citation_key] = {
                        "status": "dry_run",
                        "references_count": len(references),
                        "file_path": references_file_path
                    }
                    continue
                
                # BibTeX形式に変換（個別ヘッダー付き）
                bibtex_content = self._format_individual_references(
                    references, source, citation_key, doi
                )
                
                # ファイルに保存
                references_file.parent.mkdir(parents=True, exist_ok=True)
                
                with open(references_file, 'w', encoding='utf-8') as f:
                    f.write(bibtex_content)
                
                save_results["saved_files"].append(str(references_file))
                save_results["individual_saves"][citation_key] = {
                    "status": "success",
                    "references_count": len(references),
                    "file_path": str(references_file),
                    "source": source
                }
                
                self.logger.info(
                    f"Saved {len(references)} references for {citation_key} to {references_file}"
                )
                
            except Exception as e:
                error_msg = f"Failed to save references for {citation_key}: {e}"
                save_results["save_errors"].append(error_msg)
                save_results["individual_saves"][citation_key] = {
                    "status": "error",
                    "error": str(e)
                }
                self.logger.error(error_msg)
        
        # 保存統計
        successful_saves = sum(1 for save in save_results["individual_saves"].values() 
                              if save["status"] in ["success", "dry_run"])
        skipped_saves = sum(1 for save in save_results["individual_saves"].values() 
                           if save["status"] == "skipped")
        total_references_saved = sum(save.get("references_count", 0) 
                                   for save in save_results["individual_saves"].values())
        
        status_msg = f"Individual saving completed: {successful_saves}/{len(target_papers)} papers"
        if skipped_saves > 0:
            status_msg += f", {skipped_saves} skipped"
        status_msg += f", {total_references_saved} total references"
        
        self.logger.info(status_msg)
        
        save_results["successful_individual_saves"] = successful_saves
        save_results["skipped_individual_saves"] = skipped_saves
        save_results["total_references_saved"] = total_references_saved
        
        return save_results
    
    def _format_individual_references(self, references: List[Dict[str, Any]], 
                                     source: str, citation_key: str, doi: str) -> str:
        """
        個別論文用のBibTeX形式でフォーマット
        
        Args:
            references: 引用文献リスト
            source: データソース
            citation_key: 論文のcitation key
            doi: 論文のDOI
            
        Returns:
            BibTeX形式の文字列
        """
        # ヘッダーコメントを生成
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"""% References for citation_key: {citation_key}
% DOI: {doi}
% Generated on: {current_time}
% Total references: {len(references)}
% Data source: {source}

"""
        
        # BibTeX変換
        bibtex_content = self.reference_formatter.format_to_bibtex(references, source, doi)
        
        return header + bibtex_content
    
    def _save_results_legacy(self, citation_results: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """
        従来方式の結果保存（sync非使用時）
        
        Args:
            citation_results: 引用文献取得結果
            options: 実行オプション
            
        Returns:
            保存結果の詳細
        """
        return self._save_results(citation_results, options)
    
    def _generate_comprehensive_statistics(self, results: Dict[str, Any], target_papers: List[Dict[str, str]]) -> None:
        """
        包括的な統計情報を生成
        
        Args:
            results: 実行結果辞書（更新される）
            target_papers: 対象論文リスト
        """
        # 基本統計情報
        basic_stats = {
            "target_papers_count": len(target_papers),
            "papers_with_valid_dois": len([p for p in target_papers if p.get('has_valid_doi')]),
            "execution_timestamp": datetime.now().isoformat()
        }
        
        # API統計情報
        api_stats = {
            "crossref_success_rate": 0,
            "opencitations_success_rate": 0,
            "overall_success_rate": 0
        }
        
        total_fetches = results.get("total_dois", 0)
        if total_fetches > 0:
            crossref_successes = results.get("crossref_successes", 0)
            opencitations_successes = results.get("opencitations_successes", 0)
            
            api_stats.update({
                "crossref_success_rate": round(crossref_successes / total_fetches * 100, 1),
                "opencitations_success_rate": round(opencitations_successes / total_fetches * 100, 1),
                "overall_success_rate": round(results.get("successful_fetches", 0) / total_fetches * 100, 1)
            })
        
        # 保存統計情報
        save_stats = {
            "individual_files_saved": results.get("successful_individual_saves", 0),
            "total_references_saved": results.get("total_references_saved", 0),
            "average_references_per_paper": 0
        }
        
        if save_stats["individual_files_saved"] > 0:
            save_stats["average_references_per_paper"] = round(
                save_stats["total_references_saved"] / save_stats["individual_files_saved"], 1
            )
        
        # 統計情報を結果に追加
        results["statistics"].update({
            **basic_stats,
            **api_stats,
            **save_stats
        })
    
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

    def _enrich_references_metadata(self, references: List[Dict[str, Any]], field_type: str = 'general') -> List[Dict[str, Any]]:
        """
        引用文献のメタデータを補完
        
        Args:
            references: 引用文献のリスト
            field_type: 分野タイプ
            
        Returns:
            補完された引用文献のリスト
        """
        enriched_references = []
        incomplete_count = 0
        skipped_count = 0
        
        # API優先順位を取得
        api_priority = self.metadata_enricher._get_api_priority(field_type)
        
        for reference in references:
            try:
                # 引用文献の情報が既に完全かチェック
                if self._is_reference_complete(reference):
                    # 完全な情報がある場合はenrichmentをスキップ
                    enriched_references.append(reference)
                    skipped_count += 1
                    self.logger.debug(f"Skipping enrichment for complete reference: {reference.get('title', 'Unknown')[:50]}...")
                    continue
                
                # 引用文献にDOIがある場合のみ補完を試行
                ref_doi = reference.get('doi')
                if not ref_doi:
                    # DOIがない場合は元の情報をそのまま使用
                    enriched_references.append(reference)
                    continue
                
                incomplete_count += 1
                enriched_ref = reference.copy()
                enrichment_successful = False
                
                # API優先順位に従って順次試行
                for api_name in api_priority:
                    if api_name not in self.metadata_enricher.clients:
                        continue
                    
                    try:
                        self.logger.debug(f"Trying {api_name} for reference {ref_doi}")
                        
                        client = self.metadata_enricher.clients[api_name]
                        raw_metadata = client.get_metadata_by_doi(ref_doi)
                        
                        if raw_metadata:
                            # メタデータを正規化
                            normalized_metadata = self.metadata_enricher._normalize_metadata(raw_metadata, api_name)
                            
                            if normalized_metadata:
                                # 既存の参照情報を補完されたメタデータで更新
                                enriched_ref.update(normalized_metadata)
                                enriched_ref['enrichment_source'] = api_name
                                enriched_ref['enrichment_quality'] = self.metadata_enricher._calculate_quality_score(normalized_metadata)
                                
                                # 補完後の情報が完全かチェック
                                if self._is_reference_complete(enriched_ref):
                                    enrichment_successful = True
                                    self.logger.debug(f"Reference {ref_doi} successfully enriched by {api_name}")
                                    break  # 十分な情報が得られたので他のAPIは試行しない
                                
                    except Exception as e:
                        self.logger.debug(f"Failed to enrich reference {ref_doi} with {api_name}: {e}")
                        continue
                
                # 補完結果を追加
                enriched_references.append(enriched_ref)
                
                if enrichment_successful:
                    self.logger.debug(f"Successfully enriched reference {ref_doi}")
                else:
                    self.logger.debug(f"Could not fully enrich reference {ref_doi}, using partially completed data")
                    
            except Exception as e:
                # エラーが発生した場合は元の情報をそのまま使用
                self.logger.warning(f"Error enriching reference metadata: {e}")
                enriched_references.append(reference)
        
        success_count = sum(1 for ref in enriched_references if ref.get('enrichment_source'))
        self.logger.info(f"Metadata enrichment completed: {success_count}/{incomplete_count} incomplete references enriched, {skipped_count} complete references skipped")
        
        return enriched_references
    
    def _is_reference_complete(self, reference: Dict[str, Any]) -> bool:
        """
        引用文献の情報が完全かチェック
        
        Args:
            reference: 引用文献の辞書
            
        Returns:
            完全な情報があるかどうか
        """
        required_fields = ['title', 'author', 'year']
        optional_fields = ['journal', 'volume', 'pages']
        
        # 必須フィールドがすべて存在し、空でないかチェック
        for field in required_fields:
            value = reference.get(field)
            if not value or str(value).strip() == '':
                return False
        
        # オプションフィールドのうち少なくとも1つが存在するかチェック
        has_optional = any(
            reference.get(field) and str(reference.get(field)).strip() != ''
            for field in optional_fields
        )
        
        # 必須フィールドがすべて揃っていて、オプションフィールドが1つ以上ある場合は完全とみなす
        return has_optional


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