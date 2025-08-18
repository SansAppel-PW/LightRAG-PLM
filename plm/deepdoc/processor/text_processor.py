
"""
文档内容处理器
根据需求文档规格说明书，将解析得到的JSON结构化数据转换为标准化的文本格式
"""

import os
import re
from typing import Dict, List, Any, Iterable

from loguru import logger

class DocumentProcessor:
    """
    文档内容处理器
    按照需求规格说明书3.1-3.10节的规则处理文档内容
    """

    def __init__(self):
        self.processed_sections = []
        self.image_counter = 0
        self.output_dir = ""  # 添加输出目录属性

    def process_document(self, document_structure: Dict[str, Any], document_name: str, output_dir: str = "") -> str:
        """
        处理完整文档，返回最终的文本格式

        Args:
            document_structure: 解析得到的JSON结构
            document_name: 文档名称
            output_dir: 输出目录路径，用于生成绝对路径

        Returns:
            str: 处理后的标准化文本
        """
        try:
            self.processed_sections = []
            self.image_counter = 0
            self.output_dir = output_dir  # 设置输出目录

            # 获取文档的sections
            sections = document_structure.get("sections", [])
            if not sections:
                logger.warning("文档中没有找到sections")
                return ""

            # 查找根节点
            root_section = None
            for section in sections:
                if section.get("type") == "section" and section.get("level", 0) == 0:
                    root_section = section
                    break

            if not root_section:
                logger.warning("文档中没有找到根节点")
                return ""

            # 获取根节点下的内容
            root_content = root_section.get("content", [])

            # 查找顶级章节（level=1的章节）
            top_level_sections = []
            other_content = []
            for item in root_content:
                if item.get("type") == "section" and item.get("level", 0) == 1:
                    top_level_sections.append(item)
                else:
                    other_content.append(item)

            # 3.1 首页删除：根级别过滤首页封面表格与版本历史表格
            def _is_front_page_table(tbl: Dict[str, Any]) -> bool:
                if tbl.get("type") != "table":
                    return False
                if tbl.get("index", -1) == 0:
                    return True
                if tbl.get("index", -1) == 1:
                    rows = tbl.get("rows", [])
                    if rows and isinstance(rows[0], list) and rows[0]:
                        first_cell = rows[0][0]
                        if isinstance(first_cell, dict):
                            head_text = "".join(
                                itm.get("text", "") for itm in first_cell.get("content", []) if isinstance(itm, dict)
                            ).strip()
                            if head_text == "序号":
                                return True
                return False

            other_content = [c for c in other_content if not _is_front_page_table(c)]

            if not top_level_sections:
                logger.warning("文档中没有找到有效的一级章节")
                # 如果没有一级章节，处理其他内容
                if other_content:
                    content_parts = []
                    for item in other_content:
                        part = self._process_content_item(item)
                        if part:
                            content_parts.append(part)
                    return " ".join(content_parts)
                return ""

            # 提取TOC：空内容的一级章节（content 为空或仅包含空白段落）视为目录项
            toc_sections = []
            real_sections = []
            for s in top_level_sections:
                if self._is_toc_candidate(s):
                    toc_sections.append(s)
                else:
                    real_sections.append(s)

            toc_text = ""
            if toc_sections:
                toc_lines = []
                for ts in toc_sections:
                    raw_title = ts.get("title", "").strip()
                    clean = re.sub(r"\s+\d+\s*$", "", raw_title)  # 去尾部页码
                    # 一级标题
                    m1 = re.match(r"^(\d+)\s+(.*)$", clean)
                    if m1:
                        toc_lines.append(f"# {m1.group(1)} {m1.group(2)}")
                    else:
                        toc_lines.append(f"# {clean}")
                    # 收集其子section（用于二级 TOC）
                    for sub in ts.get("content", []):
                        if sub.get("type") == "section":
                            stitle = re.sub(r"\s+\d+\s*$", "", sub.get("title", "").strip())
                            m2 = re.match(r"^(\d+\.\d+)\s+(.*)$", stitle)
                            if m2:
                                toc_lines.append(f"## {m2.group(1)} {m2.group(2)}")
                            else:
                                m3 = re.match(r"^(\d+\.\d+\.\d+)\s+(.*)$", stitle)
                                if m3:
                                    toc_lines.append(f"### {m3.group(1)} {m3.group(2)}")
                                else:
                                    toc_lines.append(f"## {stitle}")
                if toc_lines:
                    # toc_text = "\n".join(toc_lines) + "\n\n\\n\\n\n\n"
                    # toc_text = "".join(toc_lines) + "\\n\\n"
                    # toc_text = "".join(toc_lines)
                    toc_text = "<|TOC|>"+"".join(toc_lines)+"</|TOC|>"
            else:
                real_sections = top_level_sections
            if not real_sections:
                real_sections = top_level_sections

            # 按占位目录章节顺序重排正文章节，使编号与TOC一致
            if toc_sections and real_sections:
                def _norm_title(t: str) -> str:
                    t = re.sub(r"\s+\d+\s*$", "", t.strip())  # 去尾部页码
                    t = re.sub(r"^\d+(?:\.\d+)*\s+", "", t)  # 去前缀编号
                    return t.strip()

                # 取有实际内容的 real_sections 作为候选
                content_candidates = list(real_sections)
                used_ids = set()
                ordered_real: List[Dict[str, Any]] = []

                # 对 toc_sections 中的一级编号章节按数字序维持原出现顺序
                for placeholder in toc_sections:
                    p_norm = _norm_title(placeholder.get("title", ""))
                    match_idx = -1
                    for idx, sec in enumerate(content_candidates):
                        if idx in used_ids:
                            continue
                        if _norm_title(sec.get("title", "")) == p_norm:
                            match_idx = idx
                            break
                    if match_idx >= 0:
                        ordered_real.append(content_candidates[match_idx])
                        used_ids.add(match_idx)
                # 追加未匹配的剩余章节（保持原顺序）
                for idx, sec in enumerate(content_candidates):
                    if idx not in used_ids:
                        ordered_real.append(sec)
                real_sections = ordered_real

            # 处理每个顶级章节
            final_text_parts = []

            for i, section in enumerate(real_sections):
                section_text = self._process_top_level_section(section, document_name, i + 1)
                if section_text.strip():
                    # 在每个一级章节末尾追加：真实双换行 + 字面分隔符 + 真实双换行
                    # final_text_parts.append(section_text.strip() + "\n\n\\n\\n\n\n")
                    # final_text_parts.append(section_text.strip() + "\\n\\n")
                    final_text_parts.append(section_text.strip())

            # 组合 TOC 与章节
            final_text = (toc_text + "".join(final_text_parts)).rstrip()

            return final_text

        except Exception as e:
            logger.error(f"处理文档时发生错误: {e}")
            return ""

    def _process_top_level_section(self, section: Dict[str, Any], document_name: str, section_index: int) -> str:
        """
        处理顶级章节（一级章节）

        Args:
            section: 章节数据
            document_name: 文档名称
            section_index: 章节序号

        Returns:
            str: 处理后的章节文本
        """
        try:
            title = section.get("title", "").strip()
            content = section.get("content", [])

            if not title:
                logger.warning(f"章节 {section_index} 没有标题")
                return ""

            # 清理标题：移除末尾页码数字，并去除开头重复编号避免与section_index重复
            import re
            clean_title = re.sub(r'\s+\d+\s*$', '', title)
            title_no_prefix = re.sub(r'^\d+(?:\.\d+)*\s+', '', clean_title).strip() or clean_title
            title_lower = clean_title.lower()

            # 3.1 删除首页 - 跳过处理
            if self._should_skip_first_page(section, section_index):
                logger.info(f"跳过首页章节: {title}")
                return ""

            # 3.2 目录页处理
            if self._is_toc_section(clean_title):
                toc_md = self._process_toc_section(content)
                return toc_md if toc_md else ""

            # 3.3 流程示意图处理
            if self._is_flow_diagram_section(clean_title):
                return self._process_flow_diagram_section(title_no_prefix, content, document_name, section_index)

            # 3.4 流程模板处理
            if self._is_template_section(clean_title):
                return self._process_template_section(title_no_prefix, content, document_name, section_index)

            # 3.5 流程节点功能描述处理 / 3.9 接口处理 / 3.10 其他内容处理
            return self._process_general_section(title_no_prefix, content, document_name, section_index)

        except Exception as e:
            logger.error(f"处理顶级章节时发生错误: {e}")
            return ""

    def _should_skip_first_page(self, section: Dict[str, Any], section_index: int) -> bool:
        """
        检查是否应该跳过首页内容（3.1节规则）
        """
        # 检查是否是第一个表格
        content = section.get("content", [])
        if section_index == 1 and content:
            first_item = content[0]
            if first_item.get("type") == "table" and first_item.get("index", 0) == 0:
                return True

            # 检查是否是版本历史表格
            if (first_item.get("type") == "table" and
                    first_item.get("index", 0) == 1):
                rows = first_item.get("rows", [])
                if rows and len(rows) > 0:
                    first_row = rows[0]
                    if (isinstance(first_row, list) and len(first_row) > 0 and
                            isinstance(first_row[0], dict) and
                            first_row[0].get("content", {}).get("text", "") == "序号"):
                        return True

        return False

    def _is_toc_section(self, title: str) -> bool:
        """判断是否是目录章节"""
        title_lower = title.lower()
        toc_keywords = ["目录", "contents", "content", "索引", "index"]
        return any(keyword in title_lower for keyword in toc_keywords)

    def _is_flow_diagram_section(self, title: str) -> bool:
        """判断是否是流程示意图章节
        只有完全匹配关键字（流程示意图/流程图/示意图），且不是纯目录占位的数字开头形式才认为是正文章节。
        """
        if re.match(r'^\d+\s+.*', title):  # 数字开头的留给目录候选逻辑
            return False
        return any(kw in title for kw in ["流程示意图", "流程图", "示意图"])  # 中文为主

    def _is_template_section(self, title: str) -> bool:
        """判断是否是模板章节"""
        title_lower = title.lower()
        template_keywords = ["模板", "template", "表单", "form"]
        return any(keyword in title_lower for keyword in template_keywords)

    def _is_interface_section(self, title: str) -> bool:
        """判断是否是接口章节 (3.9)"""
        title_lower = title.lower()
        interface_keywords = ["接口", "api", "接口说明"]
        return any(keyword in title_lower for keyword in interface_keywords)

    def _process_toc_section(self, content: List[Dict[str, Any]]) -> str:
        """
        处理目录页（3.2节规则）
        转换为Markdown层级标题格式
        """
        try:
            toc_lines = []
            toc_lines.append("<|CHAPTER|>")
            for item in content:
                if item.get("type") == "paragraph":
                    text = item.get("text", "").strip()
                    if text and not self._is_page_number(text):
                        # 尝试解析章节结构
                        toc_line = self._parse_toc_line(text)
                        if toc_line:
                            toc_lines.append(toc_line)
                elif item.get("type") == "section":
                    # 递归处理子章节
                    sub_toc = self._process_toc_section(item.get("content", []))
                    if sub_toc:
                        toc_lines.append(sub_toc)
            toc_lines.append("</|CHAPTER|>")
            # 目录与其它章节之间仍按双换行逻辑分隔，目录自身不追加多余空白
            # return "\n".join(toc_lines) if toc_lines else ""
            return "".join(toc_lines) if toc_lines else ""

        except Exception as e:
            logger.error(f"处理目录章节时发生错误: {e}")
            return ""

    def _parse_toc_line(self, text: str) -> str:
        """
        解析目录行，转换为Markdown格式
        """
        try:
            # 移除末尾页码（通常在行末的独立数字）
            text = re.sub(r'\s+\d+\s*$', '', text)

            # 捕获编号+标题
            m3 = re.match(r'^(?P<num>\d+\.\d+\.\d+)\s+(?P<title>.+)$', text)
            if m3:
                return f"### {m3.group('num')} {m3.group('title').strip()}"
            m2 = re.match(r'^(?P<num>\d+\.\d+)\s+(?P<title>.+)$', text)
            if m2:
                return f"## {m2.group('num')} {m2.group('title').strip()}"
            m1 = re.match(r'^(?P<num>\d+)\s+(?P<title>.+)$', text)
            if m1:
                return f"# {m1.group('num')} {m1.group('title').strip()}"
            # 没有明确数字前缀时按一级处理
            return f"# {text.strip()}"

        except Exception as e:
            logger.error(f"解析目录行时发生错误: {e}")
            return f"# {text}"

    def _is_page_number(self, text: str) -> bool:
        """判断是否是页码"""
        return bool(re.match(r'^\d+$', text.strip()))

    def _process_flow_diagram_section(self, title: str, content: List[Dict[str, Any]],
                                      document_name: str, section_index: int) -> str:
        """
        处理流程示意图章节（3.3节规则）
        """
        try:
            section_title = f"{document_name}-{section_index} {title}："
            content_parts = []

            for part in self._iterate_merged_content(content):
                if part:
                    content_parts.append(part)

            if content_parts:
                # return section_title + "\n" + " ".join(content_parts)
                return section_title + "\n" + "。".join(content_parts)
            else:
                return section_title

        except Exception as e:
            logger.error(f"处理流程示意图章节时发生错误: {e}")
            return ""

    def _process_template_section(self, title: str, content: List[Dict[str, Any]],
                                  document_name: str, section_index: int) -> str:
        """
        处理流程模板章节（3.4节规则）
        """
        try:
            section_title = f"{document_name}-{section_index} {title}："
            content_parts = []

            for part in self._iterate_merged_content(content):
                if part:
                    content_parts.append(part)

            if content_parts:
                # return section_title + "\n" + " ".join(content_parts)
                return "<|CHAPTER|>"+section_title + "".join(content_parts)+"</|CHAPTER|>"
            else:
                return "<|CHAPTER|>"+section_title+"</|CHAPTER|>"

        except Exception as e:
            logger.error(f"处理流程模板章节时发生错误: {e}")
            return ""

    def _process_general_section(self, title: str, content: List[Dict[str, Any]],
                                 document_name: str, section_index: int) -> str:
        """
        处理一般章节（3.5、3.9、3.10节规则）
        包含二级章节的用SECTION标签包裹
        """
        try:
            normalized_title = "接口" if self._is_interface_section(title) else title
            section_title = f"{document_name}-{section_index} {normalized_title}："

            # 检查是否包含二级章节
            subsections = [item for item in content if item.get("type") == "section"]

            if subsections:
                # 包含二级章节，使用SECTION标签格式
                section_parts = []

                flat_subsections = self._flatten_subsections(subsections)
                for idx, (sub_obj, numbering) in enumerate(flat_subsections, 1):
                    subsection_block = self._process_subsection(
                        sub_obj, document_name, section_index, numbering, title
                    )
                    if subsection_block:
                        section_parts.append(subsection_block)

                if section_parts:
                    # return section_title + "\n" + "\n".join(section_parts)
                    return "<|CHAPTER|>"+section_title + "".join(section_parts)+"</|CHAPTER|>"
                else:
                    # return section_title
                    return "<|CHAPTER|>"+section_title+"</|CHAPTER|>"
            else:
                # 没有二级章节，直接处理内容
                content_parts = []
                for part in self._iterate_merged_content(content):
                    if part:
                        # 直接内容保持单行形式
                        content_parts.append(part)

                if content_parts:
                    # return section_title + "\n" + " ".join(content_parts)
                    return "<|CHAPTER|>"+section_title + "".join(content_parts)+"</|CHAPTER|>"
                else:
                    # return section_title
                    return "<|CHAPTER|>" + section_title + "</|CHAPTER|>"

        except Exception as e:
            logger.error(f"处理一般章节时发生错误: {e}")
            return ""

    def _process_subsection(self, subsection: Dict[str, Any], document_name: str,
                            section_index: int, subsection_number: str, top_level_title: str) -> str:
        """
        处理二级章节（3.6节规则）
        """
        try:
            subsection_title = subsection.get("title", "").strip()
            subsection_content = subsection.get("content", [])

            clean_title = re.sub(r'\s+\d+\s*$', '', subsection_title)

            # subsection_number 已包含如 3.1 或 3.1.1
            # 如果 clean_title 以 subsection_number 开头，拆分以编号后的空格
            display_title = clean_title
            if clean_title.startswith(subsection_number):
                # 保留原格式
                display_title = clean_title
            # 构建二级/三级章节标题
            full_title = f"{document_name}-{section_index} {top_level_title}-{display_title}："

            # 收集内容行（逐行，不再拼成单行，便于缩进）
            lines: List[str] = []
            for part in self._iterate_merged_content(subsection_content):
                if part:
                    # _iterate_merged_content 可能返回多行（如表格），直接拆分
                    for ln in part.splitlines():
                        if ln.strip():
                            lines.append(ln.rstrip())

            # 构造 SECTION 块（带缩进）
            block_lines = ["<|SECTION|>"]
            # block_lines.append(f"    {full_title}")
            block_lines.append(f"{full_title}")
            for ln in lines:
                block_lines.append("    " + ln)
            block_lines.append("</|SECTION|>")
            # return "\n".join(block_lines)
            return "".join(block_lines)

        except Exception as e:
            logger.error(f"处理二级章节时发生错误: {e}")
            return ""

    def _process_content_item(self, item: Dict[str, Any]) -> str:
        """
        处理具体内容项（3.7节规则）
        """
        try:
            item_type = item.get("type", "")

            if item_type == "paragraph":
                text = item.get("text", "").strip()
                if text:
                    # return f"<|PARAGRAPH|>{text}</|PARAGRAPH|>\n"
                    return text

            elif item_type == "list_item":
                text = item.get("text", "").strip()
                if text:
                    # return f"<|LISTITEM|>{text}</|LISTITEM|>\n"
                    return text

            elif item_type == "table":
                tbl = self._process_table(item)
                return tbl + ("\n" if tbl else "")

            elif item_type == "image":
                img = self._process_image(item)
                # return img + ("\n" if img else "")
                return img

            return ""

        except Exception as e:
            logger.error(f"处理内容项时发生错误: {e}")
            return ""

    def _process_table(self, table_item: Dict[str, Any]) -> str:
        """
        处理表格（3.8节规则）
        """
        try:
            rows = table_item.get("rows", [])
            if not rows:
                return ""

            # row_entries: (first_col_value, row_markup)
            row_entries: List[tuple] = []

            # 获取表头（通常是第一行）
            headers = []
            if rows:
                first_row = rows[0]
                if isinstance(first_row, list):
                    for cell in first_row:
                        if isinstance(cell, dict):
                            # 提取单元格内容
                            content = cell.get("content", [])
                            text_parts = []
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", "").strip())
                            text = " ".join(text_parts).strip()
                            headers.append(text)
                        else:
                            headers.append(str(cell).strip())

            # 处理数据行（跳过表头）
            for i, row in enumerate(rows[1:], 1):
                if not isinstance(row, list):
                    continue
                row_data = []
                first_col_val = ""
                for j, cell in enumerate(row):
                    if isinstance(cell, dict):
                        content = cell.get("content", [])
                        text_parts = [itm.get("text", "").strip() for itm in content if
                                      isinstance(itm, dict) and itm.get("type") == "text"]
                        text = " ".join(t for t in text_parts if t).strip()
                    else:
                        text = str(cell).strip()
                    if j == 0:
                        first_col_val = text
                    if j < len(headers) and headers[j]:
                        formatted_cell = f"{headers[j]}:{text}"
                    else:
                        formatted_cell = f"列{j + 1}:{text}"
                    row_data.append(formatted_cell)
                if row_data:
                    row_markup = f"<|ROW|>|{'|'.join(row_data)}|</|ROW|>"
                    row_entries.append((first_col_val, row_markup))

            # 基于首列值连续相同分组 -> RSPAN，并应用层级缩进：
            # <|TABLE|>
            #     <|RSPAN|>
            #         <|ROW|>...
            #     </|RSPAN|>
            # </|TABLE|>
            table_lines: List[str] = ["<|TABLE|>"]
            idx = 0
            while idx < len(row_entries):
                cur_val, cur_row = row_entries[idx]
                group = [cur_row]
                j = idx + 1
                while j < len(row_entries) and row_entries[j][0] == cur_val and cur_val:
                    group.append(row_entries[j][1])
                    j += 1
                if len(group) > 1:
                    # table_lines.append("    <|RSPAN|>")
                    table_lines.append("<|RSPAN|>")
                    for gr in group:
                        # table_lines.append("        " + gr)
                        table_lines.append("" + gr)
                    # table_lines.append("    </|RSPAN|>")
                    table_lines.append("</|RSPAN|>")
                else:
                    # table_lines.append("    " + group[0])
                    table_lines.append("" + group[0])
                idx = j

            table_lines.append("</|TABLE|>")
            # return "\n".join(table_lines) if len(table_lines) > 2 else ""
            return "".join(table_lines) if len(table_lines) > 2 else ""

        except Exception as e:
            logger.error(f"处理表格时发生错误: {e}")
            return ""

    def _process_image(self, image_item: Dict[str, Any]) -> str:

        """
        处理图片，转换为标准化格式，使用绝对路径
        """
        image_path = image_item.get("path", "")
        return f"<|IMAGE|>{image_path}</|IMAGE|>"
        # try:
        #     # 从图片项中获取信息
        #     image_path = image_item.get("path", "")
        #     image_url = image_item.get("url", "")
        #
        #     # 生成绝对路径
        #     if image_url:
        #         # 使用url字段（这是主要的图片路径）
        #         if os.path.isabs(image_url):
        #             abs_path = image_url
        #         else:
        #             # 转换为绝对路径
        #             if self.output_dir:
        #                 abs_path = os.path.abspath(os.path.join(self.output_dir, image_url))
        #             else:
        #                 abs_path = os.path.abspath(image_url)
        #         # image_info = f"![image]({abs_path})"
        #         image_info = abs_path
        #     elif image_path:
        #         # 备用的path字段
        #         if os.path.isabs(image_path):
        #             abs_path = image_path
        #         else:
        #             # 转换为绝对路径
        #             if self.output_dir:
        #                 abs_path = os.path.abspath(os.path.join(self.output_dir, image_path))
        #             else:
        #                 abs_path = os.path.abspath(image_path)
        #         # image_info = f"![image]({abs_path})"
        #         image_info = abs_path
        #     else:
        #         self.image_counter += 1
        #         # 生成默认图片的绝对路径
        #         if self.output_dir:
        #             abs_path = os.path.abspath(
        #                 os.path.join(self.output_dir, f"images/image_{self.image_counter:03d}.png"))
        #         else:
        #             abs_path = os.path.abspath(f"./images/image_{self.image_counter:03d}.png")
        #         # image_info = f"![image]({abs_path})"
        #         image_info = abs_path
        #
        #     # 使用IMAGE标签包裹
        #     return f"<|IMAGE|>{image_info}</|IMAGE|>"
        #
        # except Exception as e:
        #     logger.error(f"处理图片时发生错误: {e}")
        #     return ""

    # ----------------- 新增辅助方法 -----------------
    def _iterate_merged_content(self, content: List[Dict[str, Any]]) -> Iterable[str]:
        """遍历内容并合并连续 paragraph 为单个 PARAGRAPH 标签 (3.7 合并规则)。"""
        buffer: List[str] = []
        for item in content:
            if item.get("type") == "paragraph":
                text = item.get("text", "").strip()
                if text:
                    buffer.append(text)
                continue
            # 遇到非 paragraph，先输出累积的段落
            if buffer:
                yield f"<|PARAGRAPH|>{' '.join(buffer)}</|PARAGRAPH|>"
                buffer = []
            # 处理当前项目
            yield self._process_content_item(item)
        if buffer:
            yield f"<|PARAGRAPH|>{' '.join(buffer)}</|PARAGRAPH|>"

    def _flatten_subsections(self, subsections: List[Dict[str, Any]]) -> List[tuple]:
        r"""将多级 subsection 展平为 (subsection_obj, 编号) 列表。
        编号从原 title 前缀获取（匹配 ^\d+(?:\.\d+)+）。
        """
        flat: List[tuple] = []
        for sub in subsections:
            title = sub.get("title", "").strip()
            number_match = re.match(r'^(\d+(?:\.\d+)+)', title)
            number = number_match.group(1) if number_match else ''
            flat.append((sub, number))
            # 查找更深层 section
            child_sections = [c for c in sub.get("content", []) if c.get("type") == "section"]
            if child_sections:
                flat.extend(self._flatten_subsections(child_sections))
        return flat

    # ----------------- 目录判定辅助 -----------------
    def _section_has_meaningful_content(self, section: Dict[str, Any]) -> bool:
        """判断 section 自身(直接内容)是否包含实际可视内容(段落文字/列表/表格/图片)。"""
        for item in section.get("content", []):
            t = item.get("type")
            if t == "paragraph" and item.get("text", "").strip():
                return True
            if t in {"list_item", "table", "image"}:
                # table 需有行; image 直接算内容
                if t == "table" and item.get("rows"):
                    return True
                if t in {"list_item", "image"}:
                    return True
        return False

    def _is_toc_candidate(self, section: Dict[str, Any]) -> bool:
        """判断一级章节是否应作为目录行:
        1) 自身无内容(空 content)
        2) 或 自身只包含子 section 且这些子 section 也无实际内容
        """
        content = section.get("content", [])
        if not content:
            return True
        # 若有任何非 section 的元素且有意义内容 -> 非目录
        has_non_section_meaning = any(
            (itm.get("type") != "section" and (
                    (itm.get("type") == "paragraph" and itm.get("text", "").strip()) or
                    itm.get("type") in {"list_item", "image"} or
                    (itm.get("type") == "table" and itm.get("rows"))
            ))
            for itm in content
        )
        if has_non_section_meaning:
            return False
        # 若全是子 section，且所有子 section 都无实际内容 -> 目录
        if all(itm.get("type") == "section" for itm in content):
            if all(not self._section_has_meaningful_content(itm) for itm in content):
                return True
        return False


def process_document_to_text(document_structure: Dict[str, Any], document_name: str, output_dir: str = "") -> str:
    """
    将解析得到的文档结构转换为标准化文本格式

    Args:
        document_structure: 解析得到的JSON结构
        document_name: 文档名称（不包含扩展名）
        output_dir: 输出目录路径，用于生成绝对路径

    Returns:
        str: 处理后的标准化文本
    """
    processor = DocumentProcessor()
    return processor.process_document(document_structure, document_name, output_dir)
