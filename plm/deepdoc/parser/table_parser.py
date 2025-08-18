"""
表格解析器
"""

import logging
from plm.deepdoc.utils.document_utils import identify_merged_cells
from plm.deepdoc.extractor.image_extractor import extract_table_images
from plm.deepdoc.utils.text_utils import clean_text

logger = logging.getLogger(__name__)

def parse_table(table, table_idx, image_references, images_dir):
    """解析表格并处理合并单元格"""
    # 识别所有合并单元格
    merged_cells = identify_merged_cells(table)
    
    table_data = []
    for row_idx, row in enumerate(table.rows):
        row_nodes = []
        for cell_idx, cell in enumerate(row.cells):
            # 如果是被合并的单元格，跳过
            if (row_idx, cell_idx) in merged_cells:
                continue
                
            # 创建单元格节点
            cell_node = {
                "type": "table_cell",
                "row": row_idx,
                "col": cell_idx,
                "content": []
            }
            
            # 添加文本内容
            cell_text = clean_text(cell.text)
            if cell_text:
                cell_node["content"].append({
                    "type": "text",
                    "text": cell_text
                })
                
            # 提取单元格中的图片
            image_nodes = extract_table_images(cell, table_idx, row_idx, cell_idx, image_references, images_dir)
            if image_nodes:
                for img in image_nodes:
                    cell_node["content"].append({
                        "type": "image",
                        "url": img["url"],
                        "format": img["format"],
                        "width": img["width"],
                        "height": img["height"],
                        "size": img["size"]
                    })
            
            row_nodes.append(cell_node)
        table_data.append(row_nodes)
    
    return table_data
