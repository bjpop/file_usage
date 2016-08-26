from __future__ import print_function
import sys
from collections import defaultdict, namedtuple
import os.path
from argparse import ArgumentParser
from termcolor import colored, cprint
import operator 

DEFAULT_PERCENT_THRESHOLD = 1.0 
DEFAULT_SHOW_USERS = False
DEFAULT_INDENT = 8
DEFAULT_PRECISION = 1
USER_NAME_COLOR = 'red'
FILE_SIZE_COLOR = 'yellow'
FILE_COUNT_COLOR = 'yellow'
FILE_PATH_COLOR = 'blue'

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

# from: https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html
def splitall(path):
    '''Split a file path into a list of components.

    >>> splitall("/hsm/VR0182/shared/Data")
    ['/', 'hsm', 'VR0182', 'shared', 'Data']
    >>> splitall("")
    ['']
    >>> splitall("/")
    ['/']
    >>> splitall("//")
    ['//']
    >>> splitall("/foo//bar")
    ['/', 'foo', 'bar']

    '''
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
    '''Compute how many bytes are used in by a file
    given a description of the form:

       (digit)+(designator)?

    digit in 0..9

    designator in:

    B = bytes
    K = kilobytes
    M = megabytes
    G = gigabytes
    T = terabytes

    If the designator is not given then we assume it was "B"
    for bytes.

    >>> size_in_bytes('45')
    45.0
    >>> size_in_bytes('42')
    42.0
    >>> size_in_bytes('12M')
    12582912.0
    >>> size_in_bytes('100G')
    107374182400.0
    >>> size_in_bytes('100T')
    109951162777600.0
    >>> size_in_bytes('1T')
    1099511627776.0

    '''
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

def render_bytes_in_gb(bytes, precision):
    '''Render a number of bytes as a string, in gigabytes units, showing
    precision number of decimal places:

    >>> render_bytes_in_gb(5000000000, 3)
    '4.657'

    '''
    format_str = '{{:.{}f}}'.format(precision)
    return format_str.format(float(bytes) / UNITS_IN_BYTES["G"])

class User(object):
    '''User information for a single node in the file tree (a file or a directory).

    name is the user_name of the owner of the file/directory.
    size is the size in bytes of the file, or transitive size of the directory,
        including the size of the directory itself.
    count is the transitive number of files in a directory, the count includes
       the directory itself in the count. So an empty directory will have a count
       of 1. This may seem counter-intuitive, but it simplifies things because
       we don't necessarily know what is a directory and what is a file, just by looking
       at the path on its own.
    '''

    def __init__(self, name, file_size=0.0, count=0):
        self.name = name
        self.file_size = file_size 
        self.count = count

    def size(self):
        return self.file_size

    def render(self, precision=DEFAULT_PRECISION):
        size_str = render_bytes_in_gb(self.file_size, precision)
        text = "{}: size = {}, count = {}".format(
            colored(self.name, USER_NAME_COLOR),
            colored(size_str, FILE_SIZE_COLOR),
            colored(self.count, FILE_COUNT_COLOR))
        return text 


class Node(object):
    '''A node in the file tree.
    Regular files and empty directories will have zero children.

    Non-empty directories will have one entry in children for each child.

    Each node
    '''
    def __init__(self):
        # Map from path entry to Node
        self.children = {} 
        # Map from user_name to User info
        self.users = {}

    def size(self):
        '''The size of a node in the tree is equal to the sum of the sizes
        of all the files/directories owned by all users in this node.

        We compute it this way because size is associated with a user (the owner
        of the file).
        '''
        return sum([user_stats.size() for (user_name, user_stats) in self.users.items()])

class FilePathTree(object):
    '''An entire tree for a set of file paths from the same file system.

    The tree itself is a dictionary that maps file/directory names to nodes.

    Nodes are themselves trees.
    '''
    def __init__(self):
        self.tree = {}

    def insert(self, path_str, size_bytes, user_name):
        path_list = splitall(path_str)
        tree = self.tree
        for item in path_list:
            if len(item.strip()) > 0:
                if item not in tree:
                    this_node = Node()
                    tree[item] = this_node
                    this_node.users = { user_name : User(user_name, size_bytes, 1) } 
                else:
                    this_node = tree[item]
                    this_users = this_node.users
                    if user_name in this_users:
                        this_user = this_users[user_name]
                        this_user.file_size += size_bytes
                        this_user.count += 1
                    else:
                        this_users[user_name] = User(user_name, size_bytes, 1)
                tree = this_node.children


