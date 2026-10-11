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

def fetch_bt_trackers():
    bt_rule_path = os.path.join("config", "singbox", "rules", "bt.json")
    print("[BT Trackers] Fetching latest tracker lists...")
    
    tracker_urls = [
        "https://trackerslist.com/all_aria2.txt",
        "https://cdn.jsdelivr.net/gh/XIU2/TrackersListCollection@master/all_aria2.txt",
        "https://trackers.p3terx.com/all_aria2.txt"
    ]
    
    # Pre-add base service domains for tracker lists
    domains = {
        "trackerslist.com",
        "trackers.p3terx.com"
    }
    excluded_domains = {
        "github.com",
        "raw.githubusercontent.com",
        "cdn.jsdelivr.net",
        "bittorrent.com",
        "bitcomet.com",
        "utorrent.com",
        "transmissionbt.com"
    }
    ips = set()
    
    import re
    from urllib.parse import urlparse
    
    for url in tracker_urls:
        try:
            print(f"[BT Trackers] Downloading from {url}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode('utf-8', errors='ignore')
                for item in content.split(','):
                    item = item.strip()
                    if not item:
                        continue
                    parsed = urlparse(item)
                    host = parsed.hostname
                    if host:
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
                            ips.add(f"{host}/32")
                        elif ':' in host:
                            ips.add(f"{host}/128")
                        else:
                            domains.add(host)
        except Exception as e:
            print(f"[BT Trackers] Error fetching {url}: {e}")
            
    # Also include official/community geosite:tracker from MetaCubeX if accessible
    metacubex_tracker_url = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/sing/geo/geosite/tracker.json"
    try:
        print(f"[BT Trackers] Merging MetaCubeX tracker rules from {metacubex_tracker_url}...")
        req = urllib.request.Request(metacubex_tracker_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            for rule in data.get("rules", []):
                for d in rule.get("domain", []):
                    domains.add(d)
                for ds in rule.get("domain_suffix", []):
                    domains.add(ds)
    except Exception as e:
        print(f"[BT Trackers] Error fetching MetaCubeX trackers: {e}")

    domains = {
        d for d in domains
        if d not in excluded_domains and not d.endswith(".cn")
    }
        
    sorted_domains = sorted(list(domains))
    sorted_ips = sorted(list(ips))
    
    rules = []
    if sorted_domains:
        rules.append({"domain_suffix": sorted_domains})
    if sorted_ips:
        rules.append({"ip_cidr": sorted_ips})
        
    bt_data = {
        "version": 1,
        "rules": rules
    }
    
    os.makedirs(os.path.dirname(bt_rule_path), exist_ok=True)
    with open(bt_rule_path, "w", encoding="utf-8") as f:
        json.dump(bt_data, f, indent=2, ensure_ascii=False)
        
    print(f"[BT Trackers] Successfully generated {bt_rule_path} with {len(sorted_domains)} domains and {len(sorted_ips)} IPs.")

def main():
    print("Starting rules merge process...")
    for config in MERGE_CONFIGS:
        merge_rule(config)
    fetch_bt_trackers()
    print("All rules merged successfully.")

if __name__ == "__main__":
    main()

