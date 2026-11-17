# Docker VM (VM 130) and its services

| | |
|---|---|
| VM | 130 `docker`, q35 + OVMF (UEFI), 4 cores (`cpu: host`), 6 GB RAM (no ballooning), 64 GB disk on `local-lvm` (discard, SSD hint) |
| IP | `10.77.0.30/24` static via cloud-init, DNS `10.77.0.20`, search `home.arpa` |
| OS | Debian 13 from the official cloud image, switched to the standard kernel (`linux-image-amd64`, 6.12) |
| GPU | Intel UHD 630 (`00:02.0`) passed through as `hostpci0`; inside the VM at `06:10.0`, `/dev/dri/renderD128` |
| Boot | `onboot=1`, `startup order=2` (after DNS), tag `docker` |
| Console | Serial only (`vga: serial0`); use `qm terminal 130` on the host or `ssh docker` |
| SSH | `ssh docker` (root, laptop key via cloud-init) |
| Docker | Debian packages: docker.io 26.1.5, docker-compose 2.26.1; `/etc/docker/daemon.json` uses the `local` log driver, 10 MB x 3 per container |

## Layout on the VM

| Path | What | In git? |
|---|---|---|
| `/opt/homelab` | Copy of this repo's [docker/](../../docker/) (compose file, Caddyfile, Homepage config) | Yes (source of truth is the repo) |
| `/srv/appdata/<app>` | App state (Jellyfin database and metadata, Caddy data) | No, needs backups |
| `/srv/media/{movies,tv}` | Media library (on the VM disk until the media HDD arrives) | No |

User `media` (UID/GID 1000, no login) owns `/srv/media` and `/srv/appdata/jellyfin`; containers run as
1000:1000. Group `render` is GID 991 on the VM (used by Jellyfin's `group_add`).

## Services

| Service | Image (pinned) | URL | Notes |
|---|---|---|---|
| Caddy | `caddy:2.11.9` | | Reverse proxy on port 80, routes by hostname ([Caddyfile](../../docker/caddy/Caddyfile)). Bare IP / unknown names redirect to Homepage. HTTP only until a domain exists. |
| Jellyfin | `jellyfin/jellyfin:12.4` | `http://jellyfin.home.arpa` | Quick Sync on. Media mounted read-only. UDP 7359 published for client auto-discovery. |
| Homepage | `ghcr.io/gethomepage/homepage:v2.8.0` | `http://homepage.home.arpa` | Config in [docker/homepage/](../../docker/homepage/). No Docker socket access (security). |

Names resolve via AdGuard rewrites (see [adguard-home.md](adguard-home.md)).

## Deploying changes

Edit files under `docker/` in this repo, then:

```bash
scripts/deploy-docker.sh --dry-run   # show what would change on the VM
scripts/deploy-docker.sh             # rsync to /opt/homelab, validate, pull, up -d
```

The script uses `rsync --delete`, so files that only exist on the VM are removed. Homepage creates
default files on first start (`docker.yaml`, `kubernetes.yaml`, `logs/`) and on the first page load in
a browser (`proxmox.yaml`, `custom.css`, `custom.js`); all of these are kept in the repo and
`homepage/logs/` is excluded. If a dry run shows `*deleting homepage/...`, copy that file into the repo.

Upgrading an image: change the tag in [docker/compose.yaml](../../docker/compose.yaml), deploy, test,
and update the versions table here. Check release notes first (Jellyfin major versions migrate the
database; back up `/srv/appdata/jellyfin` before).

## Jellyfin

- Setup wizard done by Ammar (admin account is his). Libraries: Movies `/media/movies`, Shows `/media/tv`.
- Server name `jellyfin` comes from the container `hostname:` (otherwise it is the random container ID).
- Hardware transcoding was set in `/srv/appdata/jellyfin/config/config/encoding.xml` (container stopped,
  backup `encoding.xml.bak-*`):

  | Setting | Value |
  |---|---|
  | Hardware acceleration | Intel QuickSync (QSV), device `/dev/dri/renderD128` |
  | Hardware decoding | h264, hevc, mpeg2video, vc1, vp8, vp9 (+ HEVC/VP9 10-bit). No AV1 on Coffee Lake. |
  | Hardware encoding | on, H.264 output (HEVC encoding off for client compatibility) |
  | Tone mapping | on (+ VPP tone mapping) for HDR -> SDR |
  | Intel low-power encoders | off (not needed on this generation) |

  These are also visible and editable in Dashboard > Playback > Transcoding.

### Verification (2026-11-17)

- `vainfo` in the VM and in the container: Intel iHD driver, H.264/HEVC Main10 decode and encode.
- Synthetic test clip `/srv/media/movies/Test Pattern (2026)/Test Pattern (2026).mkv` (60 s, 1080p,
  HEVC Main 10, generated with ffmpeg testsrc2). Manual QSV transcode to H.264: 5.1 s; `intel_gpu_top`
  showed Video 87-100%, Render 90-100%, VideoEnhance ~33%.
- Real playback from Jellyfin Web: Jellyfin chose `-hwaccel vaapi` decode, `scale_vaapi` 10->8 bit,
  `h264_qsv` encode; 280 fps, 10.6x real time, no errors in the transcode log.

To check during a playback:

```bash
ssh docker 'intel_gpu_top'                                         # Video engine busy = GPU working
ssh docker 'ls -t /srv/appdata/jellyfin/config/log/FFmpeg.Transcode-*.log | head -1 | xargs grep -m1 "Stream #0:0 ->"'
```

## Planned for this VM

- With the media HDD: Sonarr, Radarr, Prowlarr, Bazarr, Seerr, qBittorrent behind gluetun (VPN), and
  possibly Stremio's streaming server (same VPN). `/data` layout per TRaSH Guides for hardlinks.
- Tailscale, Immich (after a photo backup plan).
- With a domain: HTTPS in Caddy via DNS challenge.

## Gotchas

- Debian's cloud image ships `linux-image-cloud-amd64`, which has **no i915 driver**: `/dev/dri` stays
  missing. The standard kernel plus `firmware-intel-graphics` and `intel-media-va-driver-non-free`
  (needs `contrib non-free non-free-firmware` in apt sources) are required.
- Jellyfin's `/media` is read-only by design; write test files via `/cache` and move them on the VM.
- PCI passthrough pins all VM memory; ballooning is off. The VM always uses its full 6 GB.
