import re
#
# text = r"<Image>data_here c:/a/b/c/d.png</Image><Image>d:\\a\\b\\c.jpg</Image>"
# images = re.findall(r"<Image[^>]*>(.*?)</Image>", text, re.DOTALL)


text = r"<|IMAGE|>data_here c:/a/b/c/d.png</Image><Image>d:\\a\\b\\c.jpg</|IMAGE|>"
images = re.findall(r"<\|IMAGE\|[^>]*>(.*?)</\|IMAGE\|>", text, re.DOTALL)

print(images)

for img in images:
    print(img)


# 1. 修改 <Image> 内容
def modify_image(match):
    old_path = match.group(1)
    # 示例：替换路径为相对路径或标准化
    new_path = old_path.replace("c:/", "images/").replace("d:\\", "data/")
    return f"<Image>{new_path}</Image>"

text_modified = re.sub(r"<\|IMAGE\|[^>]*>(.*?)</\|IMAGE\|>", modify_image, text)

print(text_modified)