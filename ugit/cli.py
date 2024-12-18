import argparse
import os
import sys
import textwrap

from . import data
from . import base

def main():
    args = parse_args()
    # 调用绑定的 func
    args.func(args)
    
def parse_args():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    # init 子命令
    init_parser = commands.add_parser('init')
    init_parser.set_defaults(func=init)  # 绑定 func

    # hash-object 子命令
    hash_object_parser = commands.add_parser('hash-object')
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument('file')

    # cat-file 子命令
    cat_file_parser = commands.add_parser('cat-file')
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument('object')

    # write-tree 子命令
    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree)

    # read-tree 子命令
    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree')
    
    # commit 子命令
    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True)

    # log 子命令
    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid', nargs='?')

    #checkout 子命令
    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('oid')

    return parser.parse_args()

def init(args):
    data.init()
    print(f'Initialized empty ugit repository in {os.getcwd}/{data.GIT_DIR}')

# hash_object: 存储对象进入数据库并返回对应oid
def hash_object(args):
    with open (args.file, 'rb') as f:
        print(data.hash_object(f.read()))

# cat-file: 显示对象内容
def cat_file(args):
    sys.stdout.flush()
    sys.stdout.buffer.write(data.get_object(args.object, expected=None))

# write-tree: 写入目录树(会覆盖当前目录)
def write_tree(args):
    print(base.write_tree())

# read-tree: 读取目录树
def read_tree(args):
    base.read_tree(args.tree)

# commit: 创建提交
def commit(args):
    # args.message 由 commit_parser.add_argument('-m', '--message', required=True) 的 '--message' 自动生成并被绑定用户输入
    print(base.commit(args.message))

# log: 显示提交历史
def log(args):
    oid = args.oid or data.get_HEAD()
    while oid:
        commit = base.get_commit(oid)

        print(f'commit {oid}')
        print(textwrap.indent(commit.message, '    '))
        print('')

        oid = commit.parent

# checkout: 切换到提交 
def checkout(args):
    base.checkout(args.oid)