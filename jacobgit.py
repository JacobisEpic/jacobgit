#!/usr/bin/env python3
# Shebang allows the script to be run directly from command line on Unix-like systems

import os
import sys
import hashlib
import struct
import time
from dataclasses import dataclass
from typing import Optional, Tuple
from collections import defaultdict

@dataclass
class IndexEntry:
    path: str
    mode: int
    mtime: int
    sha1: str

def write_object(obj_type: str, data: bytes, repo_path: Optional[str] = None) -> str:
    repo = repo_path or os.getcwd()
    objects_dir = os.path.join(repo, ".jacobgit", "objects")
    os.makedirs(objects_dir, exist_ok=True)

    header = f"{obj_type} {len(data)}\0".encode()
    full    = header + data
    sha1    = hashlib.sha1(full).hexdigest()
    obj_path = os.path.join(objects_dir, sha1)
    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as f:
            f.write(full)
    return sha1

def read_index(repo_path: Optional[str] = None) -> list[IndexEntry]:
    repo = repo_path or os.getcwd()
    index_path = os.path.join(repo, ".jacobgit", "index")
    entries: list[IndexEntry] = []
    try:
        with open(index_path, 'rb') as f:
            raw = f.read(12)
            if len(raw) < 12:
                raise ValueError("Invalid index header")
            magic = raw[:4]
            version, count = struct.unpack('<II', raw[4:12])
            if magic != b"JIDX":
                raise ValueError("Bad index magic")
            if version > 0:
                raise ValueError(f"Unsupported index version {version}")
            for _ in range(count):
                hdr = f.read(10)  # 2 + 4 + 4
                if len(hdr) < 10:
                    raise ValueError("Truncated index entry header")
                path_len, mode, mtime = struct.unpack('<HII', hdr)
                sha_bytes = f.read(20)
                if len(sha_bytes) < 20:
                    raise ValueError("Truncated SHA in index")
                sha1 = sha_bytes.hex()
                path_bytes = f.read(path_len)
                if len(path_bytes) < path_len:
                    raise ValueError("Truncated path in index")
                path = path_bytes.decode('utf-8')
                entries.append(IndexEntry(path, mode, mtime, sha1))
    except FileNotFoundError:
        return []
    return entries

