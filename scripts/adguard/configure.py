import yaml

PATH = "/opt/AdGuardHome/AdGuardHome.yaml"

with open(PATH) as f:
    cfg = yaml.safe_load(f)

dns = cfg["dns"]
# Encrypted upstreams (DNS-over-HTTPS), queried in parallel; fastest answer wins.
dns["upstream_dns"] = [
    "https://dns.quad9.net/dns-query",      # Quad9 with malware blocking
    "https://cloudflare-dns.com/dns-query",  # Cloudflare
]
dns["upstream_mode"] = "parallel"
# Plain-IP resolvers used only to look up the DoH hostnames above.
dns["bootstrap_dns"] = ["9.9.9.9", "149.112.112.112", "1.1.1.1", "2620:fe::fe", "2606:4700:4700::1111"]
# Used only if every encrypted upstream is unreachable.
dns["fallback_dns"] = ["9.9.9.9", "1.1.1.1"]
# LAN-only resolver: no per-client rate limit (the default throttled the whole /24 as one client).
dns["ratelimit"] = 0
# Serve slightly stale cached answers instantly while refreshing them in the background.
dns["cache_optimistic"] = True
dns["enable_dnssec"] = True
# Reverse lookups for LAN IPs go to the router, so device names show in the logs.
dns["use_private_ptr_resolvers"] = True
dns["local_ptr_upstreams"] = ["10.77.0.1"]

cfg["filters"] = [
    {"enabled": True, "id": 1, "name": "AdGuard DNS filter",
     "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt"},
    {"enabled": True, "id": 1700000001, "name": "HaGeZi Multi PRO",
     "url": "https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt"},
    {"enabled": False, "id": 2, "name": "AdAway Default Blocklist",
     "url": "https://adguardteam.github.io/HostlistsRegistry/assets/filter_2.txt"},
]

flt = cfg["filtering"]
flt["filtering_enabled"] = True   # actually apply the blocklists
flt["protection_enabled"] = True

# Local names (see docs/network.md). Services behind Caddy point at the Docker VM.
flt["rewrites_enabled"] = True
flt["rewrites"] = [
    {"domain": "pve.home.arpa", "answer": "10.77.0.10", "enabled": True},
    {"domain": "adguard.home.arpa", "answer": "10.77.0.20", "enabled": True},
    {"domain": "homeassistant.home.arpa", "answer": "10.77.0.21", "enabled": True},
    {"domain": "tailscale.home.arpa", "answer": "10.77.0.25", "enabled": True},
    {"domain": "docker.home.arpa", "answer": "10.77.0.30", "enabled": True},
    {"domain": "jellyfin.home.arpa", "answer": "10.77.0.30", "enabled": True},
    {"domain": "homepage.home.arpa", "answer": "10.77.0.30", "enabled": True},
]

cfg["querylog"]["interval"] = "720h"     # keep 30 days of queries
cfg["statistics"]["interval"] = "720h"   # 30 days of dashboard stats

with open(PATH, "w") as f:
    yaml.safe_dump(cfg, f, sort_keys=False, default_flow_style=False)

print("config updated")
