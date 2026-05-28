#!/usr/bin/env python3
import os
import json
import urllib.request
import subprocess
import shutil
import sys
import platform

SINGBOX_RULES_DIR = os.path.join("config", "singbox", "rules")
MIHOMO_RULES_DIR = os.path.join("config", "mihomo", "rules")
FAKEIP_FILTER_URL = "https://raw.githubusercontent.com/qichiyuhub/rule/refs/heads/main/rules/fakeipfilter.json"
MIHOMO_VERSION = "v1.18.9"

def determine_ruleset_behavior(rules_data):
    has_domains = False
    has_ips = False
    has_keywords_or_regex = False

    for rule in rules_data.get("rules", []):
        if "domain" in rule or "domain_suffix" in rule:
            has_domains = True
        if "domain_keyword" in rule or "domain_regex" in rule:
            has_keywords_or_regex = True
        if "ip_cidr" in rule:
            has_ips = True

    if has_keywords_or_regex:
        return "classical"
    elif has_domains and has_ips:
        return "classical"
    elif has_ips:
        return "ipcidr"
    elif has_domains:
        return "domain"
    else:
        return "classical"

def convert_to_clash_payload(rules_data, behavior):
    payload = []
    for rule in rules_data.get("rules", []):
        if behavior == "domain":
            for item in rule.get("domain", []) + rule.get("domain_suffix", []):
                payload.append(item)
        elif behavior == "ipcidr":
            for item in rule.get("ip_cidr", []):
                payload.append(item)
        else: # classical
            for item in rule.get("domain", []):
                payload.append(f"DOMAIN,{item}")
            for item in rule.get("domain_suffix", []):
                payload.append(f"DOMAIN-SUFFIX,{item}")
            for item in rule.get("domain_keyword", []):
                payload.append(f"DOMAIN-KEYWORD,{item}")
            for item in rule.get("domain_regex", []):
                payload.append(f"DOMAIN-REGEX,{item}")
            for item in rule.get("ip_cidr", []):
                payload.append(f"IP-CIDR,{item}")
    return payload