def write_index(entries: list[IndexEntry], repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    index_path = os.path.join(repo, ".jacobgit", "index")
    with open(index_path, 'wb') as f:
        f.write(b"JIDX")
        f.write(struct.pack("<I", 0))               # version
        f.write(struct.pack("<I", len(entries)))    # count
        for e in entries:
            path_bytes = e.path.encode('utf-8')
            f.write(struct.pack('<HII', len(path_bytes), e.mode, e.mtime))
            f.write(bytes.fromhex(e.sha1))
            f.write(path_bytes)

def cmd_add(paths: list[str], repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    entries = read_index(repo)
    for path in paths:
        st = os.stat(path)
        mode = st.st_mode
        mtime = int(st.st_mtime)
        with open(path, 'rb') as f:
            data = f.read()
        sha1 = write_object("blob", data, repo)
        entries = [e for e in entries if e.path != path]
        entries.append(IndexEntry(path, mode, mtime, sha1))
    write_index(entries, repo)
    print(f"Added {len(paths)} file(s) to the index.")

def write_tree(repo_path: Optional[str] = None) -> str:
    repo = repo_path or os.getcwd()
    entries = read_index(repo)
    tree_map = defaultdict(list)
    for e in entries:
        parent, name = os.path.split(e.path)
        tree_map[parent].append((name, e))
    def build_tree(dir_path: str) -> str:
        items = []
        for name, entry in sorted(tree_map.get(dir_path, [])):
            full = os.path.join(dir_path, name)
            if full in tree_map:
                sha = build_tree(full)
                mode = 0o040000
            else:
                sha = entry.sha1
                mode = entry.mode
            header = f"{mode:o} {name}\0".encode()
            items.append(header + bytes.fromhex(sha))
        tree_data = b"".join(items)
        return write_object("tree", tree_data, repo)
    return build_tree("")

def get_head_ref(repo_path: Optional[str] = None) -> Optional[str]:
    repo = repo_path or os.getcwd()
    head_file = os.path.join(repo, ".jacobgit", "HEAD")
    try:
        content = open(head_file, 'r').read().strip()
    except FileNotFoundError:
        return None
    if content.startswith("ref: "):
        return content[5:]
    return None  # detached HEAD

def read_ref(repo_path: Optional[str] = None, ref: Optional[str] = None) -> Optional[str]:
    repo = repo_path or os.getcwd()
    if ref:
        path = os.path.join(repo, ".jacobgit", ref)
        try:
            return open(path, 'r').read().strip()
        except FileNotFoundError:
            return None
    head_ref = get_head_ref(repo)
    if head_ref:
        return read_ref(repo, head_ref)
    # HEAD contains raw SHA?
    head_file = os.path.join(repo, ".jacobgit", "HEAD")
    try:
        content = open(head_file, 'r').read().strip()
        if not content.startswith("ref: "):
            return content
    except FileNotFoundError:
        pass
    return None

def read_object(sha: str, repo_path: Optional[str] = None) -> Tuple[str, bytes]:
    repo = repo_path or os.getcwd()
    obj_path = os.path.join(repo, ".jacobgit", "objects", sha)
    with open(obj_path, 'rb') as f:
        full = f.read()
    header, raw = full.split(b'\0', 1)
    obj_type = header.split(b' ', 1)[0].decode('utf-8')
    return obj_type, raw

def cmd_commit(message: str, repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    tree_sha = write_tree(repo)
    head_ref = get_head_ref(repo) or "refs/heads/master"
    parent_sha = read_ref(repo, head_ref)
    ts = int(time.time())
    author = f"Jacob Chin <you@example.com> {ts} +0000"
    lines = [f"tree {tree_sha}"]
    if parent_sha:
        lines.append(f"parent {parent_sha}")
    lines += [
        f"author {author}",
        f"committer {author}",
        "",
        message
    ]
    data = "\n".join(lines).encode('utf-8')
    commit_sha = write_object("commit", data, repo)
    ref_path = os.path.join(repo, ".jacobgit", head_ref)
    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, 'w') as f:
        f.write(commit_sha)
    branch = head_ref.split('/')[-1]
    print(f"[{branch} {commit_sha[:7]}] {message}")

def cmd_log(repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    head_ref = get_head_ref(repo)
    sha = read_ref(repo, head_ref) if head_ref else read_ref(repo)
    while sha:
        obj_type, raw = read_object(sha, repo)
        if obj_type != "commit":
            break
        meta, body = raw.split(b"\n\n", 1)
        msg = body.decode('utf-8').strip()
        print(f"commit {sha}")
        print(f"    {msg}\n")
        parent_line = next((l for l in meta.decode().splitlines() if l.startswith("parent ")), None)
        sha = parent_line.split()[1] if parent_line else None

def cmd_init(repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    jacobgit_dir = os.path.join(repo, ".jacobgit")
    if os.path.exists(jacobgit_dir):
        print(f"jacobgit repository already exists at {jacobgit_dir}")
        return
    os.makedirs(os.path.join(jacobgit_dir, "objects"), exist_ok=True)
    os.makedirs(os.path.join(jacobgit_dir, "refs", "heads"), exist_ok=True)
    with open(os.path.join(jacobgit_dir, "HEAD"), 'w') as f:
        f.write("ref: refs/heads/master\n")
    open(os.path.join(jacobgit_dir, "refs", "heads", "master"), 'w').close()
    print(f"Initialized empty jacobgit repository in {jacobgit_dir}")

def main():
    if len(sys.argv) < 2:
        print("Usage: jacobgit <command> [<args>]")
        print("Commands:")
        print("  init                 Initialize a new repository")
        print("  add <file>…          Stage one or more files")
        print("  write-tree           Write tree objects from the index")
        print("  commit <message>     Commit staged changes")
        print("  log                  Show commit history")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: jacobgit add <file>…")
            sys.exit(1)
        cmd_add(sys.argv[2:])
    elif cmd == "write-tree":
        sha = write_tree()
        print(f"Tree written: {sha}")
    elif cmd == "commit":
        if len(sys.argv) < 3:
            print("Usage: jacobgit commit <message>")
            sys.exit(1)
        cmd_commit(sys.argv[2])
    elif cmd == "log":
        cmd_log()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
