# AdGuard Home (CT 120)

Network-wide DNS with ad and tracker blocking for the whole house.

| | |
|---|---|
| Container | LXC 120 `adguard`, unprivileged Debian 13, 1 core, 512 MB RAM + 512 MB swap, 4 GB disk |
| IP | `10.77.0.20/24` (static), gateway and OS resolver `10.77.0.1` |
| Boot | `onboot=1`, `startup order=1` (first guest to start), tag `dns` |
| Version | AdGuard Home v1.0.0 (released 2026-11-19); installed as v0.107.80, updated 2026-11-22 with the UI's built-in updater (config schema 34 to 35) |
| Install path | `/opt/AdGuardHome` (mode 0700), systemd unit `AdGuardHome` |
| Web UI | `http://adguard.home.arpa` or `http://10.77.0.20` (port 80). Ammar's login only. In the built-in browser pane use the hostname: by IP it blocks the login script and the page stays blank. |
| DNS | UDP/TCP 53 on all interfaces |
| SSH | `ssh adguard` |

Why AdGuard Home over Pi-hole and others: [decisions.md](../decisions.md).

## How it was installed

1. Container created per the standard in [proxmox.md](../proxmox.md) (with `--nameserver 10.77.0.1`
   because it is the DNS server itself).
2. `apt-get full-upgrade`, then `curl ca-certificates jq`.
3. Release downloaded from `github.com/AdguardTeam/AdGuardHome/releases` and checked against the
   release's `checksums.txt` (entries are named `./AdGuardHome_linux_amd64.tar.gz`):
   ```bash
   grep " ./AdGuardHome_linux_amd64.tar.gz$" checksums.txt | sha256sum -c -
   ```
4. Extracted to `/opt`, installed as a service with `/opt/AdGuardHome/AdGuardHome -s install`.
5. Ammar ran the first-run wizard at `:3000`: web UI on all interfaces port 80, DNS on all interfaces
   port 53, admin account.
6. Settings applied by [scripts/adguard/configure.py](../../scripts/adguard/configure.py) (needs
   `python3-yaml` in the container), with the service stopped and the original backed up as
   `AdGuardHome.yaml.bak-20261117-015047`, then validated with `--check-config`.

## Our settings and why

