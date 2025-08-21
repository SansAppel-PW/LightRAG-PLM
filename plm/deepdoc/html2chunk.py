import uuid
from pathlib import Path

from bs4 import BeautifulSoup, Tag, NavigableString
import re
from typing import List, Dict, Tuple, Optional, Any

import lxml
from transformers import AutoTokenizer

from lightrag.utils import Tokenizer
from plm.conf.settings import llm_settings

from plm.deepdoc.utils.image_utils import convert_emf_to_png
from loguru import logger
import json

class ChunkNode:
    """表示分块树中的节点"""

    def __init__(self, node_id: str, level: int, title: str = "", text="", doc_date="", metadata: dict = None,
                 parent_id: str = None):
        self.id = node_id
        self.level = level
        self.title = title
        self.text = text
        self.doc_date = doc_date
        self.metadata = metadata or {}
        self.parent_id = parent_id
        self.token_count = 0

    def to_dict(self) -> dict:
        """ 转换为字典格式，便于存储 """
        return {
            "id": self.id,
            "level": self.level,
            "text": self.text,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "token_count": self.token_count
        }


class HTMLChunker:
    def __init__(self, tokenizer: Tokenizer, content: str, html_path):
        self.html_path = html_path
        self.nodes = []  # 存储所有节点
        self.current_parent_stack = []  # 跟踪当前父节点id
        self.encoder = tokenizer  # qwen3
        self.doc_name = Path(html_path).stem

        # 创建根节点
        root_node = ChunkNode(
            node_id="root",
            level=0,
            title="Document Root",
            metadata={"source": html_path}
        )
        self.nodes.append(root_node)
        self.current_parent_stack.append('root')  # 初始化当前父节点

        # 读取并解析HTML
        # 使用lxml解析器读取并解析HTML

        # 使用lxml解析器，比标准html.parser更快更健壮
        self.soup = BeautifulSoup(content, 'lxml')

        # 预处理：移除不需要的元素
        for element in self.soup(['script', 'style', 'noscript', 'footer', 'header']):
            element.decompose()

    def count_tokens(self, text: str) -> int:
        """ 计算文本token数量 """
        return len(self.encoder.encode(text))

    def recursive_process(self, element: Tag):
        """ 递归处理 HTML 元素 """
        # 获取当前父节点ID
        current_parent_id = self.current_parent_stack[-1] if self.current_parent_stack  else "root"

        # 处理标题元素
        if element.name and element.name.startswith('h'):
            heading_level = int(element.name[1])

            # 更新当前父节点栈
            # 移除层级相同或更低的标题
            while self.current_parent_stack:
                top_node = self.get_node_by_id(self.current_parent_stack[-1])
                if top_node.level >= heading_level:
                    self.current_parent_stack.pop()
                else:
                    break

            current_parent_id = self.current_parent_stack[-1] if self.current_parent_stack  else "root"

            heading_text = element.get_text().strip()
            # 创建新的标题节点
            new_node = ChunkNode(
                node_id=f"h{heading_level}_{uuid.uuid4().hex}",
                level=min(heading_level, 3),
                title=self.doc_name + '-' + heading_text,
                text=self.doc_name + '-' + heading_text,
                metadata={"source": self.html_path},
                parent_id=current_parent_id
            )
            self.nodes.append(new_node)


            # 将新节点设为当前父节点
            self.current_parent_stack.append(new_node.id)
            current_parent_id = new_node.id

            # 处理标题内部内容
            for child in element.children:
                if isinstance(child, Tag):
                    self.recursive_process(child)

            # 处理标题后内容
            # for sibling in element.next_siblings:
            #     # if not isinstance(sibling, Tag) or sibling.name.startswith('h'):
            #     #     break  # 遇到下一个标题退出
            #     if isinstance(sibling, Tag):
            #         if sibling.name.startswith('h'): break
            #         self.recursive_process(sibling)

            return
        # 处理内容元素
        content_text, images = self.extract_content(element)
        if content_text:
            # 获取当前父节点
            parent_node = self.get_node_by_id(current_parent_id)
            if parent_node:
                # 添加内容到当前父节点的文本
                if parent_node.text:
                    # parent_node.text += "\n\n" + content_text
                    parent_node.text += "。" + content_text
                else:
                    parent_node.text = '。' + content_text # 节点初始化时有文档名-章节名，所以需要加句号
                # 更新token计数
                parent_node.token_count = self.count_tokens(parent_node.text)
                # 添加图片到元数据
                if images:
                    if "images" not in parent_node.metadata:
                        parent_node.metadata["images"] = []
                    parent_node.metadata["images"].extend(images)

        # 递归处理子元素
        # for child in element.children:
        #     if isinstance(child, Tag):
        #         self.recursive_process(child)

    def get_node_by_id(self, node_id: str) -> Optional[ChunkNode]:
        """根据 id 查找节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def extract_content(self, element: Tag) -> Tuple[str, list]:
        """ 提取元素内容， 返回文本和图片列表 """
        if isinstance(element, NavigableString):
            text = re.sub(r'\s+', ' ', element.strip())
            return text, []

        content_parts = []
        images = []

        # 处理子元素
        if element.name == 'table':
            table_text, table_images = self.process_table(element)
            content_parts.append(table_text)
            images.extend(table_images)
        elif element.name == 'img':
            alt = element.get('alt', '').strip()
            title = element.get('title', '').strip()
            img_url = element.get('src', '').strip()
            # 章节名称
            section_name = self.get_section_name()
            img_desc = self.doc_name + '-' + section_name + '-' + alt or title or "图片"
            # TODO: 保存图片，并将图片地址添加到images中
            # 这里images中存放的是图片的中文描述
            images.append(f"[图：{img_desc}]({img_url})")
            content_parts.append(f"[图：{img_desc}]({img_url})")
        elif element.name in ['p', 'div', 'section', 'article', 'li', 'ul', 'ol']:
            # 递归处理标题、段落和列表项
            for child in element.children:
                if isinstance(child, (Tag, NavigableString)):
                    child_text, child_images = self.extract_content(child)
                    if child_text:
                        content_parts.append(child_text)
                    if child_images:
                        images.extend(child_images)
        else:
            # 递归处理其他容器元素
            text = element.get_text().strip()
            if text:
                content_parts.append(text)

        return '\n'.join(content_parts), images

    def get_section_name(self):
        current_parent_id = self.current_parent_stack[-1] if self.current_parent_stack else "root"
        parent_node = self.get_node_by_id(current_parent_id)
        return parent_node.title or ""

    def process_table(self, table: Tag) -> Tuple[str, list]:
        """ 处理表格为行序列化格式 """
        rows = table.find_all(['tr', 'thead', 'tbody'], recursive=False)
        headers = []
        table_text = []
        table_images = []

        # 章节名称
        # current_parent_id = self.current_parent_stack[-1] if self.current_parent_stack  else "root"
        # parent_node = self.get_node_by_id(current_parent_id)
        # section_name = parent_node.title

        # 处理表头
        for row in rows:
            if row.name == 'thead' or (not headers and row.name == 'tr'):
                header_cells = row.find_all(['th', 'td'])
                if header_cells:
                    headers = [self.process_cell(cell, table_images) for cell in header_cells]
                    continue
        # 处理数据行
        for i, row in enumerate(rows):
            if headers and i==0:
                continue
            if row.name in ['tr', 'tbody']:
                tbody_rows = [row] if row.name == 'tr' else row.find_all('tr', recursive=False)
                for data_row in tbody_rows:
                    data_cells = data_row.find_all(['th', 'td'])
                    if not data_cells:
                        continue
                    cell_values = [self.process_cell(cell, table_images) for cell in data_cells]
                    row_entries = []
                    for i, value in enumerate(cell_values):
                        header = self.doc_name + '-' + headers[i] if i<len(headers) else f"列{i+1}"
                        # header = headers[i] if i < len(headers) else ""
                        if value:
                            # 替换逗号避免冲突
                            clean_value = value.replace(',', '，')  # 下面使用；隔开行单元格，所以不冲突，该行注释掉也可
                            row_entries.append(f"{header}:{clean_value}")
                    if row_entries:
                        table_text.append('；'.join(row_entries))
        return '。'.join(table_text) + '。', table_images

    def process_cell(self, cell: Tag, image_list: list) -> str:
        """ 处理单元格内容， 返回文本并提取图片 """
        cell_text = []
        for content in cell.contents:
            if isinstance(content, NavigableString):
                clean_text = re.sub(r'\s+', ' ', content.strip())
                if clean_text:
                    cell_text.append(clean_text)
            elif isinstance(content, Tag):
                if content.name == 'img':
                    alt = content.get('alt', '').strip()
                    title = content.get('title', '').strip()
                    src = content.get('src','').strip()
                    # 章节名称
                    section_name = self.get_section_name()
                    img_desc = self.doc_name + '-' + section_name + '-' + alt or title or "图片"
                    if img_desc:
                        image_list.append(f"[图：{img_desc}]({src})")
                        cell_text.append(f"[图：{img_desc}]({src})")
                else:
                    child_text, _ = self.extract_content(content)
                    if child_text:
                        cell_text.append(child_text)
        return ''.join(cell_text).strip()

    def build_chunk_tree(self):
        """ 构建分层分块树 """
        # 从文档 body 开始递归处理
        if self.soup.body:
            for child in self.soup.body.children:
                if isinstance(child, Tag):
                    self.recursive_process(child)

    def get_full_text(self, node_id: str):
        """ 从节点创建该节点下所有节点的完整文本 """
        node = self.get_node_by_id(node_id)
        if not node:
            return ""
        full_text = ""
        if node.title:
            full_text += f"{'#' * node.level} {node.title} \n\n"

        full_text += node.text

        # 添加直接子节点内容
        children = [n for n in self.nodes if n.parent_id == node_id]
        for child in children:
            full_text += "\n\n" + self.get_full_text(child.id)
        return full_text.strip()

    def save_to_database(self):
        """ 将分块树保存到数据库 """

        for node in self.nodes:
            # 跳过根节点
            if node.level==0:
                continue
            # 向量化节点内容
            vector = self.vectorize_node(node)

            db_record = {
                "id": node.id,
                "vector": vector,
                "level": node.level,
                "title": node.title,
                "text": node.text,
                "token_count":node.token_count,
                "parent_id": node.parent_id,
                "metadata": node.metadata
            }

            # database.insert(db_record)
            logger.info(f"保存节点： L{node.level} {node.title or node.id} (父ID:{node.parent_id}, Tokens:{node.token_count})")


    def vectorize_node(self, node:ChunkNode)->list:
        """ 向量化 节点内容 """
        return []

    def save_to_local(self, output_path):
        """ 将分块树保存到数据库 """
        with open(output_path, "w", encoding='utf-8') as f:
            for node in self.nodes:
                # 跳过根节点
                if node.level == 0:
                    continue
                # 向量化节点内容
                vector = self.vectorize_node(node)

                db_record = {
                    "id": node.id,
                    "vector": vector,
                    "level": node.level,
                    "title": node.title,
                    "text": node.text,
                    "token_count": node.token_count,
                    "parent_id": node.parent_id,
                    "metadata": node.metadata
                }
                f.write(json.dumps(db_record, ensure_ascii=False) + '\n')
                # database.insert(db_record)
                logger.info(
                    f"保存节点： L{node.level} {node.title or node.id} (父ID:{node.parent_id}, Tokens:{node.token_count})")

    def convert_to_dict_list(self):
        pattern = r'完成日期[：:]\s*(\d{4}-\d{2}-\d{2})'
        chunk_list = []
        for index, node in enumerate(self.nodes):
            # 跳过根节点
            if node.level == 0:
                if match_date:=re.search(pattern, node.text):
                    node.doc_date = match_date
                continue

            chunk_record = {
                # 原始lightrag需要保存的字段
                "tokens": node.token_count,
                "content": node.text,
                "chunk_order_index": index,
                # 下面是自定义字段
                "id": node.id,
                "vector": [],
                "level": node.level,
                "title": node.title,
                # "text": node.text,
                "doc_date": node.doc_date,
                # "token_count": node.token_count,
                "parent_id": node.parent_id,
                "metadata": node.metadata
            }
            chunk_list.append(chunk_record)
        return chunk_list

def custom_chunking(
    tokenizer: Tokenizer,
    content: str,
    split_by_character: str | None = None,
    split_by_character_only: bool = False,
    overlap_token_size: int = 128,
    max_token_size: int = 1024,
    file_path: str=''
) -> list[dict[str, Any]]:
    chunker = HTMLChunker(tokenizer, content, file_path)
    chunker.build_chunk_tree()
    chunk_list = chunker.convert_to_dict_list()
    logger.info('-----------------chunk list-----------------')
    logger.info(f'{chunk_list}')
    logger.info('--------------------------------------------')
    return chunk_list


if __name__=="__main__":
    qwen3_tokenizer = AutoTokenizer.from_pretrained(llm_settings.HIK_MAAS_TOKENIZER.get_secret_value())  # local tokenizer

    input_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output\mammoth\BOM 审核申请\BOM 审核申请_final.html"
    output_path = "output_BOM.jsonl"

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    custom_chunking(tokenizer=qwen3_tokenizer, content=content)
