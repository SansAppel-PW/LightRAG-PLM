"""
文档遍历和结构分析工具
"""

from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
import logging

logger = logging.getLogger(__name__)

def iter_block_items(parent):
    """
    按文档顺序生成段落和表格，增强异常处理
    """
    try:
        if isinstance(parent, _Document):
            parent_elm = parent.element.body
        elif isinstance(parent, Table):
            # 对于表格，我们需要遍历单元格
            for row in parent.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        yield paragraph
            return
        else:
            parent_elm = parent._element
        
        if parent_elm is None:
            logger.warning("父元素为空，跳过遍历")
            return
            
        for child in parent_elm.iterchildren():
            if isinstance(child.tag, str) and child.tag.endswith('}p'):
                yield Paragraph(child, parent)
            elif isinstance(child.tag, str) and child.tag.endswith('}tbl'):
                yield Table(child, parent)
                
    except Exception as e:
        logger.error(f"遍历文档块失败: {e}")
        return

def identify_merged_cells(table):
    """
    识别合并的单元格
    返回: 被合并单元格的位置集合{(row_idx, col_idx)}
    """
    merged_cells = set()
    try:
        # 兼容的XML命名空间处理
        try:
            from lxml import etree
            # 使用lxml的方法
            grid = table._tbl.find('.//w:tblGrid', table._tbl.nsmap)
        except ImportError:
            # 回退到xml.etree.ElementTree
            try:
                import xml.etree.ElementTree as etree
            except ImportError:
                from xml.etree import ElementTree as etree
            # 简化的命名空间处理
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            grid = table._tbl.find('.//w:tblGrid', namespaces)
        
        if grid is None:
            return merged_cells
        
        try:
            cols = grid.findall('.//w:gridCol', grid.nsmap)
        except:
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            cols = grid.findall('.//w:gridCol', namespaces)
            
        if not cols:
            return merged_cells
        
        # 创建单元格网格
        rows = table.rows
        if not rows:
            return merged_cells
        
        # 标记所有被合并的单元格
        for row_idx, row in enumerate(rows):
            for cell_idx, cell in enumerate(row.cells):
                tc = cell._tc
                tcPr = tc.tcPr
                
                # 检测跨列
                grid_span = 1
                if tcPr.gridSpan is not None:
                    grid_span = int(tcPr.gridSpan.val)
                
                # 检测跨行
                row_span = 1
                v_merge = tcPr.vMerge
                if v_merge is not None and v_merge.val == "restart":
                    # 计算实际行跨度
                    for i in range(row_idx + 1, len(table.rows)):
                        if cell_idx >= len(table.rows[i].cells):
                            break
                        next_cell = table.rows[i].cells[cell_idx]
                        next_tcPr = next_cell._tc.tcPr
                        if next_tcPr.vMerge is None or next_tcPr.vMerge.val != "continue":
                            break
                        row_span += 1
                
                # 标记被合并的单元格
                if grid_span > 1 or row_span > 1:
                    for r in range(row_idx, row_idx + row_span):
                        for c in range(cell_idx, cell_idx + grid_span):
                            if r != row_idx or c != cell_idx:
                                merged_cells.add((r, c))
                                
    except Exception as e:
        logger.error(f"识别合并单元格失败: {e}")
    
    return merged_cells
