# Homelab - Agent Instructions

This repository is the single source of truth for Ammar's home lab: what exists, how it was built,
why it was built that way, and how to operate it. If something on the network is not described here,
treat it as undocumented drift and either document it or flag it.

Read this file fully before acting. Then read the doc for whatever you are about to touch
(see "Where things are documented" below).

## Ground rules

1. **Verify before you state.** Facts in these docs were true when written. Before relying on an IP,
   version, setting or service state, check the live system (SSH, `pct config`, the config file).
   If the docs disagree with reality, reality wins: fix the docs in the same change.
2. **Never handle secrets.** Never type, store, log or commit passwords, passphrases, API tokens,
   password hashes or recovery codes. Logins (router, Proxmox web UI, AdGuard UI, wizards) are done by
   Ammar. When reading config files that contain credentials (e.g. `users:` in `AdGuardHome.yaml`),
   redact them in output. If a secret appears in chat or a terminal, tell Ammar and do not repeat it.
3. **Ask before outward-facing or hard-to-reverse actions**: router changes, deleting or recreating
   VMs/containers, wiping disks, reboots of the Proxmox host while services run, exposing anything to
   the internet. State exactly what will change first.
4. **Keep the Proxmox host minimal.** Do not install extra software on `pve` beyond what Proxmox
   needs and small admin tools. Services live in containers or VMs, never on the host.
5. **Nothing is exposed to the internet.** UPnP stays off. The only port forward is UDP 41641 to
   Tailscale on CT 125 (decision 2026-11-22). Remote access is Tailscale only. Do not change this
   without an explicit decision recorded in [docs/decisions.md](docs/decisions.md).
6. **Every change is documented here in the same session**: update the relevant doc, the IP plan,
   and add a decision entry when a choice was made between real alternatives.
7. **Prove it works end to end.** After any change, test it the way a user experiences it (e.g. DNS
   queries from the laptop, page loads from a browser), not just "the service is active".
8. **Read the output yourself.** Do not accept a user's relayed "OK" for something you can check;
   read the terminal or run the check. (A flashed USB stick was once reported OK when it had failed.)
