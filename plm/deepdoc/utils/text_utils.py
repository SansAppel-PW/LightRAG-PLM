"""
文本处理和文档结构分析工具
"""

import re
from collections import defaultdict
from docx.text.paragraph import Paragraph

def clean_text(text):
    """清理文本中的特殊字符和多余空格"""
    if not text:
        return ""
    # 替换各种空格和特殊字符
    text = text.replace('\xa0', ' ').replace('\t', ' ').replace('\r', '')
    # 合并多余空格
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_heading_level(para):
    """
    智能识别标题层级
    1. 通过样式名称识别（如"Heading 1"或"标题1"）
    2. 通过文本模式识别（如"1.1 标题内容"）
    """
    # 通过样式名称识别
    if hasattr(para, 'style') and para.style and para.style.name:
        style_name = para.style.name.lower()
        if 'heading' in style_name or '标题' in style_name:
            # 提取数字
            match = re.search(r'(\d+)', style_name)
            if match:
                return min(int(match.group(1)), 6)  # 最大支持6级
    
    # 通过文本模式识别 (如 "1.1 标题内容")
    text = clean_text(para.text)
    match = re.match(r'^(\d+(\.\d+)*)\s+', text)
    if match:
        level_str = match.group(1)
        return min(len(level_str.split('.')), 6)  # 最大支持6级
    
    return 0

def is_list_item(para):
    """判断段落是否为列表项"""
    if not hasattr(para, '_p') or para._p is None:
        return False
    if not hasattr(para._p, 'pPr') or para._p.pPr is None:
        return False
    return para._p.pPr.numPr is not None

def get_list_info(para, list_counter):
    """
    获取列表项详细信息
    返回: (list_level, prefix)
    """
    num_pr = para._p.pPr.numPr
    if num_pr is None:
        return 0, ""
    
    # 获取列表层级
    ilvl = num_pr.ilvl
    list_level = int(ilvl.val) if ilvl is not None and ilvl.val is not None else 0
    
    # 获取列表类型
    num_id = num_pr.numId
    num_id_val = num_id.val if num_id is not None else None
    
    # 更新列表计数器
    list_counter[list_level] += 1
    # 重置子层级计数器
    for lvl in range(list_level + 1, 10):
        if lvl in list_counter:
            list_counter[lvl] = 0
    
    # 创建前缀
    prefix = " " * (list_level * 4)  # 每级缩进4个空格
    
    # 确定列表符号
    is_bullet = "bullet" in str(para.style.name).lower() if hasattr(para, 'style') and para.style else False
    if is_bullet:
        prefix += "• "  # 项目符号
    else:
        # 数字编号
        prefix += ".".join(str(list_counter[lvl]) for lvl in range(list_level + 1)) + ". "
    
    return list_level, prefix

def safe_filename(filename):
    """创建安全的文件名，移除无效字符"""
    # 移除文件系统不允许的字符
    file_name = filename.replace(' ', '').strip()
    safe_name = re.sub(r'[<>:"/\\|?*\[\]]', '_', filename)
    # 限制长度
    return safe_name[:150]

def add_error_to_failed_files(failed_files, filename, error_msg):
    """添加错误信息到失败文件列表的辅助函数"""
    failed_files.append({"file": filename, "error": error_msg})
