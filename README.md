# Homelab

Ammar's home lab: one Proxmox host behind a TP-Link Archer BE550 on Rogers fiber, running
self-hosted services for the house.

> Published copy: personal details (location, account identifiers, hardware addresses) are
> replaced with placeholders. The private repo it is generated from keeps the full details.


## Highlights

- **Single-box virtualization**: a used Dell OptiPlex 5060 (i7-8700, 16 GB) running Proxmox VE 9 with
  LXC containers and VMs, guest IDs mapped to IPs, everything documented and reproducible.
- **Network-wide DNS filtering**: AdGuard Home with encrypted upstreams (DoH), DNSSEC, and local
  `*.home.arpa` names, served to the LAN and to remote devices.
- **Hardware transcoding**: the Intel iGPU passed through to a Docker VM; Jellyfin transcodes 10-bit
  HEVC on Quick Sync at about 10x real time, verified with `intel_gpu_top`.
- **Zero exposed ports**: remote access, an exit node and ad blocking on the go through a Tailscale
  subnet router.
- **Home Assistant as code**: automations kept as YAML packages in git, deployed by script with a
  config check before every restart. Homelab service-down alerts to the phone, presence, and a
  garbage-day announcement driven by the municipal collection calendar.
- **Built with an AI agent**: set up end to end with Claude Code. [CLAUDE.md](CLAUDE.md) holds the rules
  the agent works under (verify before stating, never handle secrets, prove changes end to end), and
  [docs/decisions.md](docs/decisions.md) records why each choice was made.

## Status (2026-11-17)

| Component | State |
|---|---|
| Router: TP-Link Archer BE550 replacing the Rogers XB8 | Done |
| LAN moved to `10.77.0.0/24` | Done |
| Proxmox VE 9.2 on Dell OptiPlex 5060 SFF | Done, updated, reachable over SSH |
| AdGuard Home (network DNS + ad blocking), CT 120 | Done, serving the whole house |
| Docker VM 130: Caddy, Jellyfin (Quick Sync), Homepage | Done (HTTP on `*.home.arpa`) |
| Tailscale (remote access, exit node, AdGuard DNS), CT 125 | Done |
| Home Assistant OS 18.4, VM 121 | Done (`http://homeassistant.home.arpa`): homelab alerts, presence, garbage-day reminder |
| *arr stack, Immich, HTTPS, backups | Planned |

Open issues and next steps: [docs/roadmap.md](docs/roadmap.md).

## Quick reference

| What | Where |
|---|---|
| Router admin | `http://10.77.0.1` |
| Proxmox web UI | `https://10.77.0.10:8006` (user `root`, realm Linux PAM) |
| AdGuard Home UI | `http://10.77.0.20` (`adguard.home.arpa`) |
| Dashboard (Homepage) | `http://homepage.home.arpa` |
| Jellyfin | `http://jellyfin.home.arpa` |
| Home Assistant | `http://homeassistant.home.arpa` (port 80) |
| SSH | `ssh pve`, `ssh adguard`, `ssh docker`, `ssh tailscale`, `ssh homeassistant` (key auth via ssh-agent) |
| Remote access | Tailscale app on the device, same account; everything above works by name |

## Documentation

- [CLAUDE.md](CLAUDE.md): rules and context for AI agents working in this repo (also a good human primer)
- [docs/network.md](docs/network.md): ISP, router, IP plan, DHCP and DNS
- [docs/hardware.md](docs/hardware.md): the OptiPlex, BIOS settings, Intel AMT
- [docs/proxmox.md](docs/proxmox.md): host install, storage, repositories, access
- [docs/services/adguard-home.md](docs/services/adguard-home.md): AdGuard Home setup and operation
- [docs/services/docker-vm.md](docs/services/docker-vm.md): Docker VM, Caddy, Jellyfin, Homepage
- [docs/services/tailscale.md](docs/services/tailscale.md): remote access, exit node, tailnet DNS
- [docs/services/home-assistant.md](docs/services/home-assistant.md): Home Assistant OS VM
- [docker/](docker/): Compose stack and service configs deployed to the Docker VM
- [homeassistant/](homeassistant/): Home Assistant `configuration.yaml` and automation packages
- [docs/decisions.md](docs/decisions.md): decisions and the reasoning behind them
- [docs/roadmap.md](docs/roadmap.md): planned services, shopping list, open issues

## Scripts

- [scripts/adguard/configure.py](scripts/adguard/configure.py): applies our AdGuard Home settings to `AdGuardHome.yaml`
- [scripts/dnstest.py](scripts/dnstest.py): sends raw DNS queries to a server, no dependencies
- [scripts/deploy-docker.sh](scripts/deploy-docker.sh): syncs `docker/` to VM 130 and runs `docker compose up -d`
- [scripts/deploy-homeassistant.sh](scripts/deploy-homeassistant.sh): copies `homeassistant/` to HA, runs `ha core check`, restarts
- [scripts/build-public.py](scripts/build-public.py): generates the public copy of this repo with personal details replaced
