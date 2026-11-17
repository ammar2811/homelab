# Proxmox VE host (`pve`)

| | |
|---|---|
| Hostname | `pve.home.arpa` (node name `pve`) |
| IP | `10.77.0.10/24`, gateway `10.77.0.1`, static on bridge `vmbr0` (port `nic0`) |
| Version | pve-manager 9.2.28 on Debian 13 (trixie), kernel 7.0.14-29-pve (2026-11-17) |
| Time zone | America/Toronto |
| Web UI | `https://10.77.0.10:8006`, user `root`, realm Linux PAM |
| SSH | `ssh pve` from the laptop (key auth) |

The node name `pve` is baked into `/etc/pve/nodes/pve/`; renaming it later is painful. The domain part
(`home.arpa`) only lives in `/etc/hosts` and is easy to change when a real domain is chosen.

## Install (2026-11-17)

- ISO `proxmox-ve_9.2-1.iso`, SHA-256
  `4e88fe416df9b527624a175f24c9aa07c714d3332afb1ee3dbf3879573ef2c6c` (from Proxmox's SHA256SUMS).
- USB stick flashed on a Windows PC with Rufus, then verified on the laptop: partition layout,
  `bootx64.efi`, all 1,443 installer files and the EFI partition identical to the ISO (flashing from
  the laptop itself corrupted two sticks; one Windows attempt wrote an ARM64 image by mistake).
- Installed with Secure Boot on.
- Filesystem: the default **ext4 on LVM-thin** (the ZFS option under "Options" was not selected). See
  [decisions.md](decisions.md) for what that means.

## Storage

Single 256 GB NVMe, LVM volume group `pve`:

| Volume | Size | Use | Proxmox storage ID |
|---|---|---|---|
| `pve/root` (ext4) | 69 GB | Host OS, ISOs, templates, backups (`/var/lib/vz`) | `local` |
| `pve/data` (thin pool) | 141 GB | VM and container disks | `local-lvm` |
| `pve/swap` | 8 GB | Host swap | |
| EFI partition | 1 GB | Boot | |

Container/VM snapshots work on `local-lvm`. There is no redundancy and no backup target yet
(see [roadmap.md](roadmap.md)).

## Repositories and updates

Configured over SSH (deb822 format in `/etc/apt/sources.list.d/`):

| File | State |
|---|---|
| `pve-enterprise.sources` | `Enabled: no` (paid subscription repo) |
| `ceph.sources` | `Enabled: no` (enterprise Ceph, we do not use Ceph) |
| `proxmox.sources` | **pve-no-subscription** (added) |
| `debian.sources` | Debian trixie, trixie-updates, trixie-security incl. non-free-firmware |

Update procedure:

```bash
ssh pve 'apt-get update && apt-get -y full-upgrade'
```

Reboot when a new `pve` kernel was installed (check `ls /boot/vmlinuz-*` vs `uname -r`). Guests with
`onboot=1` start automatically; CT 120 (DNS) starts first, so expect about a minute without DNS.

The first upgrade (2026-11-17) took 214 packages from 9.2.2 to 9.2.28 with no errors and loaded
Intel microcode `0xfa` (was `0xf8`). The web UI may show a "No valid subscription" notice; that is
expected on the free repository.

Known harmless boot messages: `SGX disabled or unsupported by BIOS`, and `blkmapd ... blocklayout
failed` (NFS pNFS helper, unused).

## Access setup on the laptop

- Key: `~/.ssh/id_ed25519` (ed25519, passphrase-protected), copied to `root@pve` with `ssh-copy-id`.
- Agent: systemd user service `ssh-agent.socket` (enabled), socket at
  `$XDG_RUNTIME_DIR/ssh-agent.socket`.
- `~/.ssh/config` points every host at that agent (`IdentityAgent`), sets `AddKeysToAgent yes`, and
  defines the `pve` and `adguard` aliases.

## Guests

| ID | Type | Name | IP | Notes |
|---|---|---|---|---|
| 120 | LXC | `adguard` | `10.77.0.20` | [AdGuard Home](services/adguard-home.md), start order 1 |
| 121 | VM | `homeassistant` | `10.77.0.21` | [Home Assistant OS](services/home-assistant.md), start order 3 |
| 125 | LXC | `tailscale` | `10.77.0.25` | [Tailscale](services/tailscale.md), `/dev/net/tun`, start order 2 |
| 130 | VM | `docker` | `10.77.0.30` | [Docker VM](services/docker-vm.md), iGPU passed through, start order 2 |

Images kept on the host for future VMs: `/root/images/debian-13-genericcloud-amd64.qcow2` (+ `SHA512SUMS`),
`/root/images/haos_ova-18.4.qcow2` (+ the verified `.xz`).

RAM after VM 121 started (2026-11-17): 11.8 GiB used, 3.6 GiB available of 15.4. VM 130 is pinned at
6 GB (passthrough), VM 121 has 4 GB. The 32 GB upgrade is needed before Immich or more VMs.

## iGPU passthrough (host side)

The host does not use the Intel UHD 630; VM 130 owns it (Jellyfin Quick Sync). Set up 2026-11-17:

| File | Content |
|---|---|
| `/etc/modules-load.d/vfio.conf` | `vfio`, `vfio_iommu_type1`, `vfio_pci` |
| `/etc/modprobe.d/vfio.conf` | `options vfio-pci ids=8086:3e92 disable_vga=1`, `softdep i915 pre: vfio-pci` |
| `/etc/modprobe.d/blacklist-i915.conf` | `blacklist i915` |

Applied with `update-initramfs -u -k all` and a host reboot. IOMMU was already active by default
(no kernel parameter needed); the iGPU is alone in IOMMU group 0. Check with
`lspci -nnk -s 00:02.0` (expect `Kernel driver in use: vfio-pci`).

Consequences: the host has no `/dev/dri`; the local monitor shows nothing useful once VM 130 runs
(Intel AMT still shows BIOS and boot). To give the iGPU back to the host, remove the three files,
`update-initramfs -u -k all`, reboot, and remove `hostpci0` from VM 130.

## Creating a VM from the Debian cloud image (our standard)

As done for VM 130 (see its doc for the full command): q35 + OVMF with `pre-enrolled-keys=0`,
`cpu host`, `import-from` the verified qcow2 onto `local-lvm` with `discard=on,iothread=1,ssd=1`,
cloud-init drive with `ciuser root`, laptop SSH key, static `ipconfig0`, `nameserver 10.77.0.20`,
`ciupgrade 1`, `agent enabled=1`, serial console. Then inside: install `qemu-guest-agent`, set the
time zone, and if the VM needs hardware drivers, replace the cloud kernel with `linux-image-amd64`.
Verify the SSH host key out of band with
`ssh pve 'qm guest exec <ID> -- ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub'`.

Templates downloaded: `local:vztmpl/debian-13-standard_13.6-1_amd64.tar.zst`.

## Creating a new container (our standard)

```bash
ssh pve 'pveam update && pveam available --section system | grep debian-13'
ssh pve 'pct create <ID> local:vztmpl/debian-13-standard_<ver>_amd64.tar.zst \
  --hostname <name> --unprivileged 1 --features nesting=1 \
  --cores 1 --memory 512 --swap 512 --rootfs local-lvm:<GB> \
  --net0 name=eth0,bridge=vmbr0,ip=10.77.0.<octet>/24,gw=10.77.0.1,firewall=0 \
  --nameserver 10.77.0.20 --searchdomain home.arpa \
  --onboot 1 --timezone host --tags <tag> \
  --description "<service> - <url>" \
  --ssh-public-keys /root/laptop.pub'
```

- Copy the laptop key first: `scp ~/.ssh/id_ed25519.pub pve:/root/laptop.pub` (delete it afterwards).
- ID = 100 + last octet. Pick an unused IP from the plan in [network.md](network.md).
- Use `--nameserver 10.77.0.20` for normal guests. Only DNS infrastructure itself uses the router.
- Add an `ssh` alias in the laptop's `~/.ssh/config`, check the host key fingerprint printed by
  `pct create` on first connect, then `apt-get update && apt-get -y full-upgrade` inside.
- Document the guest here and in network.md.

## Firewall

The Proxmox firewall service runs but is disabled at datacenter level (default). The LAN is trusted and
nothing is exposed to the internet. Revisit when Tailscale and exposed services arrive.
