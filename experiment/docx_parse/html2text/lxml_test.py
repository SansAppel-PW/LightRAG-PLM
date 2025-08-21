from lxml import etree
from bs4 import BeautifulSoup

input_file_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output\mammoth\文档审核\文档审核_final.html"

html = etree.parse(input_file_path, etree.HTMLParser())

result = html.xpath('//*')

print(result)

for ret in result:
    print(ret)

soup = BeautifulSoup()