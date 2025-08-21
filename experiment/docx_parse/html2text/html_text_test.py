import chardet
import html_text
import readability

input_file_path = r"C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\experiment\output\mammoth\文档审核\文档审核_final.html"

def get_encoding(file):
    with open(file, 'rb') as f:
        tmp = chardet.detect(f.read())
        return tmp["encoding"]

def get_data(file_path):
    with open(file_path, 'r', encoding=get_encoding(file_path)) as f:
        txt = f.read()
        html_doc = readability.Document(txt)
        content = html_text.extract_text(html_doc.summary(html_partial=True))
        sections = content.split("\n")
        return sections

ret = get_data(input_file_path)

for d in ret:
    print('------------')
    print(d)



