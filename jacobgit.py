#!/usr/bin/env python3
# Shebang allows the script to be run directly from command line on Unix-like systems

import os
import sys
import hashlib
import struct
import time
import functools
from dataclasses import dataclass
from typing import Optional, Tuple, Callable, TypeVar, Any, Dict, List, Union
from collections import defaultdict

# Type variables for generic decorator typing
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

def require_repo(func: F) -> F:
    """Decorator to ensure we're in a jacobgit repository"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        repo = kwargs.get('repo_path') or os.getcwd()
        jacobgit_dir = os.path.join(repo, ".jacobgit")
        if not os.path.exists(jacobgit_dir):
            print(f"fatal: not a jacobgit repository: {jacobgit_dir}")
            sys.exit(1)
        return func(*args, **kwargs)
    return wrapper  # type: ignore

def log_cmd(func: F) -> F:
    """Decorator to log command execution with file logging"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        repo = kwargs.get('repo_path') or os.getcwd()
        cmd_name = func.__name__.replace('cmd_', '')
        log_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] executing '{cmd_name}' command"
        
        # Print to console
        print(f"debug: {log_msg}")
        
        # Write to log file
        log_dir = os.path.join(repo, ".jacobgit", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "jacobgit.log")
        
        try:
            with open(log_file, 'a') as f:
                f.write(log_msg + "\n")
            result = func(*args, **kwargs)
            # Log success
            success_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] '{cmd_name}' completed successfully"
            with open(log_file, 'a') as f:
                f.write(success_msg + "\n")
            return result
        except Exception as e:
            # Log error
            error_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] '{cmd_name}' failed: {str(e)}"
            with open(log_file, 'a') as f:
                f.write(error_msg + "\n")
            print(f"error: command '{cmd_name}' failed: {str(e)}")
            sys.exit(1)
    return wrapper  # type: ignore

def catch_file_errors(func: F) -> F:
    """Decorator to handle common file operation errors"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            print(f"error: file not found: {e.filename}")
            sys.exit(1)
        except PermissionError as e:
            print(f"error: permission denied: {e.filename}")
            sys.exit(1)
        except OSError as e:
            print(f"error: operation failed: {str(e)}")
            sys.exit(1)
    return wrapper  # type: ignore

@dataclass
class IndexEntry:
    path: str
    mode: int
    mtime: int
    sha1: str

def hash_blob(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()

@catch_file_errors
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

@catch_file_errors
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

@catch_file_errors
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

@require_repo
@log_cmd
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

def get_working_files(repo_path: Optional[str] = None) -> list[str]:
    repo = repo_path or os.getcwd()
    files = []
    for root, _, names in os.walk(repo):
        # skip .jacobgit directory
        if ".jacobgit" in root.split(os.sep) or ".git" in root.split(os.sep):
            continue
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, repo)
            files.append(rel)
    return sorted(files)

def read_tree(sha: str, repo_path: Optional[str] = None, prefix: str = "") -> dict[str, str]:
    repo = repo_path or os.getcwd()
    obj_type, data = read_object(sha, repo)
    if obj_type != "tree":
        raise ValueError(f"Expected tree object, got {obj_type}")
    i = 0
    result: dict[str, str] = {}
    while i < len(data):
        # parse "mode name\0"
        j = data.find(b"\0", i)
        entry = data[i:j].decode("utf-8")
        mode_s, name = entry.split(" ", 1)
        mode = int(mode_s, 8)
        sha_bytes = data[j+1:j+21]
        entry_sha = sha_bytes.hex()
        i = j + 21
        path = f"{prefix}/{name}" if prefix else name

        # if tree, recurse; else record blob
        if mode == 0o040000:
            result.update(read_tree(entry_sha, repo, path))
        else:
            result[path] = entry_sha
    return result

def read_object(sha: str, repo_path: Optional[str] = None) -> Tuple[str, bytes]:
    repo = repo_path or os.getcwd()
    obj_path = os.path.join(repo, ".jacobgit", "objects", sha)
    with open(obj_path, 'rb') as f:
        full = f.read()
    header, raw = full.split(b'\0', 1)
    obj_type = header.split(b' ', 1)[0].decode('utf-8')
    return obj_type, raw

def validate_commit_message(func: F) -> F:
    """Decorator to validate commit message format and provide guidance"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not args:
            return func(*args, **kwargs)
            
        message = args[0]
        if not isinstance(message, str):
            return func(*args, **kwargs)

        # Validation rules
        lines = message.splitlines()
        if not lines:
            print("error: empty commit message")
            print("\nCommit message guidelines:")
            print("1. First line: short summary (50 chars or less)")
            print("2. Second line: blank")
            print("3. Following lines: detailed description")
            print("\nExample:")
            print("Add user authentication feature")
            print("")
            print("- Implement login/logout functionality")
            print("- Add password hashing")
            print("- Create user session management")
            sys.exit(1)

        # Check subject line length
        if len(lines[0]) > 50:
            print("warning: subject line should be 50 characters or less")
            print(f"current length: {len(lines[0])} characters")

        # Check if subject line starts with capital letter
        if lines[0][0].islower():
            print("warning: subject line should start with a capital letter")

        # Check if subject line ends with a period
        if lines[0].endswith('.'):
            print("warning: subject line should not end with a period")

        # If multi-line, check for blank second line
        if len(lines) > 1 and lines[1].strip():
            print("warning: second line should be blank")

        return func(*args, **kwargs)
    return wrapper  # type: ignore