| Setting | Value | Why |
|---|---|---|
| `filtering.filtering_enabled` | `true` | Wizard default was `false`: lists loaded but nothing was blocked |
| Blocklists | AdGuard DNS filter (id 1), HaGeZi Multi PRO (id 1700000001); AdAway off | About 430k rules, low false positives |
| `dns.upstream_dns` | `https://dns.quad9.net/dns-query`, `https://cloudflare-dns.com/dns-query` | Encrypted (DoH); Quad9 also blocks malware |
| `dns.upstream_mode` | `parallel` | Fastest answer wins, survives one upstream failing |
| `dns.bootstrap_dns` | Quad9 and Cloudflare IPs (v4 + v6) | Only used to resolve the DoH hostnames |
| `dns.fallback_dns` | `9.9.9.9`, `1.1.1.1` | Plain DNS only if both DoH upstreams are unreachable |
| `dns.ratelimit` | `0` | Default 20 qps per /24 throttled the whole LAN as one client; LAN-only server |
| `dns.enable_dnssec` | `true` | Rejects forged answers |
| `dns.cache_optimistic` | `true` | Instant answers from cache, refreshed in the background |
| `dns.local_ptr_upstreams` | `10.77.0.1` | Reverse lookups for LAN IPs go to the router (device names) |
| Query log / statistics | 30 days each (`720h`) | Enough history for debugging and charts, less retained data |
| `filtering.rewrites` | Local `*.home.arpa` names (list in [network.md](../network.md#local-names)) | Services by name instead of IP; explicit entries, no wildcard |

To re-apply after a reinstall:

```bash
scp scripts/adguard/configure.py adguard:/root/
ssh adguard 'apt-get -y install python3-yaml && systemctl stop AdGuardHome \
  && cp -p /opt/AdGuardHome/AdGuardHome.yaml /opt/AdGuardHome/AdGuardHome.yaml.bak-$(date +%Y%m%d-%H%M%S) \
  && python3 /root/configure.py \
  && /opt/AdGuardHome/AdGuardHome --check-config -c /opt/AdGuardHome/AdGuardHome.yaml -w /opt/AdGuardHome \
  && systemctl start AdGuardHome'
```

## Verification (2026-11-17)

From the laptop, with [scripts/dnstest.py](../../scripts/dnstest.py) and then through the system
resolver after the router change:

| Query | Result |
|---|---|
| `example.com`, `github.com` | Real IPs, 6-10 ms first, ~2 ms cached |
| `doubleclick.net`, `googleadservices.com` | `0.0.0.0` (blocked) |
| `ads.google.com` | Real IPs (advertiser website, intentionally not blocked by the lists) |
| `dnssec-failed.org` | `SERVFAIL` (DNSSEC validation works) |

```bash
python3 -I scripts/dnstest.py 10.77.0.20 example.com doubleclick.net dnssec-failed.org
```

## Operating it

### In the web UI (`http://10.77.0.20`)

| Menu | Use it for |
|---|---|
| Dashboard | Query volume, % blocked, top clients, top blocked domains |
| Query Log | Every lookup, live. Click an entry to Block or Unblock that domain. First stop when a site or app breaks. |
| Filters > DNS blocklists | Enable/disable/add lists, force an update |
| Filters > Custom filtering rules | Own rules: `\|\|example.com^` blocks, `@@\|\|example.com^` allows |
| Filters > DNS rewrites | Local names (managed by `configure.py`; add new ones there so they survive a re-apply) |
| Filters > Blocked services | One-click service blocking with schedules |
| Settings > DNS settings | Upstreams, bootstrap, fallback, cache, DNSSEC, rate limit |
| Settings > General settings | Log/stats retention, safe search, parental control |
| Settings > Client settings | Name devices, give them their own rules |

### On the command line

```bash
ssh adguard 'systemctl status AdGuardHome'
ssh adguard 'journalctl -u AdGuardHome -f'
```

Editing `AdGuardHome.yaml` by hand: AdGuard rewrites the file when settings change in the UI, so
always `systemctl stop AdGuardHome` first, back the file up, edit, validate with `--check-config`,
then start it.

### Changing the web UI password

AdGuard Home has no password change in its UI: the login is a bcrypt hash under `users:` in
`AdGuardHome.yaml`. The login page's "Forgot password?" (v1.0.0) describes the same manual edit and
suggests an online bcrypt generator; don't use one (it sends the password to a third party). [scripts/adguard/set-password.py](../../scripts/adguard/set-password.py) changes
it. Ammar runs it (it prompts for the password with no echo; the password and hash are never printed):

```bash
scp scripts/adguard/set-password.py adguard:/root/
ssh -t adguard 'apt-get -y install python3-bcrypt python3-yaml && python3 /root/set-password.py'
```

It prompts before stopping the service (DNS is down only for the few seconds of the write), backs up
the YAML as `AdGuardHome.yaml.bak-<timestamp>`, validates with `--check-config` (restoring the backup
on failure), clears `data/sessions.db` so every browser must log in again, and starts the service.
Nothing else uses the AdGuard login (Homepage only pings the page). Old `.bak-*` files and
`agh-backup/AdGuardHome.yaml` contain earlier hashes; they are root-only (0600 in a 0700 directory).
Tested on v1.0.0 (2026-11-24): the YAML round-trip is structurally identical and passes `--check-config`.

### Updating AdGuard Home

The UI shows when a new version exists. Prefer the same verified method as the install: download the
new release and `checksums.txt`, verify, stop the service, replace `/opt/AdGuardHome/AdGuardHome`,
start, run the verification queries above, and update the version in this file.

The UI's own updater was used once (v0.107.80 to v1.0.0, 2026-11-22). It downloads from
`static.adtidy.org` and keeps the previous binary and config in `/opt/AdGuardHome/agh-backup/` (roll
back by stopping the service and copying them back).

## Known limitations

- **YouTube ads are not blocked, by design.** Video ads stream from the same `*.googlevideo.com`
  servers as the videos, and feed/sponsored cards come through `youtubei.googleapis.com`; blocking
  either breaks YouTube. AdGuard does block YouTube's ad tracking (`googleads.g.doubleclick.net`,
  `pubads.g.doubleclick.net`, `pagead2.googlesyndication.com`, verified in the query log
  2026-11-17). Use a browser blocker (uBlock Origin) or YouTube Premium instead. Sponsor segments read
  inside a video are part of the video itself (SponsorBlock skips those).
- Single instance: when CT 120 or the Proxmox host is down, the house has no DNS. Plan: second
  instance on separate hardware with `adguardhome-sync` ([roadmap.md](../roadmap.md)).
- No encrypted DNS for clients (DoH/DoT server) yet; needs a certificate, comes with Caddy and a domain.
- Client names in the logs depend on the router answering reverse lookups; not yet verified.