9. **Writing style** (from Ammar's global instructions): never use the em dash character; use a plain
   hyphen. No co-author lines in commit messages. Prefer quality, robustness and long-term
   maintainability over development cost.

## Environment at a glance

| Thing | Value |
|---|---|
| ISP | Rogers fiber, 2.5 Gbps, ONT straight into our router (Rogers XB8 removed) |
| Router | TP-Link Archer BE550 at `10.77.0.1` (web UI, Ammar logs in) |
| LAN | `10.77.0.0/24`, DHCP pool `.100-.249`, no IPv6 on the LAN |
| DNS for the house | AdGuard Home at `10.77.0.20` (router hands it out as primary and secondary) |
| Docker VM | VM 130 at `10.77.0.30`: Caddy, Jellyfin, Homepage; iGPU passed through |
| Remote access | Tailscale, CT 125 at `10.77.0.25`: subnet router for `10.77.0.0/24` + exit node; tailnet DNS = AdGuard |
| Home Assistant | HAOS VM 121 at `10.77.0.21`, web on port 80 (`http://homeassistant.home.arpa`); SSH via the Terminal & SSH app |
| Local names | `*.home.arpa` via AdGuard rewrites, e.g. `http://homepage.home.arpa`, `http://jellyfin.home.arpa` |
| Hypervisor | Proxmox VE 9.2 on Dell OptiPlex 5060 SFF, `pve.home.arpa`, `10.77.0.10` |
| Proxmox web UI | `https://10.77.0.10:8006` (self-signed cert; the built-in browser pane refuses it) |
| Intel AMT | `10.77.0.208` (DHCP, not yet reserved), ports 16992+ |
| Admin workstation | Ammar's laptop (Arch/Omarchy, NetworkManager, Wi-Fi), on DHCP |

Full IP plan: [docs/network.md](docs/network.md).

## Access

SSH from the laptop uses key auth through a systemd user `ssh-agent`
(`$XDG_RUNTIME_DIR/ssh-agent.socket`, configured in `~/.ssh/config`). The key has a passphrase, so
after a laptop reboot Ammar must unlock it once:

```bash
ssh-add ~/.ssh/id_ed25519
```

If SSH fails with `Permission denied (publickey)`, the key is probably not unlocked; ask Ammar to run
the command above. Do not try to work around it.

| Alias | Target | Notes |
|---|---|---|
| `ssh pve` | `root@10.77.0.10` | Proxmox host |
| `ssh adguard` | `root@10.77.0.20` | AdGuard container (CT 120) |
| `ssh docker` | `root@10.77.0.30` | Docker VM (VM 130) |
| `ssh tailscale` | `root@10.77.0.25` | Tailscale container (CT 125) |
| `ssh homeassistant` | `root@10.77.0.21` | Home Assistant's Terminal & SSH app (config in `/homeassistant`) |

Use `ssh -o BatchMode=yes <alias> '...'` for non-interactive commands so a missing key fails fast
instead of prompting.

Anything needing `sudo` on the laptop must run in a terminal tab where Ammar types the password;
never pipe or type it yourself.

## Conventions

- **IDs match IPs**: container/VM ID = 100 + last octet of its IP. CT 120 is `10.77.0.20`, the planned
  Home Assistant VM is 121 (`.21`), the planned Docker VM is 130 (`.30`).
- **Static IPs live in `.2-.99`** and are set on the guest itself (outside the DHCP pool, so no
  router reservation needed). DHCP clients get `.100-.249`.
- **Hostnames**: short lowercase names; domain `home.arpa` (RFC 8375) until a real domain is chosen.
  Never use `.local` (it breaks mDNS used by Home Assistant, Cast and AirPlay).
- **Containers**: unprivileged Debian 13 LXC from the official Proxmox template, `nesting=1`,
  `onboot=1`, a `--tags` value, a `--description` with the service URL, and the laptop's SSH key.
  Infrastructure that others depend on (DNS) gets `--startup order=1`.
- **Software installs**: prefer distro packages; otherwise official upstream releases verified
  against published checksums before running anything. No `curl | sh`.
- **Config edits to services**: back up the file first (`cp -p f f.bak-YYYYMMDD-HHMMSS`), stop the
  service if it rewrites its own config (AdGuard does), validate if the tool supports it, restart,
  then test end to end.
- **Scripts that configure things** belong in [scripts/](scripts/) so the setup is reproducible.
- **Docker services** are defined only in [docker/](docker/) and deployed with
  `scripts/deploy-docker.sh` (run `--dry-run` first). Never edit `/opt/homelab` on the VM directly; it
  is overwritten (`rsync --delete`). Pin image tags to exact versions. App state goes in
  `/srv/appdata/<app>`, run containers as `1000:1000` (`media`), never mount the Docker socket.
- **A new web service** needs: a service in `compose.yaml`, a site block in the Caddyfile, a rewrite in
  `scripts/adguard/configure.py` (then re-apply it), a Homepage entry, and docs.
- **Home Assistant automations** live in [homeassistant/packages/](homeassistant/packages/) (one file
  per feature) and are deployed with `scripts/deploy-homeassistant.sh` (`--check` to validate without
  restarting). Don't edit them in HA's UI; UI-made automations go to `automations.yaml`, which is not
  in git. Personal data (calendar URLs with addresses, home coordinates) stays in HA, never in the repo.
  To test a time-triggered automation, deploy a temporary copy with a near trigger time, then remove it
  and delete its leftover entity (Settings > Devices & services > Entities).
- **Guest VMs** come from the verified Debian cloud image per [docs/proxmox.md](docs/proxmox.md);
  verify the SSH host key out of band through `qm guest exec`.

## Where things are documented

| Topic | File |
|---|---|
| Overview and status | [README.md](README.md) |
| Network, IP plan, router settings, DNS flow | [docs/network.md](docs/network.md) |
| Hardware, BIOS, Intel AMT | [docs/hardware.md](docs/hardware.md) |
| Proxmox host: install, storage, repos, access | [docs/proxmox.md](docs/proxmox.md) |
| AdGuard Home (CT 120) | [docs/services/adguard-home.md](docs/services/adguard-home.md) |
| Docker VM 130, Caddy, Jellyfin, Homepage | [docs/services/docker-vm.md](docs/services/docker-vm.md) |
| Tailscale (CT 125) | [docs/services/tailscale.md](docs/services/tailscale.md) |
| Home Assistant (VM 121) | [docs/services/home-assistant.md](docs/services/home-assistant.md) |
| Why things are the way they are | [docs/decisions.md](docs/decisions.md) |
| What is planned next, open issues | [docs/roadmap.md](docs/roadmap.md) |

## Known gotchas (learned the hard way)

- **BE550 DHCP DNS**: if Secondary DNS is left empty, the router silently hands out itself as a second
  DNS server, and clients bypass AdGuard. Both Primary and Secondary must be `10.77.0.20`.
- **AdGuard first-run defaults** ship with `filtering_enabled: false` (lists load but block nothing)
  and `ratelimit: 20` per /24 (throttles the whole LAN as one client). Check both after any reinstall.
- **AdGuard rewrites its own YAML**; edit only with the service stopped.
- **USB flashing from the laptop** silently corrupted images on two different sticks with both `dd`
  and caligula (writes reported success but did not land). Flash installers from another computer
  (Rufus on a Windows PC worked) and always verify the result against the ISO before booting. Check the
  image architecture too: one stick came back with an ARM64 (`bootaa64.efi`) build that cannot boot here.
- **The browser pane** cannot open self-signed HTTPS (Proxmox UI); Ammar opens those in his own browser.
- **Router sessions expire**; Ammar must log in again in the browser pane before router changes.
- **Laptop networking** is NetworkManager (not systemd-networkd); reconnect with
  `nmcli connection up <name>` to pick up DHCP changes.
- **After a laptop reboot** the ssh-agent is empty; Ammar runs `ssh-add` once (the shell finds the
  agent via `SSH_AUTH_SOCK` set in `~/.bashrc`).
- **Host reboots take DNS down** for the whole house for about a minute (CT 120 restarts with it).
  Right after boot, the first lookups through AdGuard can time out while it connects to its upstreams.
- **Tailscale admin console settings** (route approval, key expiry, DNS, ACLs) belong to Ammar's
  account; guide him, verify from the node with `tailscale status --json` and
  `tailscale dns status --all`. The "Override DNS servers" toggle only appears after a global
  nameserver is added.
- **Home Assistant's UI is shadow DOM**: browser find/read tools see nothing; work from screenshots,
  and confirm field values with a zoom before saving (a stale highlight once led to a doubled IP).
  Newer HAOS listens on port 80 by default, not 8123. HAOS releases can be Raspberry Pi only; check
  the release has a `haos_ova-*` asset before choosing a version.
- **The HA SSH app cannot use HA's core API** (401; only `ha ...` Supervisor commands work). Read
  states from the recorder DB with a temporary `apk add --no-cache sqlite`. Never read `.storage/auth*`
  or mobile app webhook secrets. `.storage` files are written with a delay (a deleted entity can take a
  few minutes to leave `core.entity_registry`). Add-ons are called "Apps" in this HA version.
- **Navigating HA in the browser pane**: click through the app; loading deep links directly has
  triggered a fresh login. The HA web terminal ignores pasted text; send commands as individual
  keystrokes (`key` with literal characters).
- **RAM is the tight resource**: about 3.6 GiB free with VMs 121 and 130 running. Check
  `free -m` on the host before adding guests.
- **"DNS unavailable" in Tailscale on mobile data** was not AdGuard: replies were dropped at a stale
  DERP relay. Fixed by the UDP 41641 forward; if it returns, check the phone is `direct` and the node
  advertises `:41641` (see [docs/services/tailscale.md](docs/services/tailscale.md)).
- **Remote devices appear in AdGuard as `10.77.0.25`** (the subnet router SNATs), not as themselves.
- **Debian cloud images use a cloud kernel without GPU drivers**; VMs that need the iGPU must switch to
  `linux-image-amd64` (see [docs/services/docker-vm.md](docs/services/docker-vm.md)).

## Publishing (public copy)

This repo is private and keeps every detail. A public showcase copy is generated from it by
`scripts/build-public.py`: it takes the last commit (`git archive HEAD`), applies
`publish/redactions.tsv` (REPLACE / DROPLINE / FORBID rules), fails if any listed personal detail
remains, and commits into the separate public repo (default `../homelab-public`). It never pushes.
`--preview [DIR]` builds from the working tree into a scratch folder with no git activity.

| | |
|---|---|
| Public repo | https://github.com/ammar2811/homelab (public, MIT, default branch `main`) |
| Local clone | `/home/ammar/Repos/homelab-public` (remote `origin`), built only by the script, never edited by hand |
| Commit identity | Set in that clone's git config (GitHub no-reply address); never the private repo's address |
| History | One commit per publish ("Publish from private repo <sha>"); private history is never published |
| First published | 2026-11-17, from private commit `8ab1074` |

Update flow (push only when Ammar asks):

```bash
scripts/build-public.py                       # after committing here; builds and commits the public copy
git -C ../homelab-public push                 # publish
```

- **Never strip details from this repo to make it publishable**; add a rule to `publish/redactions.tsv`
  instead. `publish/` itself is never published.
- When you write something personal into the docs (addresses, location, account names, tailnet name,
  Tailscale IPs, MAC addresses, Wi-Fi names, emails, public IP), add a matching rule in the same change.
- Pushing the public repo is outward-facing: only when Ammar asks.

## Before you finish a session

- Docs updated for everything that changed (including versions and the IP plan).
- New decisions recorded with their reasons and the alternatives rejected.
- Open problems you noticed but did not fix are listed in [docs/roadmap.md](docs/roadmap.md).
