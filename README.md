# Overview 

A tool for reporting file usage in a top-down manner.

# Usage

```
file_usage --showusers --thresh 10 < summary.txt
```

```
usage: file_usage [-h] [--thresh N] [--indent N] [--precision N] [--path STR]
                  [--user STR] [--showusers]

Compute filesytem usage by user and directory

optional arguments:
  -h, --help     show this help message and exit
  --thresh N     Percentage of total usage threshold, below which
                 files/directories are not shown (default 1.0)
  --indent N     Directory level indentation in output (default 8)
  --precision N  Number of decimal places to display in file/directory sizes
                 in GB (default 1)
  --path STR     Only consider files/directories with this path as their
                 prefix
  --user STR     Only consider files/directories owned by this user
  --showusers    Show usernames associated with files/directories in the
                 output
```

# Install

1. Inside a virtual environment:
```
% virtualenv file_usage_dev
% source file_usage_dev/bin/activate
% pip install -U /path/to/file_usage
```
2. Into the global package database for all users:
```
% pip install -U /path/to/file_usage
```
3. Into the user package database (for the current user only):
```
% pip install -U --user /path/to/file_usage
```

