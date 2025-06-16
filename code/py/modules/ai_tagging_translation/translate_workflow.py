"""
Translate Workflow

論文要約翻訳ワークフロークラス
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


class TranslateWorkflow:
    """
    論文要約翻訳ワークフロー
    
    Claude 3.5 Haikuを使用して論文のabstractを自然で正確な日本語に翻訳します。
    """
    
    def __init__(self, config_manager: ConfigManager, logger: IntegratedLogger):
        """
        TranslateWorkflow初期化
        
        Args:
            config_manager: 設定管理インスタンス
            logger: ログ管理インスタンス
        """
        self.config_manager = config_manager
        self.integrated_logger = logger
        self.logger = logger.get_logger('TranslateWorkflow')
        
        # 設定値取得
        self.enabled = config_manager.get_ai_setting('translate_abstract', 'enabled', default=True)
        self.batch_size = config_manager.get_ai_setting('translate_abstract', 'batch_size', default=5)
        
        # Claude APIクライアント（遅延初期化）
        self._claude_client = None
        
        self.logger.info(f"TranslateWorkflow initialized (enabled: {self.enabled}, batch_size: {self.batch_size})")
    
    @property
    def claude_client(self) -> ClaudeAPIClient:
        """Claude APIクライアントの遅延初期化"""
        if self._claude_client is None:
            self._claude_client = ClaudeAPIClient(self.config_manager, self.integrated_logger)
        return self._claude_client
    
    def process_items(self, input_dir: str, target_items: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        論文の一括要約翻訳処理
        
        Args:
            input_dir: 処理対象ディレクトリ
            target_items: 処理対象論文リスト（Noneの場合は全て）
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        if not self.enabled:
            self.logger.info("Translate workflow is disabled")
            return {'status': 'disabled', 'processed': 0, 'skipped': 0, 'failed': 0}
        
        self.logger.info(f"Starting translate processing for directory: {input_dir}")
        
        # 処理対象論文の取得
        status_manager = StatusManager(self.config_manager, self.integrated_logger)
        papers_needing_processing = status_manager.get_papers_needing_processing(
            input_dir, 'translate_abstract', target_items
        )
        
        processed_count = 0
        failed_count = 0
        
        for paper_path in papers_needing_processing:
            try:
                self.logger.debug(f"Processing translation for: {paper_path}")
                
                # Abstract翻訳
                translation = self.translate_abstract_single(paper_path)
                
                if translation:
                    # 翻訳品質評価
                    original_abstract = self.extract_abstract_content(paper_path)
                    quality_score = self.evaluate_translation_quality(translation, original_abstract)
                    
                    # フィードバックレポート生成
                    feedback = self.generate_feedback_report(translation, original_abstract, quality_score)
                    
                    # 品質スコアをログ出力
                    self.logger.info(f"Translation completed for {Path(paper_path).name} "
                                   f"(quality: {quality_score:.3f}, length: {len(translation)} chars)")
                    
                    # 改善提案があればログ出力
                    if feedback.get('suggestions'):
                        self.logger.debug(f"Translation suggestions: {'; '.join(feedback['suggestions'][:2])}")
                    
                    # YAMLヘッダー更新（品質情報も含む）
                    self.update_yaml_with_translation_and_quality(paper_path, translation, feedback)
                    
                    # citation_keyを抽出してから状態更新
                    citation_key = Path(paper_path).parent.name
                    status_manager.update_status(input_dir, citation_key, 'translate_abstract', 'completed')
                    processed_count += 1
                else:
                    # 翻訳失敗
                    citation_key = Path(paper_path).parent.name
                    status_manager.update_status(input_dir, citation_key, 'translate_abstract', 'failed')
                    failed_count += 1
                    self.logger.warning(f"No translation generated for {Path(paper_path).name}")
                    
            except Exception as e:
                self.logger.error(f"Failed to translate abstract for {paper_path}: {e}")
                citation_key = Path(paper_path).parent.name
                status_manager.update_status(input_dir, citation_key, 'translate_abstract', 'failed')
                failed_count += 1
        
        result = {
            'status': 'completed',
            'processed': processed_count,
            'skipped': len(papers_needing_processing) - processed_count - failed_count,
            'failed': failed_count,
            'total_papers': len(papers_needing_processing)
        }
        
        self.logger.info(f"Translate processing completed: {result}")
        return result
    
    def translate_abstract_single(self, paper_path: str) -> str:
        """
        単一論文のabstract翻訳
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            str: 翻訳されたabstract（日本語）
        """
        try:
            # Abstract抽出
            abstract_content = self.extract_abstract_content(paper_path)
            
            if not abstract_content or len(abstract_content.strip()) < 50:
                self.logger.warning(f"Abstract content too short or missing for {paper_path}")
                return ""
            
            # プロンプト構築
            prompt = self._build_translation_prompt(abstract_content)
            
            # Claude API呼び出し
            response = self.claude_client.send_request(prompt)
            
            # レスポンス解析
            translation = self._parse_translation_response(response)
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Failed to translate abstract for {paper_path}: {e}")
            raise ProcessingError(
                message=f"Abstract translation failed for {paper_path}",
                error_code="TRANSLATION_FAILED",
                context={"paper_path": paper_path}
            ) from e
    
    def extract_abstract_content(self, paper_path: str) -> str:
        """
        論文からabstractセクションを抽出
        
        Args:
            paper_path: 論文ファイルパス
            
        Returns:
            str: abstractコンテンツ
        """
        try:
            # YAMLヘッダー解析
            processor = YAMLHeaderProcessor(self.config_manager, self.integrated_logger)
            yaml_data, markdown_content = processor.parse_yaml_header(Path(paper_path))
            
            # paper_structure から abstract セクションを取得
            paper_structure = yaml_data.get('paper_structure', {})
            sections = paper_structure.get('sections', [])
            
            if not sections:
                self.logger.warning(f"No paper_structure found in {paper_path}")
                return ""
            
            # abstractセクションを探す
            markdown_lines = markdown_content.split('\n')
            
            for section in sections:
                section_type = section.get('section_type')
                if section_type == 'abstract':
                    start_line = section.get('start_line', 0)
                    end_line = section.get('end_line', len(markdown_lines))
                    
                    # subsectionsがある場合は、最後のsubsectionのend_lineまで含める
                    subsections = section.get('subsections', [])
                    if subsections:
                        # 全subsectionの中で最大のend_lineを取得
                        max_subsection_end = max(sub.get('end_line', end_line) for sub in subsections)
                        # abstractセクションのend_lineと比較して大きい方を使用
                        end_line = max(end_line, max_subsection_end)
                        self.logger.debug(f"Abstract has {len(subsections)} subsections, "
                                        f"extended end_line to {end_line}")
                    
                    # セクション内容抽出（行範囲ベース、1-indexedから0-indexedに変換）
                    abstract_content = '\n'.join(markdown_lines[start_line-1:end_line])
                    
                    # マークダウンのヘッダー記号を除去
                    abstract_content = re.sub(r'^#+\s*', '', abstract_content, flags=re.MULTILINE)
                    abstract_content = abstract_content.strip()
                    
                    self.logger.debug(f"Extracted abstract section: lines {start_line}-{end_line} "
                                    f"({len(abstract_content)} chars)")
                    
                    return abstract_content
            
            self.logger.warning(f"No abstract section found in {paper_path}")
            return ""
            
        except Exception as e:
            self.logger.error(f"Failed to extract abstract from {paper_path}: {e}")
            raise ProcessingError(
                message=f"Abstract extraction failed for {paper_path}",
                error_code="ABSTRACT_EXTRACTION_FAILED",
                context={"paper_path": paper_path}
            ) from e
    
    def _build_translation_prompt(self, abstract_content: str) -> str:
        """
        翻訳プロンプトの構築
        
        Args:
            abstract_content: 原文abstract
            
        Returns:
            str: 構築されたプロンプト
        """
        prompt = f"""
