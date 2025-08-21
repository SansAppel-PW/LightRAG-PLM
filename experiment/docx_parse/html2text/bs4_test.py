from pathlib import Path

from bs4 import BeautifulSoup

html_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output\mammoth\文档审核\文档审核.html"

with open(html_path, 'rb') as f:
    html_content=f.read()

# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(html_content, "html.parser")

print(soup)

all_h1 = soup.find_all('h1')
print(len(all_h1))

print(all_h1[2])

print('------------------------------------')
# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(html_content, "lxml")
print(soup.body)

all_h1 = soup.find_all('h1')

h1_1 = all_h1[1]
print(h1_1.next_siblings)
print('======================')
for n in h1_1.next_siblings:
    print(n)
    print(f"name:{n.name}")
    print('++++++++++++++++++')
