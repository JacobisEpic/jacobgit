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
python [jacobgit.py](http://_vscodecontentref_/0) init

# Add files to the staging area
python [jacobgit.py](http://_vscodecontentref_/1) add <file1> <file2> ...

# Commit staged changes
python [jacobgit.py](http://_vscodecontentref_/2) commit "Commit message"

# Show repository status
python [jacobgit.py](http://_vscodecontentref_/3) status

# Show commit history
python [jacobgit.py](http://_vscodecontentref_/4) log

# Create a new branch
python [jacobgit.py](http://_vscodecontentref_/5) branch <branch-name>

# List all branches
python [jacobgit.py](http://_vscodecontentref_/6) branch

# Delete a branch
python [jacobgit.py](http://_vscodecontentref_/7) branch -d <branch-name>

# Switch branches or checkout a commit
python [jacobgit.py](http://_vscodecontentref_/8) checkout <branch-or-commit-sha>

# Show differences
python [jacobgit.py](http://_vscodecontentref_/9) diff           # unstaged changes
python [jacobgit.py](http://_vscodecontentref_/10) diff --staged  # staged changes

---

## Project Structure
- jacobgit.py — Main implementation of the VCS logic.
- .jacobgit/ — Internal metadata directory (objects, refs, index, HEAD).
