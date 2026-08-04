#!/usr/bin/env python3
import os
import json
import urllib.request

# Define your merge configurations here
# You can add more merge targets in the future by simply adding items to this list!
MERGE_CONFIGS = [
    {
        "name": "Pikpak & Mediafire (Download)",
        "remote_url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/sing/geo/geosite/pikpak.json",
        "local_path": os.path.join("config", "singbox", "rules", "download.json"),
        "custom_domains": ["mediafire.com"]
    }
    # Example for future additions:
    # {
    #     "name": "Another Rule Set",
    #     "remote_url": "https://example.com/remote.json",
    #     "local_path": os.path.join("config", "singbox", "rules", "custom.json"),
    #     "custom_domains": ["mycustomdomain.com"]
    # }
]

def merge_rule(config):
    name = config["name"]
    remote_url = config["remote_url"]
    local_path = config["local_path"]
    custom_domains = config.get("custom_domains", [])

    print(f"[{name}] Fetching remote rules from {remote_url}...")
    try:
        req = urllib.request.Request(remote_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            remote_data = json.loads(response.read().decode('utf-8'))
        
        domains = []
        domain_suffixes = list(custom_domains)
        
        for rule in remote_data.get("rules", []):
            if "domain" in rule:
                val = rule["domain"]
                if isinstance(val, list):
                    domains.extend(val)
                else:
                    domains.append(val)
            if "domain_suffix" in rule:
                val = rule["domain_suffix"]
                if isinstance(val, list):
                    domain_suffixes.extend(val)
                else:
                    domain_suffixes.append(val)
                    
        # Deduplicate and preserve order
        domains = list(dict.fromkeys(domains))
        domain_suffixes = list(dict.fromkeys(domain_suffixes))
        
        merged_rules = []
        if domains:
            merged_rules.append({"domain": domains})
        if domain_suffixes:
            merged_rules.append({"domain_suffix": domain_suffixes})
            
        merged_data = {
            "version": 1,
            "rules": merged_rules
        }
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
            
        print(f"[{name}] Successfully merged remote rules and custom domains into {local_path}")
        
    except Exception as e:
        print(f"[{name}] Error fetching/merging rules: {e}")
        # In case of failure, ensure local JSON exists with at least the custom domains
        if not os.path.exists(local_path):
            fallback_data = {
                "version": 1,
                "rules": [{"domain_suffix": custom_domains}]
            }
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(fallback_data, f, indent=2, ensure_ascii=False)
            print(f"[{name}] Wrote fallback ruleset to {local_path}")

def main():
    print("Starting rules merge process...")
    for config in MERGE_CONFIGS:
        merge_rule(config)
    print("All rules merged successfully.")

if __name__ == "__main__":
    main()
