# Decisions

Newest first. Each entry: what we chose, why, and what we rejected. Add an entry whenever a choice is
made between real alternatives.

## 2026-11-22 - One port forward: UDP 41641 to Tailscale (CT 125)

**Chosen**: forward UDP 41641 on the BE550 to `10.77.0.25:41641` (tailscaled's fixed port) so tailnet
devices connect to home directly instead of through Tailscale's DERP relays. This replaces the "no port
forward for now" part of the 2026-11-17 Tailscale decision.
**Why**: on Rogers 5G+ the phone sits behind carrier NAT that maps every destination to a new port, so
it never got a direct path and always used a relay. Its relay session (Toronto) went stale every so
often while the phone kept sending through home's relay (Chicago): its DNS queries reached AdGuard and
were answered, but the answers were dropped at Toronto ("derp-21 does not know about peer"). The phone
showed "DNS unavailable" and pages failed to load until it reconnected. Measured over 4 days with a
recorder on CT 125: 20,876 queries, none unanswered at home, 87 relay-lost minutes with a 16.7% query
retry rate vs 2.5% otherwise. With the forward, the phone went direct right away, which also removes
the relay throughput limit for remote Jellyfin.
**Risk accepted**: the only thing reachable from the internet is tailscaled's WireGuard socket, which
drops every packet not from a key in the tailnet. No web UI or other service is exposed. UPnP stays off.
**Rejected**: IPv6 on the LAN (a direct IPv6 path still depends on hole punching through the router's
and the carrier's firewalls, and IPv6 needs its own DNS work so devices keep using AdGuard; worth doing
later as its own project, see [roadmap.md](roadmap.md)); living with relays (the outages are the
problem); a Tailscale peer relay (still needs a reachable port at home).

## 2026-11-17 - Home Assistant automations as code

**Chosen**: the official Terminal & SSH app with key auth; automations as YAML packages in
`homeassistant/packages/`, deployed by `scripts/deploy-homeassistant.sh` with `ha core check` before
any restart. Verification through the recorder database, not through API tokens.
**Why**: reproducible and reviewable like the rest of the repo; no long-lived access token to manage.
**Rejected**: building automations in the UI only (not in git); a long-lived HA token on the laptop
(a secret to protect); the community "Advanced SSH" app (more power than needed).
**Also decided**: the phone keeps Tailscale as Always-on VPN (reliable "left home" updates); the collection
calendar URL stays out of git (it identifies the address); HTTP-level checks instead of plain pings
where a service has a web endpoint (a running VM with a dead service still alerts).

## 2026-11-17 - Tailscale for remote access

**Chosen**: Tailscale in its own LXC (CT 125) as subnet router for `10.77.0.0/24` and exit node; the
tailnet's global DNS is AdGuard with override on.
- **Own container, not in the Docker VM**: remote access must survive Docker VM maintenance and is
  needed to fix it remotely.
- **All DNS via AdGuard** (not split DNS for `home.arpa` only): ad blocking and local names on every
  device on Tailscale. Trade-off: if home is unreachable, devices on Tailscale lose DNS until Tailscale
  is switched off.
- **Exit node enabled**, opt-in per device, for untrusted Wi-Fi.
- **No port forward** for now (connections may use relays); revisit if remote streaming needs direct
  connections.
**Rejected**: WireGuard on the router or a VM (needs a port forward, manual key and client management),
exposing services publicly.

## 2026-11-17 - No Nginx Proxy Manager

Caddy already is the reverse proxy; NPM would duplicate it and keeps its config in a database instead
of git.

## 2026-11-17 - Docker VM phase 1 scope and design

**Chosen**: one Debian 13 VM (130) running Docker Compose with Caddy, Jellyfin and Homepage; the
Intel iGPU fully passed through to it.
- **Full iGPU passthrough to a VM** (not Docker in an LXC with `/dev/dri` shared, not GVT-g): matches
  Proxmox's advice to run Docker in VMs, keeps Docker isolated from the host, and GVT-g is
  unmaintained. Cost: the host loses its console output and only one guest can use the GPU.
- **Docker from Debian packages** (docker.io 26.1, compose 2.26) per our "distro first" convention,
  rather than Docker's own apt repo. Revisit if a needed feature requires newer Docker.
- **HTTPS deferred**: no domain yet, so Caddy serves plain HTTP on explicit `*.home.arpa` names. Adding
  a domain later only changes the Caddyfile and DNS names.
- **arr apps wait for the media HDD** (no point configuring paths on a 64 GB disk).
- **Downloads via torrents through a VPN** (qBittorrent behind gluetun) when the arr apps arrive;
  Rogers forwards copyright notices. Stremio's streaming server, if added, goes behind the same VPN.
- **Guest Secure Boot off** (`pre-enrolled-keys=0`) to avoid module-signing friction; the host keeps
  Secure Boot.
- **Images pinned to exact versions**, upgraded deliberately.

## 2026-11-17 - AdGuard Home for network DNS

**Chosen**: AdGuard Home in its own LXC (CT 120).
**Why**: built-in encrypted upstreams (DoH/DoT/DoQ) without a second program; wildcard DNS rewrites
in one UI rule (needed for `*.home.<domain>` -> Caddy); per-client settings; single binary.
**Rejected**: Pi-hole (larger community, but wildcards need raw dnsmasq lines and encrypted upstream
needs cloudflared/Unbound alongside), Technitium (most capable, kept as the upgrade path if we want
authoritative zones and built-in clustering), Blocky (config-only, no UI), NextDNS/Control D (cloud,
cannot serve local names, DNS history leaves the house).
**Consequence**: no DNS redundancy yet; a second instance on separate hardware is planned.

## 2026-11-17 - Proxmox installed on ext4/LVM-thin (not ZFS)

**What happened**: the plan was ZFS RAID0 (to allow attaching a second SSD as a mirror later without
reinstalling), but the installer's filesystem choice sits behind an "Options" button and the default
ext4 + LVM-thin was installed. Kept as is.
**Trade-off accepted**: no checksums/compression, and adding a mirrored boot SSD later means a
reinstall (back up guests, reinstall on ZFS, restore). Snapshots still work on LVM-thin.
**Revisit**: before the guest count grows, if a mirrored boot disk becomes a goal.

## 2026-11-17 - Container conventions

ID = 100 + last IP octet; unprivileged Debian 13 LXC from the official template; services never on
the Proxmox host. Details in [proxmox.md](proxmox.md).

## 2026-11-16 - Proxmox VE as the base OS for the OptiPlex

**Why**: Home Assistant OS as a proper VM, light containers for small services, per-guest snapshots
and backups, room for a TrueNAS VM or Proxmox Backup Server later.
**Rejected**: TrueNAS SCALE / Unraid (NAS-first, storage is not the main job yet; Unraid is paid),
plain Debian + Docker (no clean HAOS, no per-service snapshots), HAOS bare metal (wastes the box).

## 2026-11-16 - Workstation stays the control point, not the OptiPlex

Claude Code and this repo live on the laptop and reach the lab over SSH. Running the agent on the
hypervisor would put an agent with root on the host and lose the helper whenever the host breaks.
Later option: a dedicated management container, never the host itself.

## 2026-11-16 - LAN subnet `10.77.0.0/24`

**Why**: avoids the `192.168.0/1.x` ranges common on other networks, which would collide with
Tailscale subnet routing when away from home. DHCP pool `.100-.249`, statics `.2-.99`.

## 2026-11-16 - Hostname domain `home.arpa`

**Why**: reserved for home networks (RFC 8375), can never clash with a public domain. Switch the
domain part to `home.<owned-domain>` once a domain is bought for Caddy/HTTPS. Never `.local` (mDNS).

## 2026-11-16 - IoT devices on the main network, prefer Zigbee/Thread

**Why**: the BE550's IoT network is all-or-nothing isolation, which would break Home Assistant's
local control and discovery. Instead: prefer Zigbee/Thread devices (not on the IP network at all),
local-control Wi-Fi devices (Shelly, ESPHome), UPnP off, no port forwards. Cloud-only devices that HA
does not need to control may go on the isolated IoT SSID (casting across networks will not work).
**Revisit**: if many cloud Wi-Fi devices arrive, move to a router with real VLANs and firewall rules
(e.g. UniFi) and keep the BE550 as an access point.

## 2026-11-16 - Router: TP-Link Archer BE550, XB8 removed

**Why**: 2.5G WAN for the 2.5 Gbps plan, Wi-Fi 7, single router covers the semi-detached house, and
with services (DNS, VPN) running on Proxmox the router only needs to route, do DHCP and Wi-Fi well.
**Rejected**: UniFi Dream Router 7 (better segmentation and IDS, higher cost; reconsider if VLANs are
needed), GL.iNet Flint 3 (OpenWrt flexibility, less polished).
**Rogers**: fiber ONT -> router WAN with plain DHCP; no Rogers TV/phone to keep.

## 2026-11-16 - No router VM on the homelab box

The house's internet must not depend on the hypervisor. Routing stays on dedicated hardware.