@require_repo
@log_cmd
@validate_commit_message
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

@require_repo
@log_cmd
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

@log_cmd
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

@require_repo
@log_cmd
def cmd_status(repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()

    # load index and HEAD tree
    index = {e.path: e.sha1 for e in read_index(repo)}

    head_ref = get_head_ref(repo)
    head_sha = read_ref(repo, head_ref) if head_ref else None
    # if HEAD points at a commit, extract its "tree" SHA
    tree_sha = None
    obj_type = None
    raw = None
    if head_sha:
        obj_type, raw = read_object(head_sha, repo)
    if obj_type == "commit" and raw is not None:
        first_line = raw.split(b"\n", 1)[0]
        tree_sha = first_line.split(b" ", 1)[1].decode()
    elif obj_type == "tree":
        tree_sha = head_sha

    head_tree = read_tree(tree_sha, repo) if tree_sha else {}
    # get current files
    work_files = get_working_files(repo)

    staged, modified, untracked = [], [], []
    for path in work_files:
        data = open(os.path.join(repo, path), "rb").read()
        work_sha = hash_blob(data)

        in_index = path in index
        in_head  = path in head_tree

        # staged: in index differs from HEAD
        if in_index and index[path] != head_tree.get(path):
            staged.append(path)
        # modified: in index but working copy changed
        if in_index and work_sha != index[path]:
            modified.append(path)
        # untracked: not in index
        if not in_index:
            untracked.append(path)

    if staged:
        print("Staged changes:")
        for p in staged: print(f"  {p}")
    if modified:
        print("Modified (unstaged):")
        for p in modified: print(f"  {p}")
    if untracked:
        print("Untracked files:")
        for p in untracked: print(f"  {p}")
    if not (staged or modified or untracked):
        print("Nothing to commit, working tree clean.")

@require_repo
@log_cmd
def cmd_diff(staged: bool = False, repo_path: Optional[str] = None):
    import os
    import difflib

    repo = repo_path or os.getcwd()

    # Load index and HEAD tree if needed
    index = {e.path: e.sha1 for e in read_index(repo)}
    head_ref = get_head_ref(repo)
    head_sha = read_ref(repo, head_ref) if head_ref else None

    # Peel a commit down to its tree SHA
    tree_sha = None
    if head_sha:
        obj_type, raw = read_object(head_sha, repo)
        if obj_type == "commit":
            tree_sha = raw.split(b"\n", 1)[0].split(b" ", 1)[1].decode()
        elif obj_type == "tree":
            tree_sha = head_sha

    head_tree = read_tree(tree_sha, repo) if staged and tree_sha else {}

    work_files = get_working_files(repo)
    diffs = []

    if staged:
        # Compare index ↔ HEAD tree
        for path, idx_sha in index.items():
            head_sha2 = head_tree.get(path)
            if head_sha2 and head_sha2 != idx_sha:
                before = read_object(head_sha2, repo)[1].decode().splitlines()
                after  = read_object(idx_sha,  repo)[1].decode().splitlines()
                diffs.append((path, before, after))
    else:
        # Compare index ↔ working tree
        for path in work_files:
            if path in index:
                before = read_object(index[path], repo)[1].decode().splitlines()
                after  = open(os.path.join(repo, path)).read().splitlines()
                if before != after:
                    diffs.append((path, before, after))

    # Print diffs
    for path, before, after in diffs:
        for line in difflib.unified_diff(
            before,
            after,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm=""
        ):
            print(line)

    if not diffs:
        print("No staged changes." if staged else "No differences.")

@require_repo
@log_cmd
def cmd_checkout(target: str, repo_path: Optional[str] = None):
    """
    Checkout a branch or commit. If `target` matches a branch name in
    .jacobgit/refs/heads, switches to that branch; otherwise treats
    `target` as a raw commit SHA (detached HEAD).
    """
    import sys

    repo = repo_path or os.getcwd()

    # 1) Resolve target to a commit SHA and decide new HEAD content
    branch_ref_path = os.path.join(repo, ".jacobgit", "refs", "heads", target)
    if os.path.isfile(branch_ref_path):
        # it's a branch
        commit_sha = open(branch_ref_path, "r").read().strip()
        new_head = f"ref: refs/heads/{target}"
    else:
        # assume raw SHA
        commit_sha = target
        new_head = commit_sha

    # 2) Load the commit object and extract its tree SHA
    obj_type, raw = read_object(commit_sha, repo)
    if obj_type != "commit":
        print(f"error: '{target}' is not a valid commit")
        sys.exit(1)
    tree_line = raw.split(b"\n", 1)[0]            # b"tree <sha>"
    tree_sha = tree_line.split(b" ", 1)[1].decode() 

    # 3) Build a mapping of all files in that tree
    file_map = read_tree(tree_sha, repo)

    # 4) Remove working-tree files not in the new tree
    for path in get_working_files(repo):
        if path not in file_map:
            os.remove(os.path.join(repo, path))

    # 5) Write each blob from the tree back to disk
    for path, blob_sha in file_map.items():
        obj_type, data = read_object(blob_sha, repo)
        full_path = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(data)

    # 6) Update HEAD
    head_file = os.path.join(repo, ".jacobgit", "HEAD")
    with open(head_file, "w") as f:
        f.write(new_head + "\n")

    print(f"Switched to {target}")

def get_HEAD_commit(repo_path: Optional[str] = None) -> Optional[str]:
    """Get the commit SHA that HEAD points to, whether directly or via a ref."""
    repo = repo_path or os.getcwd()
    head_ref = get_head_ref(repo)
    return read_ref(repo, head_ref) if head_ref else read_ref(repo)

@require_repo
@log_cmd
def cmd_branch(args: list[str], repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    heads_dir = os.path.join(repo, ".jacobgit", "refs", "heads")

    # Ensure the heads directory exists
    os.makedirs(heads_dir, exist_ok=True)

    # Branch deletion
    if len(args) == 2 and args[0] == "-d":
        name = args[1]
        path = os.path.join(heads_dir, name)
        if not os.path.exists(path):
            print(f"error: branch '{name}' not found.")
            sys.exit(1)
        current = get_head_ref(repo)
        if current and current.endswith(name):
            print(f"error: cannot delete the branch '{name}' which you are currently on.")
            sys.exit(1)
        os.remove(path)
        print(f"Deleted branch {name}")
        return

    # Branch creation
    if len(args) == 1 and args[0] != "-d":
        name = args[0]
        path = os.path.join(heads_dir, name)
        if os.path.exists(path):
            print(f"error: branch '{name}' already exists.")
            sys.exit(1)
        # Get current commit SHA (fail if no commits)
        commit_sha = get_HEAD_commit(repo)
        if not commit_sha:
            print("error: cannot create branch: no commits yet.")
            sys.exit(1)

        with open(path, 'w') as f:
            f.write(commit_sha)
        print(f"Created branch {name}")
        return

    # Listing branches (no args)
    if not args:
        current = get_head_ref(repo)
        current = current.split('/')[-1] if current else None
        for fn in sorted(os.listdir(heads_dir)):
            prefix = "* " if fn == current else "  "
            print(f"{prefix}{fn}")
        return

    # Invalid usage
    print("Usage: jacobgit branch [<name>] | branch -d <name>")
    sys.exit(1)

@require_repo
@log_cmd
def cmd_tag(args: list[str], repo_path: Optional[str] = None):
    repo = repo_path or os.getcwd()
    tags_dir = os.path.join(repo, ".jacobgit", "refs", "tags")
    os.makedirs(tags_dir, exist_ok=True)

    # List tags
    if not args or (len(args) == 1 and args[0] == "-l"):
        if not os.path.exists(tags_dir) or not os.listdir(tags_dir):
            print("No tags exist yet.")
            return
        for tag in sorted(os.listdir(tags_dir)):
            sha = open(os.path.join(tags_dir, tag)).read().strip()[:7]
            print(f"{tag}\t{sha}")
        return

    # Create tag
    if len(args) == 1:
        name = args[0]
        if name == "-l":
            print("error: tag name required")
            sys.exit(1)
        path = os.path.join(tags_dir, name)
        if os.path.exists(path):
            print(f"error: tag '{name}' already exists.")
            sys.exit(1)

        # Get current commit SHA
        commit_sha = get_HEAD_commit(repo)
        if not commit_sha:
            print("error: cannot create tag: no commits yet.")
            sys.exit(1)

        with open(path, 'w') as f:
            f.write(commit_sha)
        print(f"Created tag {name}")
        return

    print("Usage: jacobgit tag [-l] | tag <name>")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: jacobgit <command> [<args>]")
        print("Commands:")
        print("  init                 Initialize a new repository")
        print("  add <file>…          Stage one or more files")
        print("  write-tree           Write tree objects from the index")
        print("  commit <message>     Commit staged changes")
        print("  log                  Show commit history")
        print("  status               Show staged, modified and untracked files")
        print("  branch [<name>]      List or create branches")
        print("  branch -d <name>     Delete a branch")
        print("  tag [-l]            List tags")
        print("  tag <name>          Create a tag")
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
    elif cmd == "status":
        cmd_status()
    elif cmd == "diff":
        staged = "--staged" in sys.argv
        cmd_diff(staged)
    elif cmd == "checkout":
        if len(sys.argv) != 3:
            print("Usage: jacobgit checkout <branch-or-commit>")
            sys.exit(1)
        cmd_checkout(sys.argv[2])
    elif cmd == "branch":
        cmd_branch(sys.argv[2:])
    elif cmd == "tag":
        cmd_tag(sys.argv[2:])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
