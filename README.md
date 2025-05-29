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

- **Tag Management** (New!):  
  Create and manage lightweight tags for marking important commits.

- **Smart Commit Messages** (New!):  
  Built-in commit message validator to enforce best practices.

- **Command Logging** (New!):  
  Comprehensive logging system for tracking all operations.

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
python jacobgit.py diff --staged    # Staged changes

# Tag Management (New!)
python jacobgit.py tag             # List all tags
python jacobgit.py tag v1.0        # Create a tag
python jacobgit.py tag -l          # List tags with commit SHAs
```

## Project Structure
```sh
jacobgit.py     # Main CLI and VCS logic
.jacobgit/      # Internal metadata directory
├── objects/    # Stores versioned file contents
├── refs/       # Stores branch references
│   ├── heads/  # Branch references
│   └── tags/   # Tag references (New!)
├── logs/       # Command execution logs (New!)
├── index       # Staging area (index)
└── HEAD        # Current branch or commit reference
```

## New Features

### Commit Message Guidelines

jacobgit now enforces commit message best practices:

1. Subject line (first line):
   - 50 characters or less
   - Starts with a capital letter
   - No trailing period
   - Concise summary of changes

2. Message body:
   - Blank line after subject
   - Detailed description of changes
   - Bullet points for multiple items

Example of a good commit message:
```
Add user authentication feature

- Implement login/logout functionality
- Add password hashing
- Create user session management
```

### Command Logging

All operations are now automatically logged:
- Command execution logs with timestamps
- Success/failure tracking
- Detailed error messages
- Logs stored in `.jacobgit/logs/jacobgit.log`

Example log output:
```
[2024-05-27 21:33:16] executing 'commit' command
[2024-05-27 21:33:16] 'commit' completed successfully
```

## Requirements

- Python 3.9 or higher
- No external dependencies

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Your chosen license]
