#!/usr/bin/env python3
import os
import re
import glob
import tempfile
import subprocess
import sys

TARGET_DIR = os.path.join("config", "singbox", "rules")

def sanitize_jsonc(content):
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r',\s*([\]}])', r'\1', content)
    return content

def main():
    if not os.path.exists(TARGET_DIR):
        print(f"Directory {TARGET_DIR} does not exist.")
        sys.exit(1)

    # 1. Clean existing .srs files
    for srs_file in glob.glob(os.path.join(TARGET_DIR, "*.srs")):
        try:
            os.remove(srs_file)
        except Exception as e:
            print(f"Error removing {srs_file}: {e}")

    # 2. Compile all .json files
    json_files = glob.glob(os.path.join(TARGET_DIR, "*.json"))
    for json_path in json_files:
        srs_path = os.path.splitext(json_path)[0] + ".srs"
        print(f"Compiling: {json_path} -> {srs_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            clean_content = sanitize_jsonc(content)
            
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.json') as tmp:
                tmp.write(clean_content)
                tmp_path = tmp.name
                
            cmd = ["sing-box", "rule-set", "compile", "--output", srs_path, tmp_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            os.remove(tmp_path)
            
            if res.returncode != 0:
                print(f"Error compiling {json_path}:\n{res.stderr}")
                sys.exit(1)
            else:
                print(f"Successfully compiled {srs_path}")
                
        except Exception as e:
            print(f"Failed to process {json_path}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
