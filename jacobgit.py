#!/usr/bin/env python3
# Shebang allows the script to be run directly from command line on Unix-like systems

import os
import sys
import hashlib
import struct
from dataclasses import dataclass

@dataclass
class IndexEntry:
    path: str
    mode: int
    mtime: int
    sha1: str

def hash_and_store_object(file_path, objects_dir):
    with open(file_path, 'rb') as f:
        data = f.read()
    sha1 = hashlib.sha1(data).hexdigest()
    obj_path = os.path.join(objects_dir, sha1)

    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as out:
            out.write(data)
    return sha1

def write_object(obj_type: str, data: bytes, repo_path: str=None) -> str:
    repo_path = repo_path or os.getcwd()
    objects_dir = os.path.join(repo_path, ".jacobgit", "objects")
    os.makedirs(objects_dir, exist_ok=True)

    # Create the object file
    sha1 = hashlib.sha1(data).hexdigest()
    obj_path = os.path.join(objects_dir, sha1)
    
    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as f:
            f.write(data)
    
    return sha1
    header = f"{obj_type} {len(data)}\0".encode('utf-8')
    full = header + data

    sha1 = hashlib.sha1(full).hexdigest()

    # if missing, create the objects directory
    obj_path = os.path.join(objects_dir, sha1)
    if not os.path.exists(obj_path):
        with open(obj_path, 'wb') as f:
            f.write(full)

    return sha1

def read_index(repo_path=None) -> list[IndexEntry]:
    repo_path = repo_path or os.getcwd()
    index_path = os.path.join(repo_path, ".jacobgit", "index")
    entries: list[IndexEntry] = []
    try:
        with open(index_path, 'rb') as f:
            # Header (12 bytes))
            raw = f.read(12)
            if len(raw) < 12:
                raise ValueError("Invalid index file format")
            magic = raw[:4]
            version, count = struct.unpack('<II', raw[4:12]) # little-endian unsigned int
            if magic != b"JIDX":
                raise ValueError("Invalid index file format")
            if version > 0:
                raise ValueError("Unsupported index version {version}")
            
            # Entries
            for _ in range(count):
                # read path_len (H -> 2 bytes Unsigned short), mode (I -> 4 bytes Unsigned int), mtime (I -> 4 bytes Unsigned int)
                entry_header = f.read(2 + 4 + 4)
                if len(entry_header) < 10:
                    raise ValueError("Invalid entry header format")
                path_len, mode, mtime = struct.unpack('<HII', entry_header)

                # read sha1 (20 bytes)
                sha_bytes = f.read(20)
                if len(sha_bytes) < 20:
                    raise ValueError("Invalid SHA1 format")
                sha1 = sha_bytes.hex()

                # read path (variable length)
                path_bytes = f.read(path_len)
                if len(path_bytes) < path_len:
                    raise ValueError("Index path truncated")
                path = path_bytes.decode('utf-8')

                entries.append(IndexEntry(path, mode, mtime, sha1))
    except FileNotFoundError:
        print("Index file not found.")
        return []

    return entries

def write_index(entries, repo_path=None):
    repo = repo_path or os.getcwd()
    index_path = os.path.join(repo, ".jacobgit", "index")
    # Open the index file in binary write mode
    with open(index_path, 'wb') as f:
        # Write the header
        f.write(b"JIDX")
        f.write(struct.pack("<I", 0))  # version
        f.write(struct.pack("<I", len(entries)))  # count

        # Write each entry
        for entry in entries:
            path_bytes = entry.path.encode('utf-8')
            path_len = len(path_bytes)
            # Write the entry header
            f.write(struct.pack('<HII', path_len, entry.mode, entry.mtime))
            # Write the SHA1 hash
            f.write(bytes.fromhex(entry.sha1))
            # Write the path
            f.write(path_bytes)

def cmd_add(paths, repo_path=None):
    repo = repo_path or os.getcwd()
    entries = read_index(repo)
    # Check if the file exists
    for path in paths:
        # stat file
        st = os.stat(path)
        mode = st.st_mode
        mtime = st.st_mtime

        # Read file and write blob
        with open(path, 'rb') as f:
            data = f.read()
        sha1 = write_object("blob", data)

        entries = [entry for entry in entries if entry.path != path]
        entries.append(IndexEntry(path, sha1, mode, mtime))
    write_index(entries, repo)
    print(f"Added {len(paths)} file(s) to the index.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 jacobgit.py <repository_path>")
        sys.exit(1)
    
    command = sys.argv[1]

    if command == "init":
        cmd_init()
    elif command == "add":
        if len(sys.argv) < 3:
            print("Usage: python3 jacobgit.py add <file1> <file2> ...")
            sys.exit(1)
        cmd_add(sys.argv[2:])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
    
def cmd_init():
    print("Initializing jacobgit repository...")
    jacobgit_dir = os.path.join(os.getcwd(), ".jacobgit") 
    #os.getcwd() is the current working directory
    #os.path.join() joins the current working directory with the .jacobgit directory
    #.jacobgit is a hidden directory (on Unix-like operating systems) that will be created in the current working directory

    if os.path.exists(jacobgit_dir):
        print(f"jacobgitrepository already exists at {jacobgit_dir}")
        return

    os.makedirs(os.path.join(jacobgit_dir, "objects"), exist_ok=True)
    os.makedirs(os.path.join(jacobgit_dir, "refs", "heads"), exist_ok=True)

    with open(os.path.join(jacobgit_dir, "HEAD"), "w") as head_file:
        head_file.write("ref: refs/heads/master\n")
    # Create the HEAD file and write the reference to the master branch
    # The HEAD file is a special file in Git that points to the current branch
    # The refs/heads directory contains references to all the branches in the repository
    # The master branch is the default branch in Git

    open(os.path.join(jacobgit_dir, "refs", "heads", "master"), "w").close()

    print(f"Initialized empty jacobgit repository in {jacobgit_dir}")
    # The refs/heads/master file is created to represent the master branch
    # The jacobgit repository is now initialized and ready to use

if __name__ == "__main__":
    main()
# The main function is called to start the program
# Basically, this ensures that the script is run directly, not imported as a module
# The __name__ variable is a special variable in Python that is set to "__main__" when the script is run directly
# This allows the script to be imported as a module without executing the main function
# The if __name__ == "__main__": block is a common Python idiom to allow or prevent parts of code from being run when the modules are imported