import os
import re
from pathlib import Path


def prepare_env(output_dir, pdf_file_name, parse_method):
    local_md_output_dir = Path(output_dir) /parse_method /pdf_file_name
    local_image_dir = local_md_output_dir / "images"
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_output_dir, exist_ok=True)
    return local_image_dir, local_md_output_dir

def safe_filename(filename):
    """创建安全的文件名，移除无效字符"""
    # 移除文件系统不允许的字符
    safe_name = re.sub(r'[<>:"/\\|?*\[\]]', '_', filename)
    # 限制长度
    return safe_name[:150]