"""Send raw DNS A queries to one server and print rcode, answers and latency."""
import random
import socket
import struct
import sys
import time

RCODES = {0: "NOERROR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}


def query(server, name):
    qid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", qid, 0x0100, 1, 0, 0, 0)  # RD set
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\0"
    packet = header + qname + struct.pack(">HH", 1, 1)  # A, IN
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    t0 = time.monotonic()
    s.sendto(packet, (server, 53))
    data, _ = s.recvfrom(4096)
    ms = (time.monotonic() - t0) * 1000
    _, flags, _, ancount, _, _ = struct.unpack(">HHHHHH", data[:12])
    rcode = flags & 0xF
    # skip question
    i = 12
    while data[i]:
        i += data[i] + 1
    i += 5
    ips = []
    for _ in range(ancount):
        if data[i] & 0xC0 == 0xC0:
            i += 2
        else:
            while data[i]:
                i += data[i] + 1
            i += 1
        rtype, _, _, rdlen = struct.unpack(">HHIH", data[i:i + 10])
        i += 10
        if rtype == 1:
            ips.append(socket.inet_ntoa(data[i:i + 4]))
        i += rdlen
    return RCODES.get(rcode, str(rcode)), ips, ms


if len(sys.argv) < 3:
    sys.exit(f"usage: {sys.argv[0]} SERVER NAME [NAME ...]  e.g. 10.77.0.20 example.com doubleclick.net")
server = sys.argv[1]
for name in sys.argv[2:]:
    try:
        rcode, ips, ms = query(server, name)
        print(f"{name:32} {rcode:9} {','.join(ips) or '-':34} {ms:6.1f} ms")
    except Exception as e:  # noqa: BLE001
        print(f"{name:32} ERROR {e}")
