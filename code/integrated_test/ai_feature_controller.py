"""
AI機能制御クラス

統合テストにおけるAI機能（enhanced-tagger、enhanced-translate、ochiai-format）の
個別有効化/無効化を制御する開発用機能
"""

import argparse
from typing import List


class AIFeatureController:
    """AI機能の有効/無効制御"""
    
    def __init__(self, args):
        """
        Args:
            args: argparse.Namespace - コマンドライン引数
        """
        self.args = args
        self._validate_arguments()
    
    def _validate_arguments(self):
        """引数の整合性チェック"""
        # enable-only と disable の同時指定チェック
        enable_only_flags = [
            getattr(self.args, 'enable_only_tagger', False), 
            getattr(self.args, 'enable_only_translate', False), 
            getattr(self.args, 'enable_only_ochiai', False)
        ]
        
        disable_flags = [
            getattr(self.args, 'disable_ai', False),
            getattr(self.args, 'disable_tagger', False),
            getattr(self.args, 'disable_translate', False),
            getattr(self.args, 'disable_ochiai', False)
        ]
        
        if any(enable_only_flags) and any(disable_flags):
            raise ValueError("--enable-only-* と --disable-* オプションは同時指定できません")
    
    def is_tagger_enabled(self) -> bool:
        """enhanced-tagger機能が有効かチェック"""
        if getattr(self.args, 'disable_ai', False) or getattr(self.args, 'disable_tagger', False):
            return False
        if getattr(self.args, 'enable_only_translate', False) or getattr(self.args, 'enable_only_ochiai', False):
            return False
        return True  # デフォルト有効
    
    def is_translate_enabled(self) -> bool:
        """enhanced-translate機能が有効かチェック"""
        if getattr(self.args, 'disable_ai', False) or getattr(self.args, 'disable_translate', False):
            return False
        if getattr(self.args, 'enable_only_tagger', False) or getattr(self.args, 'enable_only_ochiai', False):
            return False
        return True  # デフォルト有効
    
    def is_ochiai_enabled(self) -> bool:
        """ochiai-format機能が有効かチェック"""
        if getattr(self.args, 'disable_ai', False) or getattr(self.args, 'disable_ochiai', False):
            return False
        if getattr(self.args, 'enable_only_tagger', False) or getattr(self.args, 'enable_only_translate', False):
            return False
        return True  # デフォルト有効
    
    def get_enabled_features(self) -> List[str]:
        """有効なAI機能のリストを取得"""
        enabled_features = []
        if self.is_tagger_enabled():
            enabled_features.append("enhanced-tagger")
        if self.is_translate_enabled():
            enabled_features.append("enhanced-translate")
        if self.is_ochiai_enabled():
            enabled_features.append("ochiai-format")
        return enabled_features
    
    def get_disabled_features(self) -> List[str]:
        """無効なAI機能のリストを取得"""
        disabled_features = []
        if not self.is_tagger_enabled():
            disabled_features.append("enhanced-tagger")
        if not self.is_translate_enabled():
            disabled_features.append("enhanced-translate")
        if not self.is_ochiai_enabled():
            disabled_features.append("ochiai-format")
        return disabled_features
    
    def get_summary(self) -> str:
        """現在の設定サマリー"""
        enabled_features = self.get_enabled_features()
        
        if not enabled_features:
            return "AI機能: すべて無効（API利用料金削減モード）"
        elif len(enabled_features) == 3:
            return "AI機能: すべて有効（デフォルト動作）"
        else:
            return f"AI機能: {', '.join(enabled_features)} のみ有効"
    
    def is_development_mode(self) -> bool:
        """開発モード（AI機能制御が適用されている）かチェック"""
        disable_flags = [
            getattr(self.args, 'disable_ai', False),
            getattr(self.args, 'disable_tagger', False),
            getattr(self.args, 'disable_translate', False),
            getattr(self.args, 'disable_ochiai', False)
        ]
        
        enable_only_flags = [
            getattr(self.args, 'enable_only_tagger', False),
            getattr(self.args, 'enable_only_translate', False),
            getattr(self.args, 'enable_only_ochiai', False)
        ]
        
        return any(disable_flags) or any(enable_only_flags)
    
    def get_mode_description(self) -> str:
        """実行モードの説明を取得"""
        if self.is_development_mode():
            return "🔧 開発モード: AI機能制御が適用されています"
        else:
            return "🚀 本番モード: 全機能有効（デフォルト動作）"
    
    def has_api_cost_savings(self) -> bool:
        """API利用料金削減効果があるかチェック"""
        disabled_features = self.get_disabled_features()
        return len(disabled_features) > 0


def get_default_ai_controller():
    """本番環境用のデフォルトAI制御（全機能有効）"""
    return AIFeatureController(argparse.Namespace(
        disable_ai=False,
        disable_tagger=False,
        disable_translate=False,
        disable_ochiai=False,
        enable_only_tagger=False,
        enable_only_translate=False,
        enable_only_ochiai=False
    ))


def parse_ai_feature_arguments():
    """AI機能制御用のコマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description="統合テスト実行")
    
    # AI機能制御オプション（開発用）
    ai_group = parser.add_argument_group('AI機能制御オプション（開発用）')
    ai_group.add_argument('--disable-ai', action='store_true',
                         help='すべてのAI機能を無効化（API利用料金削減）')
    ai_group.add_argument('--disable-tagger', action='store_true',
                         help='enhanced-tagger機能を無効化')
    ai_group.add_argument('--disable-translate', action='store_true',
                         help='enhanced-translate機能を無効化')
    ai_group.add_argument('--disable-ochiai', action='store_true',
                         help='ochiai-format機能を無効化')
    
    # 特定AI機能のみ有効化オプション
    exclusive_group = ai_group.add_mutually_exclusive_group()
    exclusive_group.add_argument('--enable-only-tagger', action='store_true',
                                help='enhanced-tagger機能のみ有効化')
    exclusive_group.add_argument('--enable-only-translate', action='store_true',
                                help='enhanced-translate機能のみ有効化')
    exclusive_group.add_argument('--enable-only-ochiai', action='store_true',
                                help='ochiai-format機能のみ有効化')
    
    return parser.parse_args() 