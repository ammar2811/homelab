# Hardware

## Dell OptiPlex 5060 SFF (Proxmox host)

Bought used (ex-office). Verified on the running system 2026-11-17:

| Part | Detail |
|---|---|
| CPU | Intel Core i7-8700, 6 cores / 12 threads, microcode `0xfa` |
| iGPU | Intel UHD Graphics 630 (`8086:3e92`, Quick Sync: H.264/HEVC 10-bit, no AV1). Passed through to VM 130; the host does not use it. |
| RAM | 16 GB: 2 x 8 GB DDR4-2666 Samsung `M378A1K43CB2-CTD` in DIMM1/DIMM2; DIMM3/DIMM4 empty (max 64 GB) |
| Boot disk | SK hynix PC601 256 GB NVMe |
| NIC | Intel I219-V, 1 GbE, onboard (`nic0`) |
| Expansion | Low-profile PCIe slots (room for a 2.5G/10G NIC or a low-profile GPU) |
| BIOS | 1.32.0 |
| Other bays | One 3.5" bay (planned: large HDD for media) |

### BIOS settings applied

| Setting | Value | Why |
|---|---|---|
| SATA Operation | AHCI | RAID On can hide the NVMe from Linux |
| Virtualization (VT-x), VT for Direct I/O (VT-d) | Enabled | VMs and device passthrough (iGPU, USB) |
| AC Recovery | Power On | Comes back by itself after a power cut |
| Secure Boot | Enabled (verified with `mokutil --sb-state`) | Proxmox 9 supports it |

To verify on the host: `dmidecode -s bios-version`.

### Intel AMT (out-of-band management)

Configured in MEBx (Ctrl+P at boot):

- Manageability, SOL, Storage Redirection, KVM: enabled
- User opt-in: None (so remote KVM does not need a code read off the local screen)
- Network: DHCP, network access activated
- Power: on in S0/S3/S4-5

Currently answers at `10.77.0.208` (DHCP lease). AMT shares the onboard NIC's MAC, so it only works
over the onboard port; keep it connected even if a PCIe NIC is added later.

Rules: never port-forward AMT ports (16992-16995, 5900); reach it only from the LAN or Tailscale.
The AMT admin password is Ammar's only.

Not yet verified: whether the remote KVM shows an image with no monitor attached (a DisplayPort dummy
plug fixes that if not), and Dell's "Deep Sleep Control" setting (must be Disabled for power-on from
off).

## Admin laptop

Dell Inspiron 5505 (AMD), Arch Linux with Omarchy, Wi-Fi only, NetworkManager + systemd-resolved.
USB 2.0 flash writes from this laptop proved unreliable, see [CLAUDE.md](../CLAUDE.md) gotchas.

## Network gear

See [network.md](network.md) for the TP-Link Archer BE550.
