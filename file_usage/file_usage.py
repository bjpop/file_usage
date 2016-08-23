from __future__ import print_function
import sys
from collections import defaultdict, namedtuple
import os.path
from argparse import ArgumentParser
from termcolor import colored, cprint

DEFAULT_PERCENT_THRESHOLD = 1.0 
DEFAULT_SHOW_USERS = False
DEFAULT_INDENT = 8
DEFAULT_PRECISION = 1

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
    parser.add_argument(
        '--precision',
        metavar='N',
        type=int,
        default=DEFAULT_PRECISION,
        help='Number of decimal places to display in file/directory sizes in GB (default {})'.format(
            DEFAULT_PRECISION))
    parser.add_argument(
        '--path',
        metavar='STR',
        type=str,
        help='Only consider files/directories with this path as their prefix')
    parser.add_argument(
        '--user',
        metavar='STR',
        type=str,
        help='Only consider files/directories owned by this user')
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

# Split a file path into a list of components.
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

def size_in_gb_str(bytes, precision):
    format_str = '{{:.{}f}}'.format(precision)
    return format_str.format(float(bytes) / UNITS_IN_BYTES["G"])

class User(object):
    def __init__(self, size=0.0, count=0, precision=DEFAULT_PRECISION):
        self.size = size 
        self.count = count
        self.precision = precision

    def __str__(self):
        size_str = size_in_gb_str(self.size, self.precision)
        text = "size = {}, count = {}".format(size_str, self.count)
        return colored(text, 'yellow')

class Branch(object):
    def __init__(self):
        self.children = {} 
        self.users = {} 

    def size(self):
        return sum([user_stats.size for (user_name, user_stats) in self.users.items()])

def is_big_enough(size, total_size, threshold):
   return (size / total_size) * 100.0 >= threshold 

class SizeTree(object):
    def __init__(self, show_users=DEFAULT_SHOW_USERS, indent=DEFAULT_INDENT, precision=DEFAULT_PRECISION):
        self.tree = {}
        self.show_users = show_users
        self.indent = indent
        self.precision = precision

    def insert(self, path_str, size_bytes, user_name):
        path_list = splitall(path_str)
        tree = self.tree
        for item in path_list:
            if len(item.strip()) > 0:
                if item not in tree:
                    this_branch = Branch()
                    tree[item] = this_branch
                    this_branch.users = { user_name : User(size_bytes, 1, self.precision) } 
                else:
                    this_branch = tree[item]
                    this_users = this_branch.users
                    if user_name in this_users:
                        this_user = this_users[user_name]
                        this_user.size += size_bytes
                        this_user.count += 1
                    else:
                        this_users[user_name] = User(size_bytes, 1, self.precision)
                tree = this_branch.children

    def display(self, total_size, proportion_threshold):
        self.display_rec(self.tree, 0, total_size, proportion_threshold)

    def display_rec(self, tree, current_depth, total_size, proportion_threshold):
        if len(tree) == 0:
           return
        for item, branch in sorted(tree.items(), key=lambda x: x[1].size(), reverse=True):
            branch_size = branch.size() 
            if is_big_enough(branch_size, total_size, proportion_threshold):

                # Try to collapse directories which contain just one file.
                # This helps avoid gratuitous nesting in the output, especially
                # for paths which are sticks.
                path = item 
                while len(branch.children) == 1:
                    for item, branch in branch.children.items():
                        if path == '/':
                            path += item
                        else:
                            path += '/' + item 

                indent = ' ' * (self.indent * current_depth)
                print("{}{} ({} GB)".format(indent, colored(path, 'blue'), size_in_gb_str(branch_size, self.precision)))
                if self.show_users:
                    for user, user_stats in sorted(branch.users.items(), key=lambda x: x[1].size, reverse=True):
                        user_size = user_stats.size
                        #user_count = user_stats.count
                        if is_big_enough(user_size, total_size, proportion_threshold):
                            #print("{}  - {}: {} GB, {}".format(indent, colored(user, 'red'),
                            #      size_in_gb_str(user_size, self.precision), colored(user_count, 'yellow')))
                            print("{}  - {}: {}".format(indent, colored(user, 'red'), user_stats))
                self.display_rec(branch.children, current_depth + 1, total_size, proportion_threshold)


def consider_file(args, user_name, path):
    result = True
    if args.path and (not (path.startswith(args.path))):
        result = False
    if args.user and (not (user_name == args.user)):
        result = False
    return result

def main():
    args = parse_args()
    size_tree = SizeTree(args.showusers, args.indent, args.precision)
    user_usage = {} 
    num_skipped_lines = 0

    for line in sys.stdin:
        fields = line.split()
        if len(fields) >= 3:
            size, user_name, path = fields[:3]
            if consider_file(args, user_name, path):
                this_bytes = size_in_bytes(size)
                if user_name not in user_usage:
                    user_usage[user_name] = User(this_bytes, 1, args.precision)
                else:
                    user_usage[user_name].size += this_bytes
                    user_usage[user_name].count += 1 
                size_tree.insert(path, this_bytes, user_name)
        else:
            num_skipped_lines += 1 

    if num_skipped_lines > 0:
        print("Skipped {} lines in input.".format(num_skipped_lines))

    total_size_usage = sum([user_stats.size for user, user_stats in user_usage.items()]) 
    total_count = sum([user_stats.count for user, user_stats in user_usage.items()]) 

    if total_count > 0:

        if args.showusers:
            print("User totals:\n")
            for user, user_stats in sorted(user_usage.items(), key=lambda x: x[1], reverse=True):
                print("{}: {}".format(colored(user, 'red'), user_stats)) 

            print("\nTotal size:  {} GB".format(size_in_gb_str(total_size_usage, args.precision)))
            print("Total count: {}\n".format(total_count))
        size_tree.display(total_size_usage, args.thresh)
    else:
        print("\nTotal usage is 0 GB, nothing to show.")

if __name__ == '__main__':
    main()
