# jacobgit

**jacobgit** is a minimalist, educational version control system (VCS) written in Python. It implements core concepts inspired by Git, including commits, branches, trees, and an index, all managed in a custom `.jacobgit` directory. This project demonstrates a deep understanding of version control internals, file system manipulation, and Python programming.

---

## Features

- **Repository Initialization**:  
  Initialize a new repository with `jacobgit init`.

- **Staging and Committing**:  
  Add files to the index and commit changes, tracking project history.

- **Branching**:  
  Create, list, and delete branches for parallel development.

- **Checkout**:  
  Switch between branches or specific commits.

- **Status and Diff**:  
  View staged, modified, and untracked files. See differences between working directory, index, and HEAD.

- **Log**:  
  Display commit history in a readable format.

---

## Usage

```sh
# Initialize a new repository
python jacobgit.py init

# Add files to the staging area
python jacobgit.py add <file1> <file2> ...

# Commit staged changes
python jacobgit.py commit "Commit message"

# Show repository status
python jacobgit.py status

# Show commit history
python jacobgit.py log

# Create a new branch
python jacobgit.py branch <branch-name>

# List all branches
python jacobgit.py branch

# Delete a branch
python jacobgit.py branch -d <branch-name>

# Switch branches or checkout a commit
python jacobgit.py checkout <branch-name-or-commit-sha>

# Show differences
python jacobgit.py diff             # Unstaged changes
python jacobgit.py diff --staged   # Staged changes
```
---

## Project Structure
```sh
jacobgit.py     # Main CLI and VCS logic
.jacobgit/      # Internal metadata directory
├── objects/    # Stores versioned file contents
├── refs/       # Stores branch references
├── index       # Staging area (index)
└── HEAD        # Current branch or commit reference
```
