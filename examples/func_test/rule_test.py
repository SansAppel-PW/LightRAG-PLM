import re

text = r"<Image>data_here c:/a/b/c/d.png</Image><Image>d:\\a\\b\\c.jpg</Image>"
images = re.findall(r"<Image[^>]*>(.*?)</Image>", text, re.DOTALL)

print(images)

for img in images:
    print(img)