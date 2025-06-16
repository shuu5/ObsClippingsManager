"""
Tagger Workflow

論文自動タグ生成ワークフロークラス
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .claude_api_client import ClaudeAPIClient
from ..shared_modules.config_manager import ConfigManager
from ..shared_modules.integrated_logger import IntegratedLogger
from ..shared_modules.exceptions import APIError, ProcessingError
from ..status_management_yaml.status_manager import StatusManager
from ..status_management_yaml.yaml_header_processor import YAMLHeaderProcessor


class TaggerWorkflow:
    """
    論文自動タグ生成ワークフロー
    
    Claude 3.5 Haikuを使用して論文内容から適切なタグを自動生成します。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        TaggerWorkflow初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.integrated_logger = logger
        self.logger = logger.get_logger('TaggerWorkflow')
        
        # 設定値取得
        self.enabled = config_manager.get_ai_setting('tagger', 'enabled', default=True)
        self.batch_size = config_manager.get_ai_setting('tagger', 'batch_size', default=8)
        self.tag_count_range = config_manager.get_ai_setting('tagger', 'tag_count_range', default=[10, 20])
        
        # Claude APIクライアント（遅延初期化）
        self._claude_client = None
        
        self.logger.info(f"TaggerWorkflow initialized (enabled: {self.enabled}, batch_size: {self.batch_size})")
    
    @property
    def claude_client(self) -> ClaudeAPIClient:
        """Claude APIクライアントの遅延初期化"""
        if self._claude_client is None:
            self._claude_client = ClaudeAPIClient(self.config_manager, self.integrated_logger)
        return self._claude_client
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        論文の一括タグ生成処理
        
        Args:
            input_dir: 処理対象ディレクトリ
            target_items: 処理対象論文リスト（Noneの場合は全て）
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        if not self.enabled:
            self.logger.info("Tagger workflow is disabled")
            return {'status': 'disabled', 'processed': 0, 'skipped': 0, 'failed': 0}
        
        self.logger.info(f"Starting tagger processing for directory: {input_dir}")
        
        # 処理対象論文の取得
        status_manager = StatusManager(self.config_manager, self.integrated_logger)
        papers_needing_processing = status_manager.get_papers_needing_processing(
            input_dir, 'tagger', target_items
        )
        
        processed_count = 0
        failed_count = 0
        
        for paper_path in papers_needing_processing:
            try:
                self.logger.debug(f"Processing tags for: {paper_path}")
                
                # タグ生成
                tags = self.generate_tags_single(paper_path)
                
                if tags:
                    # 品質評価
                    paper_content = self.extract_paper_content(paper_path)
                    quality_score = self.evaluate_tag_quality(tags, paper_content)
                    
                    # フィードバックレポート生成
                    feedback = self.generate_feedback_report(tags, paper_content, quality_score)
                    
                    # 品質スコアをログ出力
                    self.logger.info(f"Generated {len(tags)} tags for {Path(paper_path).name} "
                                   f"(quality: {quality_score:.3f})")
                    
                    # 改善提案があればログ出力
                    if feedback.get('suggestions'):
                        self.logger.debug(f"Improvement suggestions: {'; '.join(feedback['suggestions'][:2])}")
                    
                    # YAMLヘッダー更新（品質情報も含む）
                    self.update_yaml_with_tags_and_quality(paper_path, tags, feedback)
                    
                    # citation_keyを抽出してから状態更新
                    citation_key = Path(paper_path).parent.name
                    status_manager.update_status(input_dir, citation_key, 'tagger', 'completed')
                    processed_count += 1
                else:
                    # タグ生成失敗
                    citation_key = Path(paper_path).parent.name
                    status_manager.update_status(input_dir, citation_key, 'tagger', 'failed')
                    failed_count += 1
                    self.logger.warning(f"No tags generated for {Path(paper_path).name}")
                    
            except Exception as e:
                self.logger.error(f"Failed to generate tags for {paper_path}: {e}")
                citation_key = Path(paper_path).parent.name
                status_manager.update_status(input_dir, citation_key, 'tagger', 'failed')
                failed_count += 1
        
        result = {
            'status': 'completed',
            'processed': processed_count,
            'skipped': len(papers_needing_processing) - processed_count - failed_count,
            'failed': failed_count,
            'total_papers': len(papers_needing_processing)
        }
        
        self.logger.info(f"Tagger processing completed: {result}")
        return result
    
    def generate_tags_single(self, paper_path: str) -> List[str]:
        """
        単一論文のタグ生成
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            List[str]: 生成されたタグリスト
        """
        try:
            # 論文コンテンツ抽出
            paper_content = self.extract_paper_content(paper_path)
            
            # プロンプト構築
            prompt = self._build_tagging_prompt(paper_content)
            
            # Claude API呼び出し
            response = self.claude_client.send_request(prompt)
            
            # レスポンス解析
            tags = self._parse_tags_response(response)
            
            return tags
            
        except Exception as e:
            self.logger.error(f"Failed to generate tags for {paper_path}: {e}")
            raise ProcessingError(
                message=f"Tag generation failed for {paper_path}",
                error_code="TAG_GENERATION_FAILED",
                context={"paper_path": paper_path}
            ) from e
    
    def extract_paper_content(self, paper_path: str) -> str:
        """
        paper_structure を使用してintroduction, results, discussionセクションを抽出
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            str: 抽出されたセクションコンテンツ（全文）
        """
        try:
            # YAMLヘッダー解析
            processor = YAMLHeaderProcessor(self.config_manager, self.integrated_logger)
            yaml_data, markdown_content = processor.parse_yaml_header(Path(paper_path))
            
            # paper_structure 取得
            paper_structure = yaml_data.get('paper_structure', {})
            sections = paper_structure.get('sections', [])
            
            if not sections:
                self.logger.warning(f"No paper_structure found in {paper_path}, falling back to full content")
                return markdown_content
            
            # 対象セクション（introduction, results, discussion）の抽出
            target_section_types = ['introduction', 'results', 'discussion']
            extracted_sections = []
            
            markdown_lines = markdown_content.split('\n')
            
            for section in sections:
                section_type = section.get('section_type')
                if section_type in target_section_types:
                    start_line = section.get('start_line', 0)
                    end_line = section.get('end_line', len(markdown_lines))
                    
                    # セクション内容抽出（行範囲ベース、1-indexedから0-indexedに変換）
                    section_content = '\n'.join(markdown_lines[start_line-1:end_line])
                    section_title = section.get('title', section_type.title())
                    extracted_sections.append(f"## {section_title}\n{section_content}")
                    
                    self.logger.debug(f"Extracted {section_type} section: lines {start_line}-{end_line}")
            
            if not extracted_sections:
                self.logger.warning(f"No target sections found in {paper_path}, falling back to full content")
                return markdown_content
            
            result = '\n\n'.join(extracted_sections)
            self.logger.info(f"Extracted {len(extracted_sections)} sections for tagging from {Path(paper_path).name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to extract content from {paper_path}: {e}")
            raise ProcessingError(
                message=f"Content extraction failed for {paper_path}",
                error_code="CONTENT_EXTRACTION_FAILED",
                context={"paper_path": paper_path}
            ) from e
    
    def _build_tagging_prompt(self, paper_content: str) -> str:
        """
        タグ生成プロンプトの構築
        
        Args:
            paper_content: 論文コンテンツ（主要セクション抽出済み）
            
        Returns:
            str: 構築されたプロンプト
        """
        min_tags, max_tags = self.tag_count_range
        
        prompt = f"""以下の学術論文の主要セクション（Introduction, Results, Discussion）から、{min_tags}-{max_tags}個のタグを生成してください。

ルール:
- 英語でのタグ生成
- スネークケース形式（例: machine_learning, cancer_research）
- 遺伝子名はgene symbol（例: KRT13, EGFR, TP53）
- 論文理解に重要なキーワードを抽出
- 研究分野、技術、疾患、遺伝子、手法などを含む
- 専門性と一般性のバランスを考慮

論文の主要セクション:
{paper_content}

生成されたタグ（JSON配列形式で返答）:"""

        return prompt
    
    def _parse_tags_response(self, response: str) -> List[str]:
        """
        Claude APIレスポンスからタグを解析
        
        Args:
            response: Claude APIレスポンス
            
        Returns:
            List[str]: 解析されたタグリスト
        """
        try:
            # JSONとして解析を試行
            tags = json.loads(response.strip())
            
            if isinstance(tags, list):
                # タグのバリデーション
                validated_tags = []
                for tag in tags:
                    if isinstance(tag, str) and self._validate_tag_format(tag):
                        validated_tags.append(tag.lower())
                
                return validated_tags
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse tags response as JSON: {e}")
            self.logger.debug(f"Response content: '{response.strip()[:200]}...'")
            
            # フォールバック: 正規表現でタグを抽出
            try:
                tag_pattern = r'["\']([a-zA-Z0-9_]+)["\']'
                matches = re.findall(tag_pattern, response)
                if matches:
                    validated_tags = [tag.lower() for tag in matches if self._validate_tag_format(tag)]
                    return validated_tags[:self.tag_count_range[1]]  # 最大数制限
            except Exception as fallback_error:
                self.logger.error(f"Fallback tag parsing also failed: {fallback_error}")
        
        self.logger.error(f"Could not parse any tags from response: {response[:200]}...")
        return []
    
    def _validate_tag_format(self, tag: str) -> bool:
        """
        タグ形式のバリデーション
        
        Args:
            tag: 検証するタグ
            
        Returns:
            bool: 有効な形式かどうか
        """
        # スネークケース形式の検証
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, tag)) and len(tag) >= 2
    
    def update_yaml_with_tags(self, paper_path: str, tags: List[str]):
        """
        YAMLヘッダーにタグを更新
        
        Args:
            paper_path: 論文ファイルパス
            tags: 更新するタグリスト
        """
        try:
            processor = YAMLHeaderProcessor(self.config_manager, self.integrated_logger)
            
            # 現在のYAMLヘッダー読み込み
            current_yaml, markdown_content = processor.parse_yaml_header(Path(paper_path))
            
            # タグセクション更新
            current_yaml['tags'] = tags
            
            # processing_status更新
            if 'processing_status' not in current_yaml:
                current_yaml['processing_status'] = {}
            current_yaml['processing_status']['tagger'] = 'completed'
            
            # last_updated更新
            current_yaml['last_updated'] = datetime.now().isoformat()
            
            # YAMLヘッダー書き込み
            processor.write_yaml_header(Path(paper_path), current_yaml, markdown_content)
            
            self.logger.debug(f"Updated YAML header with {len(tags)} tags for {paper_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header for {paper_path}: {e}")
            raise ProcessingError(
                message=f"YAML header update failed for {paper_path}",
                error_code="YAML_UPDATE_FAILED",
                context={"paper_path": paper_path, "tags": tags}
            ) from e
    
    def update_yaml_with_tags_and_quality(self, paper_path: str, tags: List[str], feedback: Dict[str, Any]):
        """
        YAMLヘッダーにタグと品質情報を更新
        
        Args:
            paper_path: 論文ファイルパス
            tags: 更新するタグリスト
            feedback: 品質フィードバック情報
        """
        try:
            processor = YAMLHeaderProcessor(self.config_manager, self.integrated_logger)
            
            # 現在のYAMLヘッダー読み込み
            current_yaml, markdown_content = processor.parse_yaml_header(Path(paper_path))
            
            # タグセクション更新
            current_yaml['tags'] = tags
            
            # タグ品質情報追加
            if 'tag_quality' not in current_yaml:
                current_yaml['tag_quality'] = {}
            
            current_yaml['tag_quality'].update({
                'quality_score': feedback.get('quality_score', 0.0),
                'tag_count': feedback.get('tag_count', len(tags)),
                'format_compliance': feedback.get('format_compliance', 0.0),
                'content_relevance': feedback.get('content_relevance', 0.0),
                'evaluation_timestamp': feedback.get('evaluation_timestamp'),
                'has_suggestions': len(feedback.get('suggestions', [])) > 0
            })
            
            # processing_status更新
            if 'processing_status' not in current_yaml:
                current_yaml['processing_status'] = {}
            current_yaml['processing_status']['tagger'] = 'completed'
            
            # last_updated更新
            current_yaml['last_updated'] = datetime.now().isoformat()
            
            # YAMLヘッダー書き込み
            processor.write_yaml_header(Path(paper_path), current_yaml, markdown_content)
            
            self.logger.debug(f"Updated YAML header with {len(tags)} tags and quality info for {paper_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header with quality info for {paper_path}: {e}")
            raise ProcessingError(
                message=f"YAML header update with quality failed for {paper_path}",
                error_code="YAML_UPDATE_FAILED",
                context={"paper_path": paper_path, "tags": tags, "feedback": feedback}
            ) from e
    
    def evaluate_tag_quality(self, tags: List[str], paper_content: str) -> float:
        """
        タグ品質の評価
        
        Args:
            tags: 評価対象のタグリスト
            paper_content: 論文コンテンツ
            
        Returns:
            float: 品質スコア（0.0-1.0）
        """
        try:
            total_score = 0.0
            max_score = 0.0
            
            # 1. タグ数の適切性（重み: 0.2）
            tag_count_score = self._evaluate_tag_count(len(tags))
            total_score += tag_count_score * 0.2
            max_score += 0.2
            
            # 2. タグ形式の適切性（重み: 0.2）
            format_score = self._evaluate_tag_format(tags)
            total_score += format_score * 0.2
            max_score += 0.2
            
            # 3. 内容関連性（重み: 0.4）
            relevance_score = self._evaluate_content_relevance(tags, paper_content)
            total_score += relevance_score * 0.4
            max_score += 0.4
            
            # 4. 専門性・多様性（重み: 0.2）
            diversity_score = self._evaluate_tag_diversity(tags)
            total_score += diversity_score * 0.2
            max_score += 0.2
            
            quality_score = total_score / max_score if max_score > 0 else 0.0
            
            self.logger.debug(f"Tag quality evaluation: {quality_score:.3f} "
                            f"(count: {tag_count_score:.2f}, format: {format_score:.2f}, "
                            f"relevance: {relevance_score:.2f}, diversity: {diversity_score:.2f})")
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate tag quality: {e}")
            return 0.0
    
    def generate_feedback_report(self, tags: List[str], paper_content: str, quality_score: float) -> Dict[str, Any]:
        """
        フィードバックレポートの生成
        
        Args:
            tags: タグリスト
            paper_content: 論文コンテンツ
            quality_score: 品質スコア
            
        Returns:
            Dict[str, Any]: フィードバックレポート
        """
        try:
            # 基本統計
            tag_count = len(tags)
            format_compliance = sum(1 for tag in tags if self._validate_tag_format(tag)) / tag_count if tag_count > 0 else 0
            
            # 内容関連性の評価
            content_relevance = self._evaluate_content_relevance(tags, paper_content)
            
            # 改善提案
            suggestions = self.suggest_improvements(tags, paper_content)
            
            feedback = {
                'quality_score': quality_score,
                'tag_count': tag_count,
                'format_compliance': format_compliance,
                'content_relevance': content_relevance,
                'suggestions': suggestions,
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
            self.logger.debug(f"Generated feedback report: quality={quality_score:.3f}, "
                            f"suggestions={len(suggestions)}")
            
            return feedback
            
        except Exception as e:
            self.logger.error(f"Failed to generate feedback report: {e}")
            return {'error': str(e)}
    
    def suggest_improvements(self, tags: List[str], paper_content: str) -> List[str]:
        """
        改善提案の生成
        
        Args:
            tags: 現在のタグリスト
            paper_content: 論文コンテンツ
            
        Returns:
            List[str]: 改善提案リスト
        """
        suggestions = []
        
        try:
            # タグ数の確認
            min_tags, max_tags = self.tag_count_range
            if len(tags) < min_tags:
                suggestions.append(f"Consider adding more tags (current: {len(tags)}, recommended: {min_tags}-{max_tags})")
            elif len(tags) > max_tags:
                suggestions.append(f"Consider reducing number of tags (current: {len(tags)}, recommended: {min_tags}-{max_tags})")
            
            # フォーマット確認
            invalid_format_tags = [tag for tag in tags if not self._validate_tag_format(tag)]
            if invalid_format_tags:
                suggestions.append(f"Fix tag format for: {', '.join(invalid_format_tags[:3])} (use snake_case)")
            
            # 内容関連性の確認
            paper_lower = paper_content.lower()
            
            # 重要なキーワードが漏れていないかチェック
            important_keywords = self._extract_important_keywords(paper_content)
            missing_keywords = [kw for kw in important_keywords if not any(kw.lower() in tag.lower() for tag in tags)]
            if missing_keywords:
                suggestions.append(f"Consider adding tags for important concepts: {', '.join(missing_keywords[:3])}")
            
            # 重複や類似タグの確認
            similar_tags = self._find_similar_tags(tags)
            if similar_tags:
                suggestions.append(f"Consider consolidating similar tags: {', '.join(similar_tags[:3])}")
            
            self.logger.debug(f"Generated {len(suggestions)} improvement suggestions")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate suggestions: {e}")
            return ["Error generating suggestions"]
    
    def validate_tag_relevance(self, tag: str, paper_content: str) -> float:
        """
        タグの内容関連性を検証
        
        Args:
            tag: 検証するタグ
            paper_content: 論文コンテンツ
            
        Returns:
            float: 関連性スコア（0.0-1.0）
        """
        try:
            paper_lower = paper_content.lower()
            tag_lower = tag.lower()
            
            # 直接一致
            if tag_lower in paper_lower:
                return 1.0
            
            # 部分一致
            tag_words = tag_lower.replace('_', ' ').split()
            match_count = sum(1 for word in tag_words if word in paper_lower)
            if len(tag_words) > 0:
                partial_score = match_count / len(tag_words)
                return min(partial_score * 0.8, 1.0)  # 部分一致は最大0.8
            
            # 関連語彙チェック（簡単な例）
            related_terms = self._get_related_terms(tag_lower)
            related_matches = sum(1 for term in related_terms if term in paper_lower)
            if len(related_terms) > 0:
                related_score = related_matches / len(related_terms)
                return min(related_score * 0.6, 1.0)  # 関連語は最大0.6
            
            return 0.0
            
        except Exception as e:
            self.logger.error(f"Failed to validate tag relevance for '{tag}': {e}")
            return 0.0
    
    def _evaluate_tag_count(self, count: int) -> float:
        """タグ数の適切性評価"""
        min_tags, max_tags = self.tag_count_range
        if min_tags <= count <= max_tags:
            return 1.0
        elif count < min_tags:
            return max(0.0, count / min_tags)
        else:  # count > max_tags
            return max(0.0, 1.0 - (count - max_tags) / max_tags)
    
    def _evaluate_tag_format(self, tags: List[str]) -> float:
        """タグ形式の適切性評価"""
        if not tags:
            return 0.0
        valid_count = sum(1 for tag in tags if self._validate_tag_format(tag))
        return valid_count / len(tags)
    
    def _evaluate_content_relevance(self, tags: List[str], paper_content: str) -> float:
        """内容関連性の評価"""
        if not tags:
            return 0.0
        relevance_scores = [self.validate_tag_relevance(tag, paper_content) for tag in tags]
        return sum(relevance_scores) / len(relevance_scores)
    
    def _evaluate_tag_diversity(self, tags: List[str]) -> float:
        """タグの多様性評価"""
        if not tags:
            return 0.0
        
        # 異なるカテゴリのタグの存在を確認
        categories = {
            'gene': 0,    # 遺伝子名
            'disease': 0, # 疾患名
            'method': 0,  # 手法
            'general': 0  # 一般的なタグ
        }
        
        for tag in tags:
            if re.match(r'^[A-Z]+[0-9]*$', tag.replace('_', '').upper()):
                categories['gene'] += 1
            elif any(term in tag.lower() for term in ['cancer', 'disease', 'tumor', 'syndrome']):
                categories['disease'] += 1
            elif any(term in tag.lower() for term in ['analysis', 'method', 'technique', 'assay']):
                categories['method'] += 1
            else:
                categories['general'] += 1
        
        # 複数カテゴリに分散していることを評価
        active_categories = sum(1 for count in categories.values() if count > 0)
        return min(active_categories / 3.0, 1.0)  # 3カテゴリ以上で満点
    
    def _extract_important_keywords(self, paper_content: str) -> List[str]:
        """重要なキーワードの抽出"""
        # 簡単な実装：大文字の単語（遺伝子名など）と頻出する専門用語
        content_upper = paper_content.upper()
        
        # 遺伝子名パターン
        gene_pattern = re.findall(r'\b[A-Z]{2,}[0-9]*\b', paper_content)
        
        # よく使われる専門用語
        common_terms = ['cancer', 'biomarker', 'expression', 'mutation', 'protein', 'analysis']
        found_terms = [term for term in common_terms if term.lower() in paper_content.lower()]
        
        return list(set(gene_pattern[:3] + found_terms[:3]))  # 最大6個
    
    def _find_similar_tags(self, tags: List[str]) -> List[str]:
        """類似タグの検出"""
        similar = []
        for i, tag1 in enumerate(tags):
            for tag2 in tags[i+1:]:
                if self._are_tags_similar(tag1, tag2):
                    similar.extend([tag1, tag2])
        return list(set(similar))
    
    def _are_tags_similar(self, tag1: str, tag2: str) -> bool:
        """2つのタグが類似しているかの判定"""
        # 簡単な類似性判定
        words1 = set(tag1.replace('_', ' ').split())
        words2 = set(tag2.replace('_', ' ').split())
        
        # 共通語彙が50%以上
        if words1 and words2:
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            return intersection / union > 0.5
        
        return False
    
    def _get_related_terms(self, tag: str) -> List[str]:
        """タグに関連する用語を取得"""
        # 簡単な関連語辞書
        related_dict = {
            'cancer': ['tumor', 'carcinoma', 'oncology', 'malignant'],
            'biomarker': ['marker', 'indicator', 'predictor'],
            'analysis': ['study', 'evaluation', 'assessment'],
            'expression': ['level', 'abundance', 'concentration']
        }
        
        for key, related_terms in related_dict.items():
            if key in tag.lower():
                return related_terms
        
        return [] 