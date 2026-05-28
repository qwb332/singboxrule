#!/usr/bin/env python3
import os
import json
import urllib.request
import sys

SINGBOX_RULES_DIR = os.path.join("config", "singbox", "rules")
MIHOMO_RULES_DIR = os.path.join("config", "mihomo", "rules")
FAKEIP_FILTER_URL = "https://raw.githubusercontent.com/qichiyuhub/rule/refs/heads/main/rules/fakeipfilter.json"

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
            # For domain behavior, output raw domains
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

def main():
    print("Starting Sing-box JSON rules to Mihomo YAML conversion...")
    
    os.makedirs(MIHOMO_RULES_DIR, exist_ok=True)
    
    # 1. Clean existing rule files in Mihomo rules directory (including old .mrs)
    for filename in os.listdir(MIHOMO_RULES_DIR):
        if filename.endswith(".mrs") or filename.endswith(".yaml"):
            try:
                os.remove(os.path.join(MIHOMO_RULES_DIR, filename))
            except Exception as e:
                print(f"Failed to remove {filename}: {e}")
            
    # 2. Download and convert remote fakeipfilter.json
    print(f"Downloading remote fakeipfilter.json from {FAKEIP_FILTER_URL}...")
    try:
        req = urllib.request.Request(FAKEIP_FILTER_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            fakeip_data = json.loads(response.read().decode('utf-8'))
            
        behavior = determine_ruleset_behavior(fakeip_data)
        payload = convert_to_clash_payload(fakeip_data, behavior)
        
        output_yaml = os.path.join(MIHOMO_RULES_DIR, "fakeipfilter.yaml")
        write_clash_yaml(payload, output_yaml)
        print(f"Exported fakeipfilter.yaml successfully ({behavior} behavior).")
    except Exception as e:
        print(f"Failed to fetch/process remote fakeipfilter: {e}")

    # 3. Process local sing-box rules
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
                
                output_yaml = os.path.join(MIHOMO_RULES_DIR, f"{rule_name}.yaml")
                write_clash_yaml(payload, output_yaml)
                print(f"Exported {rule_name}.yaml successfully ({behavior} behavior).")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
                
    print("Rules conversion process completed.")

if __name__ == "__main__":
    main()
