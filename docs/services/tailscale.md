# Tailscale (CT 125)

Remote access to the home network from anywhere, without opening ports.

| | |
|---|---|
| Container | LXC 125 `tailscale`, unprivileged Debian 13, 1 core, 512 MB RAM + 512 MB swap, 4 GB disk |
| IP | `10.77.0.25/24` (static), DNS `10.77.0.20` |
| Boot | `onboot=1`, `startup order=2` (after DNS), tag `vpn` |
| Device access | `dev0: /dev/net/tun` (kernel-mode WireGuard) |
| Version | Tailscale 1.104.7 from `pkgs.tailscale.com/stable/debian trixie` |
| Tailnet name | `homelab`, Tailscale IP `100.x.y.z`, MagicDNS `homelab.<tailnet>.ts.net` |
| Account | Ammar's Tailscale account (admin console: `login.tailscale.com/admin`) |
| SSH | `ssh tailscale` |

## What it does

- **Subnet router** for `10.77.0.0/24`: tailnet devices reach every home IP (Proxmox, AdGuard, Docker VM).
  Traffic is SNATed, so home services see it coming from `10.77.0.25`.
- **Exit node** (opt-in per device): routes all of a device's internet traffic through home.
- **DNS**: the tailnet's global nameserver is AdGuard `10.77.0.20` with "Override DNS servers" on, so
  devices on Tailscale get ad blocking and `*.home.arpa` names everywhere. MagicDNS stays on (handles
  `*.ts.net`).

## How it was installed

1. Container created per the standard in [proxmox.md](../proxmox.md), plus `--dev0 /dev/net/tun`.
2. Tailscale's apt repo key checked before use: fingerprint
   `2596A99EAAB33821893C0A79458CA832957F5868` (Tailscale's published signing key), installed to
   `/usr/share/keyrings/tailscale-archive-keyring.gpg`, repo in `/etc/apt/sources.list.d/tailscale.list`.
   Debian does not package Tailscale.
3. Forwarding: `/etc/sysctl.d/99-tailscale.conf` (`net.ipv4.ip_forward=1`,
   `net.ipv6.conf.all.forwarding=1`).
4. UDP GRO forwarding on `eth0` (Tailscale's recommended throughput tweak for forwarding nodes), made
   persistent by `/etc/systemd/system/udp-gro-forwarding.service` (runs before `tailscaled`).
5. Started with:
   ```bash
   tailscale up --advertise-routes=10.77.0.0/24 --advertise-exit-node --hostname=homelab --accept-dns=false
   ```
   `--accept-dns=false` keeps the container on AdGuard directly instead of Tailscale's resolver.
6. Ammar signed in, then in the admin console: approved the `10.77.0.0/24` route and the exit node,
   disabled key expiry, added `10.77.0.20` as a global nameserver and turned on Override DNS servers.

## Verification (2026-11-17)

- Node: `BackendState Running`, `PrimaryRoutes ['10.77.0.0/24']`, exit node routes allowed, key expiry
  disabled; `tailscale dns status --all` shows resolver `10.77.0.20`.
- Phone (Pixel 9) on mobile data: Homepage, Jellyfin and Proxmox loaded by name; exit node showed the
  home IP; AdGuard logged 293 lookups from `10.77.0.25` (71 blocked).

## Direct connections (port forward, 2026-11-22)

The BE550 forwards UDP 41641 to `10.77.0.25:41641`, the port tailscaled listens on
(`PORT="41641"` in `/etc/default/tailscaled`; keep it fixed). The node then advertises
`<public IP>:41641` as an endpoint, and devices behind hard carrier NAT can reach it directly.
Decision and evidence: [decisions.md](../decisions.md) (2026-11-22).

**The problem it fixed**: on Rogers 5G+ the phone (IPv6-only with 464XLAT, endpoint-dependent carrier
NAT) never got a direct path and always used a DERP relay. Phone-to-home traffic went through home's
relay (`ord`) and arrived, but home's replies went through the phone's relay (`tor`), and that session
went stale every so often. tailscaled logged `derp-21 does not know about peer [...]`, DNS answers were
dropped, and the phone showed "DNS unavailable" (the Tailscale warning can stay up for a while after DNS
works again). Every query that reached AdGuard was answered, so AdGuard was never the problem.

Verified 2026-11-22 right after adding the rule: `tailscale status` showed the phone on 5G as
`direct <carrier IP>:<port>` instead of `relay "tor"`, `tailscale ping` answered via the direct
address, and 5 pings had 0% loss (28-160 ms; the spread is the phone's radio waking up).

**If DNS or pages fail on Tailscale again**, check in this order:

```bash
ssh tailscale 'tailscale status'                       # phone direct or relay?
ssh tailscale 'tailscale status --json | python3 -c "import json,sys;print(json.load(sys.stdin)[\"Self\"][\"Addrs\"])"'
                                                        # must include <public IP>:41641
ssh tailscale 'journalctl -u tailscaled --since -1h | grep "does not know about peer"'
```

No `:41641` endpoint means the forward is gone (router reset or firmware update) or the port changed.
To see whether queries arrive and get answered, run `tcpdump -i tailscale0 -nn host <device tailnet IP>`
on CT 125 (tcpdump is installed there); a query without a reply is a home problem, a reply followed by
the same query again means replies are not reaching the device.

## Operating it

```bash
ssh tailscale 'tailscale status'            # peers and how they connect (direct vs relay)
ssh tailscale 'tailscale netcheck'          # NAT type, nearest relay
ssh tailscale 'tailscale dns status --all'  # DNS config pushed by the tailnet
ssh tailscale 'apt-get update && apt-get -y upgrade'   # update Tailscale
```

Admin console tasks (Ammar): add/remove devices, approve routes, key expiry, DNS, ACLs.

## Known limitations

- If CT 125 or the host is down, remote access is down. Devices with "Override DNS servers" lose DNS
  while connected to Tailscale if AdGuard is unreachable; turning Tailscale off restores local DNS.
- The tailnet's DNS points at a home IP: when a device is on Tailscale and at home, it still works (the
  subnet route and the LAN are the same network).
