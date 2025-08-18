from pathlib import Path

from bs4 import BeautifulSoup

html_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output\mammoth\文档审核\文档审核.html"

with open(html_path, 'rb') as f:
    html_content=f.read()

# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(html_content, "html.parser")

print(soup)