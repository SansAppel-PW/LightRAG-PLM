from pathlib import Path

str=''
if str.strip():
    print(str.strip())
else:
    print('nlll')

p = "C:/a/b/c.txt"
print(Path(p).parent)