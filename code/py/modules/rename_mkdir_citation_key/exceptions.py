"""
Rename & MkDir Citation Key専用例外クラス
"""

from ..shared.exceptions import ObsClippingsError


class RenameOrganizeError(ObsClippingsError):
    """Rename & MkDir機能専用例外の基底クラス"""
    pass


class FileMatchingError(RenameOrganizeError):
    """ファイル照合エラー"""
    def __init__(self, message: str, filename: str = None, similarity_score: float = None):
        super().__init__(message)
        self.filename = filename
        self.similarity_score = similarity_score


class DirectoryOperationError(RenameOrganizeError):
    """ディレクトリ操作エラー"""
    def __init__(self, message: str, directory_path: str = None, operation: str = None):
        super().__init__(message)
        self.directory_path = directory_path
        self.operation = operation


class TitleSyncError(RenameOrganizeError):
    """タイトル同期エラー"""
    def __init__(self, message: str, file_path: str = None, bib_title: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.bib_title = bib_title


class YAMLUpdateError(RenameOrganizeError):
    """YAML frontmatter更新エラー"""
    def __init__(self, message: str, file_path: str = None):
        super().__init__(message)
        self.file_path = file_path 