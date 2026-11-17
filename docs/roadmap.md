# Roadmap

## Open issues

| Issue | Detail | Next step |
|---|---|---|
| No DNS redundancy | CT 120 or a host reboot takes DNS down for the house | Second AdGuard on separate hardware (e.g. Raspberry Pi) + `adguardhome-sync` |
| No backups | Nothing backs up guests yet, now including Jellyfin's database in `/srv/appdata` on VM 130 | Pick a target (USB disk, NAS, Proxmox Backup Server) and schedule `vzdump` |
| Test clip in the library | `Test Pattern (2026)` (synthetic HEVC 10-bit) sits in Movies for transcoding tests | Delete it from `/srv/media/movies` once real media exists, or keep for future GPU checks |
| Intel AMT on a DHCP address | Currently `10.77.0.208` | Pin it (router reservation or static in MEBx), verify remote KVM, check BIOS Deep Sleep Control = Disabled |
| Alerts blind to host outages | Home Assistant (the alerter) runs on the Proxmox host, so a host or power outage sends nothing | External dead-man's switch: HA pings a Healthchecks.io check every few minutes; it emails when pings stop |
| Tailscale via relay | The phone reached home through a Tailscale relay (Toronto), not directly; fine for web UIs, may limit remote Jellyfin streaming | Decide whether to allow one port forward (UDP 41641 -> `10.77.0.25`) for direct connections; record the decision. Re-check with `ssh tailscale 'tailscale status'` while a remote device is active |
| Router reverse DNS | Unknown whether the BE550 answers PTR for DHCP clients (affects names in AdGuard logs) | Check the Query Log client column |

## Planned services

In rough order. IPs from [network.md](network.md).

Done: Docker VM 130 with Caddy (HTTP), Jellyfin (Quick Sync verified) and Homepage
(see [services/docker-vm.md](services/docker-vm.md)).

1. ~~Home Assistant OS~~ - done 2026-11-17 ([services/home-assistant.md](services/home-assistant.md)).
   Done since: homelab service-down alerts, phone presence, garbage-day reminder (all in
   `homeassistant/packages/`). Next for HA: Zigbee coordinator and first devices (leak sensors, a
   power-monitoring plug for laundry-done); morning briefing and Environment Canada alerts on the Home
   Mini; decide on voice control (Nabu Casa vs manual Google project); put HA behind Caddy with HTTPS.
2. ~~Tailscale~~ - done 2026-11-17 ([services/tailscale.md](services/tailscale.md)).
3. **Media HDD**, then on VM 130: **Sonarr, Radarr, Prowlarr, Bazarr, Seerr, qBittorrent behind
   gluetun (VPN)**, optional Stremio streaming server behind the same VPN. `/data` layout per TRaSH
   Guides for hardlinks. Pass the HDD to VM 130 and move `/srv/media` onto it.
4. **HTTPS** - buy a domain (DNS on Cloudflare), Caddy wildcard certificate via DNS challenge, rename
   services to `<name>.home.<domain>`.
5. **Immich** - only after a backup plan exists for photos (3-2-1). Can use the iGPU on VM 130 for ML.
6. **Ollama + Open WebUI** - needs a GPU (e.g. low-profile RTX A2000) or another machine.
7. **Homepage widgets** - service widgets (Jellyfin, AdGuard) need API keys created by Ammar; keep them
   out of git.

## Shopping list

- 32 GB DDR4-2666 (2 x 16 GB) - before Immich or any further VM (3.6 GiB left with HA running)
- 12-20 TB 3.5" HDD for media (one bay in the SFF)
- Backup target for photos and guest backups
- Zigbee coordinator (SMLIGHT SLZB-06 or HA Connect ZBT-1)
- Optional later: second SSD (mirror needs a ZFS reinstall), 2.5G PCIe NIC, low-profile GPU

## Decisions pending

- Domain name for Caddy/HTTPS (determines hostnames and certificates)
- Whether to reinstall Proxmox on ZFS before adding more guests
- Redundant DNS hardware
