from abc import ABC, abstractmethod


class BaseParser(ABC):

    @abstractmethod
    def __init__(self, *args, **kwargs):
        self.file_path = None
        self.doc_name = None
        self.headings = BaseParser.extract_headings(*args, **kwargs)

    # @staticmethod
    # @abstractmethod
    # def execute_build_catalog(*args, **kwargs):
    #     ...
    #
    # @staticmethod
    # @abstractmethod
    # def extract_headings(*args, **kwargs):
    #     ...
    #
    # @abstractmethod
    # def paragraph_transform(self, *args, **kwargs):
    #     pass
    #
    # @abstractmethod
    # def find_image_positions(self):
    #     ...
    #
    # @abstractmethod
    # def find_table_positions(self):
    #     ...
    #
    # @abstractmethod
    # def extract_tables_as_html(self) -> list[str]:
    #     ...
    #
    # @abstractmethod
    # def extract_images_as_obj(self, *agrs, **kwargs):
    #     pass
