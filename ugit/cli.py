import argparse
import os
import sys
import textwrap
import subprocess

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

    # 获取转换函数引用
    oid = base.get_oid

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
    cat_file_parser.add_argument('object', type=oid) # 使用转换函数作为参数类型

    # write-tree 子命令
    write_tree_parser = commands.add_parser('write-tree')
    write_tree_parser.set_defaults(func=write_tree)

    # read-tree 子命令
    read_tree_parser = commands.add_parser('read-tree')
    read_tree_parser.set_defaults(func=read_tree)
    read_tree_parser.add_argument('tree', type=oid)
    
    # commit 子命令
    commit_parser = commands.add_parser('commit')
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument('-m', '--message', required=True)

    # log 子命令
    log_parser = commands.add_parser('log')
    log_parser.set_defaults(func=log)
    log_parser.add_argument('oid',default='@', type=oid, nargs='?')

    #checkout 子命令
    checkout_parser = commands.add_parser('checkout')
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument('oid', type=oid)

    # tag 子命令
    tag_parser = commands.add_parser('tag')
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument('name')
    tag_parser.add_argument('oid' ,default='@', type=oid, nargs='?')

    # k 子命令
    k_parser = commands.add_parser('k')
    k_parser.set_defaults(func=k)

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
    oid = args.oid
    while oid:
        commit = base.get_commit(oid)

        print(f'commit {oid}')
        print(textwrap.indent(commit.message, '    '))
        print('')

        oid = commit.parent

# checkout: 切换到提交 
def checkout(args):
    base.checkout(args.oid)

# tag: 创建标签
def tag(args):
    base.create_tag(args.name, args.oid)

# k: 可视化记录
def k(args):
    # 添加中文字体支持
    dot = '''digraph commits {
    graph [fontname="Microsoft YaHei"];
    node [fontname="Microsoft YaHei"];
    edge [fontname="Microsoft YaHei"];
'''
    # 1. 收集所有引用的OID
    oids = set()
    for refname, ref in data.iter_refs():
        dot += f'"{refname}" [shape=note]\n'
        dot += f'"{refname}" -> "{ref}"\n'
        oids.add(ref)

    # 2. 遍历所有提交及其父提交
    for oid in base.iter_commits_and_parents(oids):
        commit = base.get_commit(oid)
        dot += f'"{oid}" [shape=box style=filled label="{oid[:10]}\n{commit.message}"]\n'
        if commit.parent:
            dot += f'"{oid}" -> "{commit.parent}"\n'
        
    dot += '}'
    
    # 3. 保存到临时文件，使用 utf-8 编码
    temp_file = 'graph.dot'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(dot)
    
    try:
        # 使用 -Gcharset=utf-8 参数
        subprocess.run(['dot', '-Gcharset=utf-8', '-Tpng', temp_file, '-o', 'graph.png'])
        subprocess.run(['start', 'graph.png'], shell=True)
    except FileNotFoundError:
        print('Graphviz not found. DOT 格式输出如下:')
        print('\n' + dot)
        print('\n请将以上内容复制到 https://dreampuf.github.io/GraphvizOnline/')