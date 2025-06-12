"""
落合フォーマット要約機能のデータ構造

学術論文の内容を6つの構造化された質問に答える形で要約する
落合フォーマットのデータ構造を定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class OchiaiFormat:
    """
    落合フォーマット要約データ構造
    
    学術論文を6つの質問項目で構造化要約：
    1. どんなもの？
    2. 先行研究と比べてどこがすごい？
    3. 技術や手法のキモはどこ？
    4. どうやって有効だと検証した？
    5. 議論はある？
    6. 次に読むべき論文は？
    """
    
    what_is_this: str = ""              # どんなもの？
    what_is_superior: str = ""          # 先行研究と比べてどこがすごい？
    technical_key: str = ""             # 技術や手法のキモはどこ？
    validation_method: str = ""         # どうやって有効だと検証した？
    discussion_points: str = ""         # 議論はある？
    next_papers: str = ""              # 次に読むべき論文は？
    generated_at: str = ""             # 生成日時
    
    def __post_init__(self):
        """初期化後処理"""
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        辞書形式に変換
        
        Returns:
            YAMLヘッダー用の辞書
        """
        return {
            'generated_at': self.generated_at,
            'questions': {
                'what_is_this': self.what_is_this,
                'what_is_superior': self.what_is_superior,
                'technical_key': self.technical_key,
                'validation_method': self.validation_method,
                'discussion_points': self.discussion_points,
                'next_papers': self.next_papers
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OchiaiFormat':
        """
        辞書から復元
        
        Args:
            data: 辞書データ
            
        Returns:
            OchiaiFormatインスタンス
        """
        questions = data.get('questions', {})
        
        return cls(
            what_is_this=questions.get('what_is_this', ''),
            what_is_superior=questions.get('what_is_superior', ''),
            technical_key=questions.get('technical_key', ''),
            validation_method=questions.get('validation_method', ''),
            discussion_points=questions.get('discussion_points', ''),
            next_papers=questions.get('next_papers', ''),
            generated_at=data.get('generated_at', '')
        )
    
    def is_valid(self) -> bool:
        """
        要約の妥当性検証
        
        Returns:
            全ての質問項目が適切に回答されているかどうか
        """
        required_fields = [
            self.what_is_this,
            self.what_is_superior,
            self.technical_key,
            self.validation_method,
            self.discussion_points,
            self.next_papers
        ]
        
        # 全ての項目が空でなく、最小文字数を満たしているかチェック
        min_length = 20  # 最小文字数
        return all(
            field and isinstance(field, str) and len(field.strip()) >= min_length
            for field in required_fields
        )
    
    def get_summary_statistics(self) -> Dict[str, int]:
        """
        要約統計情報を取得
        
        Returns:
            各項目の文字数統計
        """
        return {
            'what_is_this_length': len(self.what_is_this),
            'what_is_superior_length': len(self.what_is_superior),
            'technical_key_length': len(self.technical_key),
            'validation_method_length': len(self.validation_method),
            'discussion_points_length': len(self.discussion_points),
            'next_papers_length': len(self.next_papers),
            'total_length': sum([
                len(self.what_is_this),
                len(self.what_is_superior),
                len(self.technical_key),
                len(self.validation_method),
                len(self.discussion_points),
                len(self.next_papers)
            ])
        }
    
    def format_for_display(self) -> str:
        """
        表示用フォーマット
        
        Returns:
            読みやすい形式の文字列
        """
        questions = [
            ("どんなもの？", self.what_is_this),
            ("先行研究と比べてどこがすごい？", self.what_is_superior),
            ("技術や手法のキモはどこ？", self.technical_key),
            ("どうやって有効だと検証した？", self.validation_method),
            ("議論はある？", self.discussion_points),
            ("次に読むべき論文は？", self.next_papers)
        ]
        
        formatted_sections = []
        for question, answer in questions:
            formatted_sections.append(f"## {question}\n{answer}\n")
        
        return "\n".join(formatted_sections)
    
    def __str__(self) -> str:
        """文字列表現"""
        return f"OchiaiFormat(generated_at={self.generated_at}, valid={self.is_valid()})"
    
    def __repr__(self) -> str:
        """詳細文字列表現"""
        stats = self.get_summary_statistics()
        return (f"OchiaiFormat(generated_at={self.generated_at}, "
                f"total_length={stats['total_length']}, valid={self.is_valid()})")


def create_ochiai_format_from_json_response(json_data: Dict[str, str]) -> OchiaiFormat:
    """
    Claude APIからのJSON応答から OchiaiFormat を作成
    
    Args:
        json_data: Claude API応答のJSON辞書
        
    Returns:
        OchiaiFormatインスタンス
        
    Raises:
        KeyError: 必要なキーが不足している場合
        ValueError: データが不正な場合
    """
    required_keys = [
        'what_is_this', 'what_is_superior', 'technical_key',
        'validation_method', 'discussion_points', 'next_papers'
    ]
    
    # 必要なキーの存在確認
    missing_keys = [key for key in required_keys if key not in json_data]
    if missing_keys:
        raise KeyError(f"Missing required keys: {missing_keys}")
    
    # データの妥当性確認
    for key, value in json_data.items():
        if key in required_keys and not isinstance(value, str):
            raise ValueError(f"Invalid data type for {key}: expected str, got {type(value)}")
    
    return OchiaiFormat(
        what_is_this=json_data['what_is_this'],
        what_is_superior=json_data['what_is_superior'],
        technical_key=json_data['technical_key'],
        validation_method=json_data['validation_method'],
        discussion_points=json_data['discussion_points'],
        next_papers=json_data['next_papers']
    ) 