#!/usr/bin/env python3
"""Build the public copy of this repo, with personal details replaced.

The private repo (this one) stays the source of truth with full details. This script takes the
last commit (git archive HEAD, so uncommitted edits are never published), applies the rules in
publish/redactions.tsv, refuses to continue if any personal detail remains, and commits the result
into a separate public repo. It never pushes.

Usage: scripts/build-public.py [PUBLIC_REPO_DIR]     (default: ../homelab-public)

The public repo's commit identity comes from its own git config (user.name / user.email); set it
once in that directory before the first build.
"""
import io
import pathlib
import shutil
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RULES = ROOT / "publish" / "redactions.tsv"
EXCLUDE_TOP = {"publish"}  # never published
NOTE = (
    "> Published copy: personal details (location, account identifiers, hardware addresses) are\n"
    "> replaced with placeholders. The private repo it is generated from keeps the full details.\n"
)


def git(*args, cwd=ROOT, capture=True):
    return subprocess.run(["git", *args], cwd=cwd, check=True, text=True,
                          capture_output=capture).stdout.strip()


def load_rules():
    replace, drop, forbid = [], [], []
    for n, raw in enumerate(RULES.read_text().splitlines(), 1):
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        kind = parts[0]
        if kind == "REPLACE" and len(parts) == 3:
            replace.append((parts[1], parts[2]))
        elif kind == "DROPLINE" and len(parts) == 2:
            drop.append(parts[1])
        elif kind == "FORBID" and len(parts) == 2:
            forbid.append(parts[1])
        else:
            sys.exit(f"{RULES}:{n}: bad rule: {raw!r}")
    replace.sort(key=lambda r: len(r[0]), reverse=True)
    forbid += [lit for lit, _ in replace] + drop
    return replace, drop, forbid


def snapshot_head():
    """Return {relative path: bytes} for every file in HEAD, minus excluded folders."""
    data = subprocess.run(["git", "archive", "--format=tar", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if m.isfile() and m.name.split("/")[0] not in EXCLUDE_TOP:
                files[m.name] = (tar.extractfile(m).read(), m.mode)
    return files


def snapshot_worktree():
    """Like snapshot_head, but from tracked + untracked (not ignored) files on disk."""
    names = git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    files = {}
    for name in names:
        p = ROOT / name
        if p.is_file() and name.split("/")[0] not in EXCLUDE_TOP:
            files[name] = (p.read_bytes(), p.stat().st_mode)
    return files


def redact(files, replace, drop):
    out = {}
    for path, (blob, mode) in files.items():
        try:
            text = blob.decode("utf-8")
        except UnicodeDecodeError:
            out[path] = (blob, mode)
            continue
        lines = [l for l in text.splitlines(keepends=True) if not any(d in l for d in drop)]
        text = "".join(lines)
        for lit, new in replace:
            text = text.replace(lit, new)
        if path == "README.md":
            head, sep, rest = text.partition("\n\n## ")
            text = f"{head}\n\n{NOTE}{sep}{rest}" if sep else text + "\n" + NOTE
        out[path] = (text.encode("utf-8"), mode)
    return out


def leak_check(files, forbid):
    leaks = []
    for path, (blob, _) in files.items():
        hay = (path + "\n" + blob.decode("utf-8", "replace")).lower()
        for lit in forbid:
            if lit.lower() in hay:
                for n, line in enumerate(hay.splitlines(), 0):
                    if lit.lower() in line:
                        leaks.append(f"{path}:{n}: contains {lit!r}")
    return leaks


def main():
    args = [a for a in sys.argv[1:] if a != "--preview"]
    preview = "--preview" in sys.argv[1:]
    replace, drop, forbid = load_rules()

    if preview:
        # Working-tree build into a throwaway folder: no git operations, nothing committed.
        dst = pathlib.Path(args[0] if args else "/tmp/homelab-public-preview").resolve()
        files = redact(snapshot_worktree(), replace, drop)
        leaks = leak_check(files, forbid)
        if leaks:
            print("LEAK CHECK FAILED:", *leaks, sep="\n  ")
            sys.exit(1)
        shutil.rmtree(dst, ignore_errors=True)
        for path, (blob, mode) in files.items():
            (dst / path).parent.mkdir(parents=True, exist_ok=True)
            (dst / path).write_bytes(blob)
        print(f"preview OK: {len(files)} files written to {dst} (working tree, nothing committed)")
        return

    dst = pathlib.Path(args[0] if args else ROOT.parent / "homelab-public").resolve()
    if git("status", "--porcelain"):
        print("note: uncommitted changes in the private repo are NOT published (building from HEAD)")
    head = git("rev-parse", "--short", "HEAD")

    files = redact(snapshot_head(), replace, drop)
    leaks = leak_check(files, forbid)
    if leaks:
        print("LEAK CHECK FAILED, nothing written:", *leaks, sep="\n  ")
        sys.exit(1)
    print(f"leak check passed: {len(files)} files, {len(forbid)} forbidden strings")

    dst.mkdir(parents=True, exist_ok=True)
    if not (dst / ".git").exists():
        git("init", "-q", "-b", "main", cwd=dst)
    for child in dst.iterdir():
        if child.name != ".git":
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    for path, (blob, mode) in files.items():
        target = dst / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
        target.chmod(mode & 0o777)

    git("add", "-A", cwd=dst)
    if not git("status", "--porcelain", cwd=dst):
        print(f"public repo already matches private {head}; nothing to commit")
        return
    try:
        git("config", "user.email", cwd=dst)
    except subprocess.CalledProcessError:
        print(f"files staged in {dst}, but no commit identity is set there.\n"
              f"Set one with: git -C {dst} config user.name ... && git -C {dst} config user.email ...")
        sys.exit(2)
    git("commit", "-q", "-m", f"Publish from private repo {head}", cwd=dst)
    print(f"committed to {dst}: {git('log', '--oneline', '-1', cwd=dst)}")
    print("Not pushed. Review, then push yourself or ask the agent to.")


if __name__ == "__main__":
    main()
