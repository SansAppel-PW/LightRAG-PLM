"""
文档解析器核心模块
"""

import logging
import os
import shutil
import tempfile
import traceback
from collections import defaultdict, deque
from datetime import datetime

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from plm.deepdoc.extractor.content_extractor import extract_paragraph_content
from plm.deepdoc.parser.table_parser import parse_table
from plm.deepdoc.utils.document_utils import iter_block_items
# 导入模块化组件
from plm.deepdoc.utils.text_utils import clean_text, get_heading_level, is_list_item, get_list_info

logger = logging.getLogger(__name__)

def extract_metadata(doc, docx_path):
    """提取文档元数据"""
    try:
        core_props = doc.core_properties
        return {
            "source_path": docx_path,
            "title": core_props.title,
            "author": core_props.author,
            "created": str(core_props.created),
            "modified": str(core_props.modified),
            "subject": core_props.subject,
            "keywords": core_props.keywords,
            "category": core_props.category,
            "comments": core_props.comments,
            "company": getattr(core_props, "company", "N/A"),
            "file_size": f"{os.path.getsize(docx_path)/1024:.2f} KB"
        }
    except Exception as e:
        logger.warning(f"提取元数据失败: {e}")
        return {
            "error": f"Failed to extract metadata: {e}",
            "source_path": docx_path,
            "file_size": f"{os.path.getsize(docx_path)/1024:.2f} KB" if os.path.exists(docx_path) else "N/A"
        }
