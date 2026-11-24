#!/usr/bin/env python3
"""Change the AdGuard Home web UI password. Runs inside CT 120, interactively.

AdGuard Home has no password change in its UI; the password is a bcrypt hash in
AdGuardHome.yaml (users[].password), which may only be edited with the service stopped.

The password is read with getpass and never printed, logged or passed on a command line.
It is prompted for before the service is stopped, so DNS is down only for the few seconds
of the write. Existing web sessions are cleared so every browser must log in again.

Usage (Ammar, from the laptop):
    scp scripts/adguard/set-password.py adguard:/root/
    ssh -t adguard 'apt-get -y install python3-bcrypt python3-yaml && python3 /root/set-password.py'
"""
import getpass
import os
import shutil
import subprocess
import sys
import time

import bcrypt
import yaml

DIR = "/opt/AdGuardHome"
PATH = f"{DIR}/AdGuardHome.yaml"
SESSIONS = f"{DIR}/data/sessions.db"
MIN_LEN = 12


def run(*cmd):
    subprocess.run(cmd, check=True)


def load():
    with open(PATH) as f:
        cfg = yaml.safe_load(f)
    users = cfg.get("users") or []
    if len(users) != 1:
        sys.exit(f"expected exactly one user in {PATH}, found {len(users)}; aborting")
    return cfg, users[0]


_, user = load()
print(f"Changing the password for AdGuard user '{user['name']}'.")

pw = getpass.getpass("New password: ")
if len(pw) < MIN_LEN:
    sys.exit(f"password must be at least {MIN_LEN} characters; nothing changed")
if pw != getpass.getpass("Repeat new password: "):
    sys.exit("passwords do not match; nothing changed")
hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode()
del pw

backup = f"{PATH}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
run("systemctl", "stop", "AdGuardHome")
try:
    shutil.copy2(PATH, backup)
    # Re-read after stopping: AdGuard may have rewritten its config while we were prompting.
    cfg, user = load()
    user["password"] = hashed
    try:
        with open(PATH, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, default_flow_style=False)
        run(f"{DIR}/AdGuardHome", "--check-config", "-c", PATH, "-w", DIR)
    except BaseException:
        shutil.copy2(backup, PATH)
        print(f"failed; restored {backup}", file=sys.stderr)
        raise
    if os.path.exists(SESSIONS):
        os.remove(SESSIONS)
finally:
    run("systemctl", "start", "AdGuardHome")

print(f"Password changed; old config backed up as {backup}. All web sessions were logged out.")
