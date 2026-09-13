import json
import hashlib

target = "7395f9e8ac7cd5dde3c3f1c419e025f8851bb4155b17a47089e8dc4190da0246"

# Let's inspect git diff on commit a0ea8fb for data/cache/llm_cache.json
import subprocess
res = subprocess.run(["git", "show", "a0ea8fb", "--", "data/cache/llm_cache.json"], capture_output=True, text=True, encoding='utf-8')
lines = res.stdout.splitlines()
for i, line in enumerate(lines):
    if target in line:
        print(f"Line {i}: {line}")
        # print surrounding 10 lines
        for j in range(max(0, i-5), min(len(lines), i+15)):
            print(lines[j])
        break