def write_clash_yaml(payload, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("payload:\n")
        for item in payload:
            f.write(f"  - '{item}'\n")

def compile_ruleset(mihomo_path, behavior, input_yaml, output_mrs):
    cmd = [mihomo_path, "convert-ruleset", behavior, "yaml", input_yaml, output_mrs]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Compilation error for {input_yaml}: {result.stderr}")
        return False
    return True

def download_mihomo():
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    # Check if mihomo is already in PATH
    mihomo_cmd = shutil.which("mihomo")
    if mihomo_cmd:
        print(f"Found mihomo in system PATH: {mihomo_cmd}")
        return mihomo_cmd

    ext = ".exe" if system == "windows" else ""
    local_binary = os.path.abspath(f"mihomo{ext}")
    if os.path.exists(local_binary):
        print(f"Found mihomo binary locally: {local_binary}")
        return local_binary

    arch_map = {
        "amd64": "amd64",
        "x86_64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "armv7l": "armv7",
        "i386": "386",
        "i686": "386"
    }
    
    arch = arch_map.get(machine)
    if not arch:
        print(f"Unsupported architecture: {machine}")
        return None

    archive_ext = ".zip" if system == "windows" else ".gz"
    
    if system == "windows":
        system_name = "windows"
    elif system == "linux":
        system_name = "linux"
    elif system == "darwin":
        system_name = "darwin"
    else:
        print(f"Unsupported OS: {system}")
        return None

    # Determine correct download URL
    asset_name = f"mihomo-{system_name}-{arch}-{MIHOMO_VERSION}"
    url_paths = [
        f"https://github.com/MetaCubeX/mihomo/releases/download/{MIHOMO_VERSION}/{asset_name}{archive_ext}",
        f"https://githubproxy.cc/https://github.com/MetaCubeX/mihomo/releases/download/{MIHOMO_VERSION}/{asset_name}{archive_ext}"
    ]

    for url in url_paths:
        print(f"Trying to download mihomo from {url}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            archive_path = f"temp_mihomo{archive_ext}"
            with urllib.request.urlopen(req) as response, open(archive_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
            # Extract
            if archive_ext == ".zip":
                import zipfile
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    for member in zip_ref.namelist():
                        if member.endswith(".exe"):
                            with zip_ref.open(member) as source, open(local_binary, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            break
            else: # .gz
                import gzip
                with gzip.open(archive_path, 'rb') as f_in, open(local_binary, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                os.chmod(local_binary, 0o755)

            if os.path.exists(archive_path):
                os.remove(archive_path)

            print(f"Successfully downloaded and extracted mihomo to {local_binary}")
            return local_binary
        except Exception as e:
            print(f"Failed to download from {url}: {e}")
            if os.path.exists(f"temp_mihomo{archive_ext}"):
                os.remove(f"temp_mihomo{archive_ext}")
            continue

    print("Error: Could not download mihomo binary from any mirror.")
    return None

def main():
    print("Starting Sing-box rules to Mihomo MRS/YAML conversion...")
    
    os.makedirs(MIHOMO_RULES_DIR, exist_ok=True)
    
    # 1. Clean existing .mrs and .yaml files in Mihomo rules directory
    for filename in os.listdir(MIHOMO_RULES_DIR):
        if filename.endswith(".mrs") or filename.endswith(".yaml"):
            os.remove(os.path.join(MIHOMO_RULES_DIR, filename))
            
    # 2. Get mihomo compiler binary
    mihomo_path = download_mihomo()
    if not mihomo_path:
        print("Warning: Mihomo compiler binary not found. MRS compilation will be skipped (only YAML files will be produced).")
        
    # 3. Download and convert remote fakeipfilter.json
    print(f"Downloading remote fakeipfilter.json from {FAKEIP_FILTER_URL}...")
    try:
        req = urllib.request.Request(FAKEIP_FILTER_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            fakeip_data = json.loads(response.read().decode('utf-8'))
            
        behavior = determine_ruleset_behavior(fakeip_data)
        payload = convert_to_clash_payload(fakeip_data, behavior)
        
        temp_yaml = os.path.join(MIHOMO_RULES_DIR, "fakeipfilter.yaml")
        write_clash_yaml(payload, temp_yaml)
        
        if mihomo_path and behavior != "classical":
            output_mrs = os.path.join(MIHOMO_RULES_DIR, "fakeipfilter.mrs")
            if compile_ruleset(mihomo_path, behavior, temp_yaml, output_mrs):
                os.remove(temp_yaml)
                print("Compiled fakeipfilter.mrs successfully.")
        else:
            if behavior == "classical":
                print("Exported fakeipfilter.yaml successfully (classical behavior).")
            else:
                print(f"Exported fakeipfilter.yaml successfully ({behavior} behavior, compilation skipped).")
    except Exception as e:
        print(f"Failed to fetch/process remote fakeipfilter: {e}")

    # 4. Process local sing-box rules
    if not os.path.exists(SINGBOX_RULES_DIR):
        print(f"Error: Sing-box rules directory '{SINGBOX_RULES_DIR}' does not exist.")
        sys.exit(1)
        
    for filename in os.listdir(SINGBOX_RULES_DIR):
        if filename.endswith(".json"):
            json_path = os.path.join(SINGBOX_RULES_DIR, filename)
            rule_name = os.path.splitext(filename)[0]
            
            print(f"Processing: {json_path}")
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    rules_data = json.load(f)
                    
                behavior = determine_ruleset_behavior(rules_data)
                payload = convert_to_clash_payload(rules_data, behavior)
                
                temp_yaml = os.path.join(MIHOMO_RULES_DIR, f"{rule_name}.yaml")
                write_clash_yaml(payload, temp_yaml)
                
                if mihomo_path and behavior != "classical":
                    output_mrs = os.path.join(MIHOMO_RULES_DIR, f"{rule_name}.mrs")
                    if compile_ruleset(mihomo_path, behavior, temp_yaml, output_mrs):
                        os.remove(temp_yaml)
                        print(f"Compiled {rule_name}.mrs successfully.")
                else:
                    if behavior == "classical":
                        print(f"Exported {rule_name}.yaml successfully (classical behavior).")
                    else:
                        print(f"Exported {rule_name}.yaml successfully ({behavior} behavior, compilation skipped).")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                
    print("Rules conversion process completed.")

if __name__ == "__main__":
    main()