def parse_docx_with_path(docx_path, output_dir, quick_mode=True):
    """
    解析单个DOCX文档并提取内容，增强错误处理和健壮性
    返回结构化JSON数据
    
    Args:
        docx_path: DOCX文件路径
        output_dir: 输出目录
        quick_mode: 快速模式，跳过耗时的EMF/WMF转换（默认True）
    """
    temp_dir = None
    try:
        # 首先检查输入文件
        if not os.path.exists(docx_path):
            logger.error(f"输入文件不存在: {docx_path}")
            return None
            
        if not docx_path.lower().endswith('.docx'):
            logger.error(f"不是有效的DOCX文件: {docx_path}")
            return None
            
        # 检查文件是否为临时文件或系统文件（以~$开头）
        filename = os.path.basename(docx_path)
        if filename.startswith('~$'):
            logger.warning(f"跳过临时文件: {filename}")
            return None
            
        file_size = os.path.getsize(docx_path)
        if file_size == 0:
            logger.error(f"文件为空: {docx_path}")
            return None
        elif file_size < 1024:  # 小于1KB的DOCX文件可能损坏
            logger.warning(f"文件可能损坏（太小）: {docx_path} ({file_size} bytes)")
        
        # 创建临时工作目录
        temp_dir = tempfile.mkdtemp(prefix="docx_extract_")
        logger.info(f"创建临时目录: {temp_dir}")
        
        # 复制文件到临时目录
        temp_docx_path = os.path.join(temp_dir, os.path.basename(docx_path))
        try:
            shutil.copy2(docx_path, temp_docx_path)
        except (OSError, IOError) as e:
            logger.error(f"复制文件失败: {e}")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # 检查文件是否成功复制
        if not os.path.exists(temp_docx_path) or os.path.getsize(temp_docx_path) == 0:
            logger.error(f"复制后的文件不存在或为空: {temp_docx_path}")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # 尝试打开文档
        try:
            doc = Document(temp_docx_path)
        except Exception as e:
            logger.error(f"无法打开DOCX文件 {docx_path}: {e}")
            if "Package not found" in str(e) or "not a valid" in str(e).lower():
                logger.error("文件可能损坏或不是有效的DOCX格式")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # 创建输出目录
        try:
            os.makedirs(output_dir, exist_ok=True)
            # 创建图片目录
            images_dir = os.path.join(output_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
        except (OSError, IOError) as e:
            logger.error(f"创建输出目录失败: {e}")
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # 准备文档结构
        document_structure = {
            "metadata": extract_metadata(doc, docx_path),
            "sections": [],
            "processing_info": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_file": os.path.basename(docx_path),
                "file_size_bytes": file_size,
                "errors": [],
                "warnings": []
            }
        }
        
        # 图片引用字典
        image_references = {}
        
        # 图片现在会在内容遍历过程中提取，不需要单独的批量提取
        
        # 创建根节点
        root_section = {
            "type": "section",
            "title": "根节点",
            "level": 0,
            "content": []
        }
        document_structure["sections"].append(root_section)
        
        # 使用栈管理标题层级
        stack = deque([root_section])
        
        # 状态跟踪
        in_toc = False  # 是否在目录部分
        list_counter = defaultdict(int)  # 多级列表计数器
        table_counter = 0  # 表格计数器
        block_counter = 0  # 处理的块计数器
        
        # 遍历文档块（增强错误处理）
        try:
            for block in iter_block_items(doc):
                block_counter += 1
                try:
                    # 段落处理
                    if isinstance(block, Paragraph):
                        try:
                            text = clean_text(block.text) if block.text else ""
                        except Exception as e:
                            logger.warning(f"段落 {block_counter} 文本清理失败: {e}")
                            text = str(block.text) if block.text else ""
                        
                        # 检测目录开始
                        if not in_toc and text and len(text) < 10:
                            import re
                            if re.match(r'^(目\s*录|contents?)$', text, re.IGNORECASE):
                                in_toc = True
                                continue
                            
                        # 检测目录结束
                        if in_toc:
                            try:
                                if get_heading_level(block) > 0 or len(text) > 50:
                                    in_toc = False
                                else:
                                    continue
                            except Exception as e:
                                logger.warning(f"目录检测失败，继续处理: {e}")
                                in_toc = False
                        
                        # 标题处理
                        try:
                            heading_level = get_heading_level(block)
                            if heading_level > 0:
                                # 创建新章节
                                new_section = {
                                    "type": "section",
                                    "title": text,
                                    "level": heading_level,
                                    "content": []
                                }
                                
                                # 确定父章节
                                while stack and stack[-1]["level"] >= heading_level:
                                    stack.pop()
                                
                                # 添加到适当的父章节
                                parent_section = stack[-1] if stack else root_section
                                parent_section["content"].append(new_section)
                                
                                stack.append(new_section)
                                continue
                        except Exception as e:
                            logger.warning(f"标题级别检测失败: {e}")
                        
                        # 列表项处理
                        try:
                            if is_list_item(block):
                                list_level, prefix = get_list_info(block, list_counter)
                                
                                # 提取列表项中的内容（图片和SmartArt）
                                content_nodes = extract_paragraph_content(block, output_dir, image_references, quick_mode)
                                
                                # 创建列表项节点
                                list_item = {
                                    "type": "list_item",
                                    "text": text,  # 保持原始文本，不添加prefix
                                    "level": list_level,
                                    "prefix": prefix,  # 将前缀作为独立字段存储
                                    "is_bullet": "bullet" in str(block.style.name).lower() if hasattr(block, 'style') and block.style else False
                                }
                                
                                # 添加到当前章节
                                current_section = stack[-1] if stack else root_section
                                current_section["content"].append(list_item)
                                
                                # 添加内容作为独立节点
                                if content_nodes:
                                    current_section["content"].extend(content_nodes)
                                continue
                        except Exception as e:
                            logger.warning(f"列表项处理失败: {e}")
                        
                        # 普通段落处理
                        if text or (hasattr(block, 'runs') and block.runs):
                            try:
                                # 提取段落中的内容（图片和SmartArt）
                                content_nodes = extract_paragraph_content(block, output_dir, image_references, quick_mode)
                                
                                # 添加文本段落
                                if text:
                                    para_item = {
                                        "type": "paragraph",
                                        "text": text,
                                        "bold": False,
                                        "italic": False
                                    }
                                    
                                    # 检查格式
                                    try:
                                        if hasattr(block, 'runs') and block.runs:
                                            first_run = block.runs[0]
                                            if hasattr(first_run, 'bold') and first_run.bold:
                                                para_item["bold"] = True
                                            if hasattr(first_run, 'italic') and first_run.italic:
                                                para_item["italic"] = True
                                    except Exception as e:
                                        logger.debug(f"格式检查失败: {e}")
                                    
                                    # 添加到当前章节
                                    current_section = stack[-1] if stack else root_section
                                    current_section["content"].append(para_item)
                                
                                # 添加内容作为独立节点
                                if content_nodes:
                                    current_section = stack[-1] if stack else root_section
                                    current_section["content"].extend(content_nodes)
                            except Exception as e:
                                logger.warning(f"段落内容提取失败: {e}")
                                document_structure["processing_info"]["warnings"].append(f"Paragraph {block_counter} content extraction failed: {e}")
                    
                    # 表格处理
                    elif isinstance(block, Table):
                        try:
                            table_data = parse_table(block, table_counter, image_references, images_dir)
                            table_item = {
                                "type": "table",
                                "index": table_counter,
                                "rows": table_data
                            }
                            table_counter += 1
                            
                            # 添加到当前章节
                            current_section = stack[-1] if stack else root_section
                            current_section["content"].append(table_item)
                        except Exception as e:
                            logger.warning(f"表格 {table_counter} 处理失败: {e}")
                            document_structure["processing_info"]["warnings"].append(f"Table {table_counter} processing failed: {e}")
                            table_counter += 1
                
                except Exception as e:
                    logger.warning(f"处理文档块 {block_counter} 时出错: {e}")
                    document_structure["processing_info"]["warnings"].append(f"Block {block_counter} processing failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"遍历文档块时出现严重错误: {e}")
            document_structure["processing_info"]["errors"].append(f"Document traversal failed: {e}")
        
        # 添加图片引用
        if image_references:
            document_structure["images"] = image_references
            logger.info(f"检测到 {len(image_references)} 张图片")
        else:
            logger.info(f"文档 {os.path.basename(docx_path)} 中没有检测到图片")
        
        # 添加处理统计信息
        document_structure["processing_info"]["blocks_processed"] = block_counter
        document_structure["processing_info"]["tables_found"] = table_counter
        document_structure["processing_info"]["images_found"] = len(image_references)
        
        # 清理临时目录
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.info(f"清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")
        
        return document_structure
        
    except Exception as e:
        logger.error(f"解析文档 {docx_path} 失败: {e}")
        logger.error(traceback.format_exc())
        
        # 确保清理临时目录
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
            
        return None