class FilePathTreeRender(object):
    '''Display a FilePathTree in a pretty nested format.
    '''
    def __init__(self, tree, total_size,
            percent_threshold=DEFAULT_PERCENT_THRESHOLD,
            show_users=DEFAULT_SHOW_USERS,
            indent=DEFAULT_INDENT,
            precision=DEFAULT_PRECISION):
        self.file_path_tree = tree
        self.show_users = show_users
        self.indent = indent
        self.precision = precision
        self.total_size = total_size
        self.percent_threshold = percent_threshold

    def render(self):
        self.render_rec(self.file_path_tree.tree, 0)

    def render_rec(self, tree, current_depth):
        if len(tree) == 0:
            # reached a leaf of the tree, nothing to print
            return

        # Sort the children by their size
        for path, node, node_size in iter_by_size(tree): 
            node_size = node.size() 
            # Only display and traverse nodes which are big enough
            if self.is_big_enough(node_size):

                # Try to collapse directories which contain just one file.
                # This helps avoid gratuitous nesting in the output, especially
                # for paths which are sticks.

                while len(node.children) == 1:
                    child_path, node = node.children.items()[0]
                    # Don't insert a forward slash if we are at the root
                    # directory, because it is already called /
                    if path == '/':
                        path += child_path 
                    else:
                        path += '/' + child_path 

                # Indent the output based on how deep we are in the tree
                indent = ' ' * (self.indent * current_depth)

                print("{}{} ({} GB)".format(indent, colored(path, FILE_PATH_COLOR),
                    render_bytes_in_gb(node_size, self.precision)))

                if self.show_users:
                    # Show user information for this node
                    # Sort the users by the size of their contribution
                    for user, user_stats, user_size in iter_by_size(node.users): 
                        # Only print user information if their used file size big enough
                        if self.is_big_enough(user_size):
                            print("{}  - {}".format(indent, user_stats.render(self.precision)))

                # Recurse into the children of the node
                self.render_rec(node.children, current_depth + 1)

    def is_big_enough(self, size):
        '''Compute the percentage this size is of the total size for the whole
        set of considerd file paths.

        If the percentage is >= to user defined threshold then return True, indicating
        that the size is big enough to warrant consideration.
        '''
        return (size / self.total_size) * 100.0 >= self.percent_threshold 


def iter_by_size(dict):
    '''Given a dictionary whose values have a .size() method,
    compute a list of descending sorted triples: (key, val, val.size())

    We use this repeatedly when displaying various parts of the output because
    it is useful to show items in size sorted order, so that the largest is
    displayed first
    '''
    items = [(key, val, val.size()) for (key, val) in dict.items()] 
    return sorted(items, key=operator.itemgetter(2), reverse=True)


def consider_file(args, user_name, path):
    '''Check if we should consider a file for inclusion in the file_path tree.
    The decision is affected by user supplied command line arguments for:
        - user_name (only consider files/dirs owned by this user)
        - path (only consider files/dirs that start with this path prefix)

    If one or both of the command line arguments are set, and at least
    one of the conditions is not met, then we do not consider the file
    (skip over it).
    '''
    result = True
    if args.path and (not (path.startswith(args.path))):
        result = False
    if args.user and (not (user_name == args.user)):
        result = False
    return result


def process_input(args):
    '''Read the input file from stdin, build file_path_tree
    and user usage summary
    '''
    file_path_tree = FilePathTree()
    user_usage = {} 
    num_skipped_lines = 0

    for line in sys.stdin:
        fields = line.split()
        # skip lines which cannot be parsed
        if len(fields) >= 3:
            size, user_name, path = fields[:3]
            # check if we should consider this file path
            if consider_file(args, user_name, path):
                this_bytes = size_in_bytes(size)
                if user_name not in user_usage:
                    user_usage[user_name] = User(user_name, this_bytes, 1)
                else:
                    user_usage[user_name].file_size += this_bytes
                    user_usage[user_name].count += 1 
                file_path_tree.insert(path, this_bytes, user_name)
        else:
            num_skipped_lines += 1 

    if num_skipped_lines > 0:
        print("Skipped {} lines in input.".format(num_skipped_lines))

    return user_usage, file_path_tree


def show_user_summary(total_count, total_size_usage, user_usage, precision):
    '''Display a summary of all users' usage'''
    print("User totals:\n")
    for user, user_stats, user_size in iter_by_size(user_usage): 
        print("{}".format(user_stats.render(precision)))
    print("\nTotal size:  {} GB".format(render_bytes_in_gb(total_size_usage, precision)))
    print("Total count: {}\n".format(total_count))


def main():
    args = parse_args()
    user_usage, file_path_tree = process_input(args)
    total_size_usage = sum([user_stats.size() for user, user_stats in user_usage.items()]) 
    total_count = sum([user_stats.count for user, user_stats in user_usage.items()]) 

    if total_count > 0:
        if args.showusers:
            show_user_summary(total_count, total_size_usage, user_usage, args.precision)
        # Render the file_path_tree according to user specified limits.
        renderer = FilePathTreeRender(file_path_tree, total_size_usage,
            args.thresh, args.showusers, args.indent, args.precision)
        renderer.render()

    else:
        print("\nTotal usage is 0 GB, nothing to show.")

if __name__ == '__main__':
    main()
