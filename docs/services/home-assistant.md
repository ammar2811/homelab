# Home Assistant (VM 121)

| | |
|---|---|
| VM | 121 `homeassistant`, q35 + OVMF (UEFI, `pre-enrolled-keys=0`: HAOS does not support Secure Boot), `cpu host`, 2 cores, 4 GB RAM, 32 GB disk on `local-lvm` (discard, SSD hint) |
| OS | Home Assistant OS 18.4 (generic x86-64 / OVA build) |
| IP | `10.77.0.21/24` static (set inside HA), gateway `10.77.0.1`, DNS `10.77.0.20` |
| URL | `http://homeassistant.home.arpa` (also `http://10.77.0.21`) |
| Web port | **80** (this HA version's default, shown under Settings > System > Network > HTTP server; 8123 only redirects) |
| Boot | `onboot=1`, `startup order=3` (after DNS and Tailscale), tag `homeassistant` |
| Guest agent | Built into HAOS; Proxmox shows its IP and can shut it down cleanly |
| Accounts | Owner account created by Ammar during onboarding (his only) |

## How it was installed (2026-11-17)

1. Picked the image: HAOS 18.5 is a Raspberry Pi-only release; 18.4 is the current build for x86/VMs
   and already contains 18.5's kernel fix.
2. Downloaded `haos_ova-18.4.qcow2.xz` from `github.com/home-assistant/operating-system/releases/tag/18.4`
   and verified it against the SHA-256 GitHub records for the asset
   (`756ec485b1b153099ca53e88a5eebd63a801d56b791afe5c6d63ef94a35dc02d`). Unpacked copy kept in
   `/root/images/` on the host.
3. Created the VM:
   ```bash
   qm create 121 --name homeassistant --machine q35 --bios ovmf \
     --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=0 \
     --cpu host --cores 2 --memory 4096 --scsihw virtio-scsi-single \
     --scsi0 local-lvm:0,import-from=/root/images/haos_ova-18.4.qcow2,discard=on,iothread=1,ssd=1 \
     --net0 virtio,bridge=vmbr0 --boot order=scsi0 --ostype l26 --agent enabled=1 \
     --onboot 1 --startup order=3 --tags homeassistant
   ```
4. First boot took a DHCP address (`10.77.0.198`); HA's core downloaded in under a minute.
5. Ammar ran onboarding (owner account, location, units).
6. Static IPv4 set in Settings > System > Network > IPv4: Static, `10.77.0.21`, netmask
   `255.255.255.0`, gateway `10.77.0.1`, DNS `10.77.0.20`. IPv6 left as is.
7. AdGuard rewrite `homeassistant.home.arpa -> 10.77.0.21` (in `scripts/adguard/configure.py`) and a
   Homepage entry with a live status check.

Verified: HTTP 200 on `10.77.0.21` and by name, the old DHCP address no longer answers, the guest
agent reports `10.77.0.21`.

## Not behind Caddy (yet)

HA is reached directly on its own IP. Putting it behind Caddy later (for HTTPS) needs
`http: use_x_forwarded_for: true` and `trusted_proxies: [10.77.0.30]` in HA's `configuration.yaml`,
otherwise HA rejects proxied requests.

## Integrations

| Integration | Status |
|---|---|
| Google Cast (Google Home Mini) | Added. The Mini is `media_player.bedroom_speaker` ("Google Home Mini", area Bedroom). Discovery uses mDNS, so the Mini must stay on the main network |
| Mobile App (Pixel 9) | Registered; `device_tracker.pixel_9` (GPS), notifications via `notify.mobile_app_pixel_9` |
| Google Translate TTS | `tts.google_translate_en_com` (set up by onboarding) |
| Command line | The 7 homelab checks (see below) |
| Remote Calendar | "Garbage collection" -> `calendar.garbage_collection`, the municipality's iCal feed for the address |
| ESPHome | Desk lamp (ESP32 relay, `desk-lamp`, `10.77.0.130`) added 2026-11-19 as "Bedroom Desk Lamp": `switch.bedroom_desk_lamp_lamp`, Wi-Fi signal and uptime sensors, restart button. Firmware lives in the separate `Smart-Desk-Lamp-IoT-System` repo; its API encryption key is in that repo's gitignored `secrets.yaml`. It must stay on the main network (decision 2026-11-16). Weak 2.4 GHz link, see roadmap |
| Zigbee/Thread | Not yet; no Zigbee/Thread devices yet. Needs a coordinator (SMLIGHT SLZB-06 preferred) |
| Voice ("Hey Google") | Not set up; needs Home Assistant Cloud (Nabu Casa) or a manual Google project, see roadmap |

## Config as code

| | |
|---|---|
| Access | Official **Terminal & SSH** app (Settings > Apps; "add-ons" were renamed "Apps"), v10.6.0, port 22, key auth only (laptop key in its Authorized Keys option), Watchdog and start on boot on, shown in the sidebar as "Terminal" |
| SSH | `ssh homeassistant` (root in the app container; HA config at `/homeassistant`, `/config` links to it). Host key `SHA256:Is0Klf3FBJGSURrTOMNPbPp/U94pORu74fQJAK33q8Q`, verified through the app's web terminal |
| Source of truth | [homeassistant/](../../homeassistant/) in this repo: `configuration.yaml` (adds `packages: !include_dir_named packages`) and one package file per feature |
| Deploy | `scripts/deploy-homeassistant.sh` copies the files (mirrors `packages/`), runs `ha core check`, restores the previous `configuration.yaml` if the check fails, keeps 5 backups, then `ha core restart` (`--check` to skip the restart) |
| UI-owned files | `automations.yaml`, `scripts.yaml`, `scenes.yaml` stay UI-managed and are not in git |

Limits of the SSH app: it may use the Supervisor API (`ha ...`: check, restart, logs) but **not** HA's
core API (401), so it cannot read states or call services. To verify, read the recorder database
read-only: `apk add --no-cache sqlite` inside the app (temporary, gone on app restart), then query
`/homeassistant/home-assistant_v2.db` (`states` joined with `states_meta`). Saved automation traces
are only written on shutdown. Never read `.storage/auth*` or the mobile app's webhook secrets.

## Automations (packages)

### Homelab service-down alerts ([homelab_monitoring.yaml](../../homeassistant/packages/homelab_monitoring.yaml))

Seven `command_line` connectivity sensors, checked every 60 s from inside HA, grouped as
`group.homelab_services`:

| Sensor | Check |
|---|---|
| `binary_sensor.internet` | `https://www.google.com/generate_204` returns 204 |
| `binary_sensor.router` | `http://10.77.0.1/` answers 2xx/3xx |
| `binary_sensor.proxmox` | `https://10.77.0.10:8006/` answers |
| `binary_sensor.adguard_dns` | real DNS lookup of example.com against `10.77.0.20` |
| `binary_sensor.tailscale` | ping `10.77.0.25` |
| `binary_sensor.jellyfin` | `/health` says `Healthy`, through Caddy (tests the proxy too) |
| `binary_sensor.homepage` | Homepage via Caddy returns 200 |

Down for 2 minutes -> phone notification "X is down" (channel "Homelab alerts", high importance,
tap opens Homepage). Recovery after an outage of 2+ minutes replaces it with "X is back, down for N min"
(same notification tag).

Verified 2026-11-17 by stopping the Homepage container for 3.5 min: sensor off 13 s after the stop,
down alert at exactly +2 min, recovery 40 s after restart; both notifications arrived on the phone.

### Garbage-day reminder ([garbage_day.yaml](../../homeassistant/packages/garbage_day.yaml))

At 20:00, reads tomorrow's events from `calendar.garbage_collection`; if any, the Home Mini says
"Reminder: tomorrow is collection day. Put out the <streams>." and the phone gets "Collection tomorrow".
Holiday shifts come from the municipal calendar. The iCal URL identifies the address and lives only in HA.

Verified 2026-11-17 with a temporary copy looking two days ahead: it found Thursday's
"Organics and yard waste", the Mini played the announcement (6 s), the phone got the notification.
The copy was removed and its leftover entity deleted (Settings > Devices & services > Entities).

## Presence

- Person `person.ammar_siddiqui` follows `device_tracker.pixel_9` (GPS from the companion app).
  First location 2026-11-17 13:06 (`home`). The home zone is set in HA (not recorded here).
- Phone settings needed: app server URL and internal URL `http://homeassistant.home.arpa`; location
  sensors (background location, location zone, single accurate location) with "Allow all the time";
  battery "Unrestricted"; Tailscale **Always-on VPN**.
- Why always-on Tailscale, even at home: Android's Tailscale app cannot switch itself on when leaving
  home Wi-Fi, and the "left home" location update is lost if HA is unreachable at that moment. Cost:
  at home the phone reaches `10.77.0.x` and DNS through CT 125, so if Tailscale is down, toggle it off
  (the Tailscale check above alerts on that). Alternative without a VPN: Home Assistant Cloud.

## Operating it

- Updates: Settings > System > Updates (HA Core, OS and apps). HA keeps its own backups before
  updates if enabled (Settings > System > Backups); Proxmox backups of VM 121 come with the backup plan.
- Console: the Terminal sidebar entry, `ssh homeassistant`, or Proxmox > VM 121 > Console.
- Logs: `ssh homeassistant 'ha core logs'`.
- Memory: 4 GB fixed; after it started, the host had 3.6 GiB available (2026-11-17).

## Known limitations

- **Alerts cannot report a Proxmox host outage**: HA runs on that host. Fix idea: an external
  dead-man's switch (e.g. HA pinging a free Healthchecks.io check every few minutes, which emails if the
  pings stop). See roadmap.
- No backups yet beyond what HA can do internally (no off-box target).
- Remote access is via Tailscale only (no Nabu Casa / public exposure).
- HA logged one SSDP "Network unreachable" error at 12:56 (around the IP change); not seen since.
