from __future__ import print_function
import sys
from collections import defaultdict, namedtuple
import os.path
from argparse import ArgumentParser
from termcolor import colored, cprint

DEFAULT_PERCENT_THRESHOLD = 1.0 
DEFAULT_SHOW_USERS = False
DEFAULT_INDENT = 8

def parse_args():
    '''Parse command line arguments.
    Returns Options object with command line argument values as attributes.
    Will exit the program on a command line error.
    '''
    parser = ArgumentParser(description='Compute filesytem usage by user and directory')
    parser.add_argument(
        '--thresh',
        metavar='N',
        type=float,
        default=DEFAULT_PERCENT_THRESHOLD,
        help='Percentage of total usage threshold, below which files/directories are not shown (default {})'.format(
            DEFAULT_PERCENT_THRESHOLD))
    parser.add_argument(
        '--indent',
        metavar='N',
        type=int,
        default=DEFAULT_INDENT,
        help='Directory level indentation in output (default {})'.format(
            DEFAULT_INDENT))
    parser.add_argument('--showusers', action='store_true',
        default=DEFAULT_SHOW_USERS,
        help='Show usernames associated with files/directories in the output')
    return parser.parse_args()


UNITS_IN_BYTES = {
    "B": 1,
    "K": 1024,
    "M": 1024 ** 2,
    "G": 1024 ** 3,
    "T": 1024 ** 4 
}

# from: https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html
def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def size_in_bytes(size_str):
    if len(size_str) >= 1:
        units = size_str[-1]
        if units.upper() not in ["K", "M", "G", "T"]:
            units = "B"
            number = size_str
        else:
            number = size_str[:-1]
        try:
            scalar = float(number)
        except:
            pass
        else:
            return scalar * UNITS_IN_BYTES[units]
    # If we get here then there was something wrong with
    # the input file size
    exit("Bad file size in input: '{}'".format(size_str))

def size_in_gb(bytes):
    return "{:.1f}".format(float(bytes) / UNITS_IN_BYTES["G"])

class Branch(object):
    def __init__(self):
        self.children = {} 
        self.users = defaultdict(int)

    def size(self):
        return sum([user_size for (user, user_size) in self.users.items()])

def is_big_enough(size, total_size, threshold):
   return (size / total_size) * 100.0 >= threshold 

class SizeTree(object):
    def __init__(self, show_users=DEFAULT_SHOW_USERS, indent=DEFAULT_INDENT):
        self.tree = {}
        self.show_users = show_users
        self.indent = indent

    def insert(self, path_str, size_bytes, user):
        path_list = splitall(path_str)
        tree = self.tree
        for item in path_list:
            if len(item.strip()) > 0:
                if item not in tree:
                    tree[item] = Branch()
                this_branch = tree[item]
                this_users = this_branch.users
                this_users[user] += size_bytes
                tree = this_branch.children

    def display(self, total_size, proportion_threshold):
        self.display_rec(self.tree, 0, total_size, proportion_threshold)

    def display_rec(self, tree, current_depth, total_size, proportion_threshold):
        if len(tree) == 0:
           return
        for item, branch in sorted(tree.items(), key=lambda x: x[1].size(), reverse=True):
            branch_size = branch.size() 
            if is_big_enough(branch_size, total_size, proportion_threshold):

                path = item 
                while len(branch.children) == 1:
                    for item, branch in branch.children.items():
                        if path == '/':
                            path += item
                        else:
                            path += '/' + item 

                indent = ' ' * (self.indent * current_depth)
                print("{}{} ({} GB)".format(indent, colored(path, 'blue'), size_in_gb(branch_size)))
                if self.show_users:
                    for user, user_size in sorted(branch.users.items(), key=lambda x: x[1], reverse=True):
                        if is_big_enough(user_size, total_size, proportion_threshold):
                            print("{}  - {}: {} GB".format(indent, colored(user, 'red'), size_in_gb(user_size)))
                self.display_rec(branch.children, current_depth + 1, total_size, proportion_threshold)
            

def main():
    args = parse_args()
    size_tree = SizeTree(args.showusers, args.indent)
    user_usage = defaultdict(int)
    for line in sys.stdin:
        fields = line.split()
        if len(fields) >= 3:
            size, user, path = fields[:3]
            this_bytes = size_in_bytes(size)
            user_usage[user] += this_bytes
            size_tree.insert(path, this_bytes, user)
        else:
            print("Skipping '{}'".format(line))
    total_usage = 0
    print("User totals:\n")
    for user, usage in sorted(user_usage.items(), key=lambda x: x[1], reverse=True):
        print("{}: {} GB".format(colored(user, 'red'), size_in_gb(usage))) 
        total_usage += usage 
    print("\nTotal: {} GB".format(size_in_gb(total_usage)))
    print("\nDirectory breakdown:\n")
    size_tree.display(total_usage, args.thresh)

if __name__ == '__main__':
    main()