以下の学術論文のabstractを自然で正確な日本語に翻訳してください。

## **翻訳要件**

**品質基準:**
- **自然性**: 学術論文として適切な日本語表現を使用
- **正確性**: 専門用語の適切な翻訳と一貫性の維持
- **完全性**: 原文の情報量を保持し、詳細な内容を省略しない
- **読みやすさ**: 理解しやすい文章構成と適切な文体

**翻訳指針:**
1. **専門用語処理**: 
   - 遺伝子名・タンパク質名: 原文のまま保持（例: KRT13, EGFR, TP53）
   - 疾患名: 日本語標準訳語を使用（例: breast cancer → 乳癌）
   - 技術手法: 一般的な日本語訳語を使用（例: Western blot → ウエスタンブロット）

2. **文体・表現**:
   - 学術論文として適切な敬語・丁寧語を使用
   - 能動態・受動態の適切な使い分け
   - 論理的な接続詞の使用

3. **数値・統計**:
   - 数値は原文のまま保持
   - 統計用語は標準的な日本語訳語を使用

4. **文章構成**:
   - 原文の段落構成を保持
   - 日本語として自然な文の区切りと接続

## **Original Abstract:**
---
{abstract_content}
---

**日本語翻訳:**

"""

        return prompt
    
    def _parse_translation_response(self, response: str) -> str:
        """
        Claude APIレスポンスから翻訳を解析
        
        Args:
            response: Claude APIレスポンス
            
        Returns:
            str: 解析された翻訳テキスト
        """
        try:
            # レスポンスを整形
            translation = response.strip()
            
            # 余分な装飾や説明文を除去
            # "日本語翻訳:" などのラベルがある場合のみ除去、それ以外はそのまま保持
            colon_match = re.match(r'^[^:：]*[:：]\s*', translation)
            if colon_match:
                # コロンより前の部分を取得
                prefix_part = translation[:colon_match.end()].split(':')[0].split('：')[0]
                # プレフィックス部分に日本語が含まれていない場合のみ除去
                if not re.search(r'[ひらがなカタカナ漢字]', prefix_part):
                    translation = re.sub(r'^[^:：]*[:：]\s*', '', translation).strip()
            
            # 改行で分割して空行を除去
            lines = [line.strip() for line in translation.split('\n') if line.strip()]
            translation = '\n'.join(lines)
            
            # 最低限の長さをチェック
            if len(translation) < 50:
                self.logger.warning(f"Translation appears too short: {len(translation)} chars")
                return ""
            
            # 日本語文字が含まれているかチェック
            if not re.search(r'[ひらがなカタカナ漢字]', translation):
                self.logger.warning("Translation does not contain Japanese characters")
                return ""
            
            self.logger.debug(f"Parsed translation: {len(translation)} chars")
            return translation
            
        except Exception as e:
            self.logger.error(f"Failed to parse translation response: {e}")
            self.logger.debug(f"Response content: '{response[:200]}...'")
            return ""
    
    def evaluate_translation_quality(self, translation: str, original: str) -> float:
        """
        翻訳品質の評価
        
        Args:
            translation: 翻訳文（日本語）
            original: 原文（英語）
            
        Returns:
            float: 品質スコア（0.0-1.0）
        """
        try:
            total_score = 0.0
            max_score = 0.0
            
            # 1. 完全性評価（重み: 0.3）
            completeness_score = self._evaluate_completeness(translation, original)
            total_score += completeness_score * 0.3
            max_score += 0.3
            
            # 2. 自然性評価（重み: 0.25）
            fluency_score = self._evaluate_fluency(translation)
            total_score += fluency_score * 0.25
            max_score += 0.25
            
            # 3. 一貫性評価（重み: 0.25）
            consistency_score = self._evaluate_consistency(translation)
            total_score += consistency_score * 0.25
            max_score += 0.25
            
            # 4. 正確性評価（重み: 0.2）
            accuracy_score = self._evaluate_accuracy(translation, original)
            total_score += accuracy_score * 0.2
            max_score += 0.2
            
            quality_score = total_score / max_score if max_score > 0 else 0.0
            
            self.logger.debug(f"Translation quality evaluation: {quality_score:.3f} "
                            f"(completeness: {completeness_score:.2f}, fluency: {fluency_score:.2f}, "
                            f"consistency: {consistency_score:.2f}, accuracy: {accuracy_score:.2f})")
            
            return quality_score
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate translation quality: {e}")
            return 0.0
    
    def generate_feedback_report(self, translation: str, original: str, quality_score: float) -> Dict[str, Any]:
        """
        翻訳フィードバックレポートの生成
        
        Args:
            translation: 翻訳文
            original: 原文
            quality_score: 品質スコア
            
        Returns:
            Dict[str, Any]: フィードバックレポート
        """
        try:
            # 基本統計
            original_length = len(original)
            translation_length = len(translation)
            length_ratio = translation_length / original_length if original_length > 0 else 0
            
            # 各評価軸のスコア
            completeness = self._evaluate_completeness(translation, original)
            fluency = self._evaluate_fluency(translation)
            consistency = self._evaluate_consistency(translation)
            accuracy = self._evaluate_accuracy(translation, original)
            
            # 改善提案
            suggestions = self.suggest_translation_improvements(translation, original)
            
            feedback = {
                'quality_score': quality_score,
                'original_length': original_length,
                'translation_length': translation_length,
                'length_ratio': length_ratio,
                'completeness_score': completeness,
                'fluency_score': fluency,
                'consistency_score': consistency,
                'accuracy_score': accuracy,
                'suggestions': suggestions,
                'evaluation_timestamp': datetime.now().isoformat()
            }
            
            self.logger.debug(f"Generated translation feedback: quality={quality_score:.3f}, "
                            f"suggestions={len(suggestions)}")
            
            return feedback
            
        except Exception as e:
            self.logger.error(f"Failed to generate translation feedback: {e}")
            return {'error': str(e)}
    
    def suggest_translation_improvements(self, translation: str, original: str) -> List[str]:
        """
        翻訳改善提案の生成
        
        Args:
            translation: 翻訳文
            original: 原文
            
        Returns:
            List[str]: 改善提案リスト
        """
        suggestions = []
        
        try:
            # 長さの比較
            length_ratio = len(translation) / len(original) if len(original) > 0 else 0
            if length_ratio < 0.7:
                suggestions.append("Translation appears shorter than expected - check for missing content")
            elif length_ratio > 2.0:
                suggestions.append("Translation appears longer than expected - consider conciseness")
            
            # 日本語文字の確認
            if not re.search(r'[ひらがなカタカナ漢字]', translation):
                suggestions.append("Translation should contain Japanese characters")
            
            # 専門用語の確認（遺伝子名など）
            gene_symbols = re.findall(r'\b[A-Z]{2,}[0-9]*\b', original)
            missing_genes = []
            for gene in gene_symbols[:5]:  # 最初の5個まで
                if gene not in translation:
                    missing_genes.append(gene)
            if missing_genes:
                suggestions.append(f"Consider preserving gene symbols: {', '.join(missing_genes)}")
            
            # 数値の確認
            numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', original)
            missing_numbers = []
            for number in numbers[:3]:  # 最初の3個まで
                if number not in translation:
                    missing_numbers.append(number)
            if missing_numbers:
                suggestions.append(f"Consider preserving numerical values: {', '.join(missing_numbers)}")
            
            # 文章の自然性チェック（簡易）
            sentences = translation.split('。')
            long_sentences = [s for s in sentences if len(s) > 150]
            if long_sentences:
                suggestions.append("Consider breaking down very long sentences for readability")
            
            self.logger.debug(f"Generated {len(suggestions)} translation improvement suggestions")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate translation suggestions: {e}")
            return ["Error generating suggestions"]
    
    def update_yaml_with_translation_and_quality(self, paper_path: str, translation: str, feedback: Dict[str, Any]):
        """
        YAMLヘッダーに翻訳と品質情報を更新
        
        Args:
            paper_path: 論文ファイルパス
            translation: 翻訳文
            feedback: 品質フィードバック情報
        """
        try:
            processor = YAMLHeaderProcessor(self.config_manager, self.integrated_logger)
            
            # 現在のYAMLヘッダー読み込み
            current_yaml, markdown_content = processor.parse_yaml_header(Path(paper_path))
            
            # ai_contentセクション初期化
            if 'ai_content' not in current_yaml:
                current_yaml['ai_content'] = {}
            
            # abstract_japaneseセクション更新
            current_yaml['ai_content']['abstract_japanese'] = {
                'generated_at': datetime.now().isoformat(),
                'content': translation
            }
            
            # 翻訳品質情報追加
            if 'translation_quality' not in current_yaml:
                current_yaml['translation_quality'] = {}
            
            current_yaml['translation_quality'].update({
                'quality_score': feedback.get('quality_score', 0.0),
                'completeness_score': feedback.get('completeness_score', 0.0),
                'fluency_score': feedback.get('fluency_score', 0.0),
                'consistency_score': feedback.get('consistency_score', 0.0),
                'accuracy_score': feedback.get('accuracy_score', 0.0),
                'original_length': feedback.get('original_length', 0),
                'translation_length': feedback.get('translation_length', 0),
                'length_ratio': feedback.get('length_ratio', 0.0),
                'evaluation_timestamp': feedback.get('evaluation_timestamp'),
                'has_suggestions': len(feedback.get('suggestions', [])) > 0
            })
            
            # processing_status更新
            if 'processing_status' not in current_yaml:
                current_yaml['processing_status'] = {}
            current_yaml['processing_status']['translate_abstract'] = 'completed'
            
            # last_updated更新
            current_yaml['last_updated'] = datetime.now().isoformat()
            
            # YAMLヘッダー書き込み
            processor.write_yaml_header(Path(paper_path), current_yaml, markdown_content)
            
            self.logger.debug(f"Updated YAML header with translation and quality info for {paper_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to update YAML header with translation for {paper_path}: {e}")
            raise ProcessingError(
                message=f"YAML header update with translation failed for {paper_path}",
                error_code="YAML_UPDATE_FAILED",
                context={"paper_path": paper_path, "translation": translation, "feedback": feedback}
            ) from e
    
    def _evaluate_completeness(self, translation: str, original: str) -> float:
        """完全性評価 - 原文の情報量が保持されているか"""
        try:
            # 簡易的な完全性評価
            length_ratio = len(translation) / len(original) if len(original) > 0 else 0
            
            # 理想的な長さ比率を0.8-1.5と仮定
            if 0.8 <= length_ratio <= 1.5:
                return 1.0
            elif length_ratio < 0.8:
                return max(0.0, length_ratio / 0.8)
            else:  # length_ratio > 1.5
                return max(0.0, 1.0 - (length_ratio - 1.5) / 1.5)
        except:
            return 0.5
    
    def _evaluate_fluency(self, translation: str) -> float:
        """自然性評価 - 日本語として自然か"""
        try:
            score = 0.0
            
            # 日本語文字の存在確認
            if re.search(r'[ひらがなカタカナ漢字]', translation):
                score += 0.4
            
            # 適切な句読点の使用
            if '。' in translation or '、' in translation:
                score += 0.3
            
            # 極端に長い文の確認（減点）
            sentences = translation.split('。')
            avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
            if avg_sentence_length < 200:  # 適切な文長
                score += 0.3
            
            return min(score, 1.0)
        except:
            return 0.5
    
    def _evaluate_consistency(self, translation: str) -> float:
        """一貫性評価 - 用語統一など"""
        try:
            # 簡易的な一貫性評価
            # 英語の混入度合いを確認
            english_words = re.findall(r'\b[a-zA-Z]+\b', translation)
            japanese_chars = len(re.findall(r'[ひらがなカタカナ漢字]', translation))
            
            if japanese_chars == 0:
                return 0.0
            
            # 適度な英語混入は許容（専門用語のため）
            english_ratio = len(english_words) / (japanese_chars / 10) if japanese_chars > 0 else 0
            if english_ratio <= 0.5:
                return 1.0
            elif english_ratio <= 1.0:
                return 0.7
            else:
                return 0.4
        except:
            return 0.5
    
    def _evaluate_accuracy(self, translation: str, original: str) -> float:
        """正確性評価 - 専門用語や数値の正確性"""
        try:
            score = 0.0
            
            # 数値の保持確認
            original_numbers = set(re.findall(r'\b\d+(?:\.\d+)?%?\b', original))
            preserved_numbers = 0
            for num in original_numbers:
                if num in translation:
                    preserved_numbers += 1
            
            if original_numbers:
                score += 0.5 * (preserved_numbers / len(original_numbers))
            else:
                score += 0.5
            
            # 遺伝子名の保持確認
            gene_symbols = set(re.findall(r'\b[A-Z]{2,}[0-9]*\b', original))
            preserved_genes = 0
            for gene in gene_symbols:
                if gene in translation:
                    preserved_genes += 1
            
            if gene_symbols:
                score += 0.5 * (preserved_genes / len(gene_symbols))
            else:
                score += 0.5
            
            return min(score, 1.0)
        except:
            return 0.5