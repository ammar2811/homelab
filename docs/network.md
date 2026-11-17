# Network

## Internet

- **ISP**: Rogers fiber, 2.5 Gbps plan. No Rogers TV or home phone.
- **Path**: Rogers ONT -> BE550 WAN port (2.5G). The Rogers XB8 gateway is removed (keep it boxed; it
  may be a rental to return).
- **WAN**: plain DHCP from Rogers (no PPPoE, no VLAN tag). The router gets a public IPv4 directly.
  If the WAN ever fails to get an address after hardware changes, power-cycle the ONT (its lease can
  stick to the previous router's MAC).

## Router: TP-Link Archer BE550 (hardware v1.0)

- Firmware 1.3.1 Build 20260731, auto-update on (03:00-05:00).
- Admin UI: `http://10.77.0.1`. Ammar logs in; sessions expire. Do not bind it to a TP-Link cloud ID.

Settings we set or verified (2026-11-16/17):

| Setting | Value | Where in the UI |
|---|---|---|
| LAN IP | `10.77.0.1/24` | Advanced > Network > LAN |
| DHCP pool | `10.77.0.100 - 10.77.0.249`, lease 120 min | Advanced > Network > DHCP Server |
| DHCP Primary DNS | `10.77.0.20` (AdGuard) | same |
| DHCP Secondary DNS | `10.77.0.20` (must not be empty, see below) | same |
| UPnP | Off | Advanced > NAT Forwarding > UPnP |
| WPS | Off | Advanced > Wireless > WPS |
| Remote Management | Off | Advanced > System > Administration |
| Wi-Fi security | WPA3+WPA2 on 2.4/5 GHz, WPA3 on 6 GHz, MLO on | Advanced > Wireless > Wireless Settings |
| Port forwards | None | Advanced > NAT Forwarding |

**Why Secondary DNS is not empty**: when it is blank, the BE550 adds itself as a second DNS server in
DHCP, and clients send some queries to it, bypassing AdGuard (verified: `doubleclick.net` resolved to
a real IP). Setting both fields to AdGuard leaves it nothing to add.

**Why `10.77.0.0/24`**: `192.168.0.x`/`192.168.1.x` are used by most hotels, cafes and friends'
networks. With Tailscale subnet routing, an overlapping home subnet makes remote access ambiguous.

## IP plan

Static addresses are configured on the device itself and sit outside the DHCP pool.
Guest IDs follow the rule ID = 100 + last octet.

| IP | Name | What | Status |
|---|---|---|---|
| `10.77.0.1` | router | TP-Link Archer BE550 | Live |
| `10.77.0.10` | `pve.home.arpa` | Proxmox VE host (OptiPlex 5060) | Live |
| `10.77.0.20` | `adguard` | CT 120, AdGuard Home | Live |
| `10.77.0.25` | `tailscale` | CT 125, Tailscale subnet router + exit node | Live |
| `10.77.0.21` | `homeassistant` | VM 121, Home Assistant OS (web on port 80) | Live |
| `10.77.0.30` | `docker` | VM 130, Debian + Docker: Caddy, Jellyfin, Homepage | Live |
| `10.77.0.2-.99` | | Reserved for infrastructure (NAS, Zigbee coordinator, APs) | Free |
| `10.77.0.100-.249` | | DHCP clients | Pool |
| `10.77.0.208` | | Intel AMT of the OptiPlex (DHCP lease) | Live, should be pinned |

## DNS flow

```
client --(DHCP gives 10.77.0.20)--> AdGuard Home (CT 120)
   blocked domain  -> 0.0.0.0
   everything else -> DoH upstreams in parallel: Quad9, Cloudflare
   LAN reverse lookups (PTR) -> router 10.77.0.1
```

- AdGuard's own container uses the router (`10.77.0.1`) for its OS lookups, so it can still update
  itself if AdGuard is broken.

## Local names

Served by AdGuard DNS rewrites (managed in [scripts/adguard/configure.py](../scripts/adguard/configure.py)).
Explicit names only, no wildcard, so device names elsewhere in `home.arpa` are not hijacked.

| Name | Answer | What |
|---|---|---|
| `pve.home.arpa` | `10.77.0.10` | Proxmox (`https://pve.home.arpa:8006`) |
| `adguard.home.arpa` | `10.77.0.20` | AdGuard Home UI |
| `homeassistant.home.arpa` | `10.77.0.21` | Home Assistant (direct, port 80, not via Caddy) |
| `tailscale.home.arpa` | `10.77.0.25` | Tailscale container |
| `docker.home.arpa` | `10.77.0.30` | Docker VM |
| `jellyfin.home.arpa` | `10.77.0.30` | Jellyfin via Caddy |
| `homepage.home.arpa` | `10.77.0.30` | Homepage dashboard via Caddy |

New web services behind Caddy need both a rewrite here and a site block in
[docker/caddy/Caddyfile](../docker/caddy/Caddyfile).
- There is **no DNS redundancy**: if CT 120 or the Proxmox host is down, the house has no DNS. A second
  AdGuard instance on separate hardware is on the roadmap.

## IPv6

The LAN currently has no global IPv6 (checked on the laptop and CT 120). If IPv6 is ever enabled on
the BE550, make sure router advertisements do not hand out the router as a DNS server, or IPv6-capable
devices will bypass AdGuard.

## Physical

- OptiPlex onboard NIC (`nic0`, Intel I219-V, MAC `xx:xx:xx:xx:xx:xx`) -> BE550 LAN port, direct,
  **1000 Mb/s full duplex** (the original cable only did 100 Mb/s and was replaced, see
  [roadmap.md](roadmap.md)).
- Laptop is on Wi-Fi (NetworkManager).
