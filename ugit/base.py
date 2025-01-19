import os
import itertools
import operator
import string

from collections import deque, namedtuple

from . import data
from . import diff


def init():
    data.init()
    data.update_ref('HEAD', data.RefValue(symbolic=True, value='refs/heads/master'))


def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = f'{directory}/{entry.name}'
            if is_ignored(full):
                continue

            if entry.is_file(follow_symlinks=False):
                type_ = 'blob'
                with open(full, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = 'tree'
                oid = write_tree(full)
            entries.append((entry.name, oid, type_))

    tree = ''.join(f'{type_} {oid} {name}\n'
                   for name, oid, type_
                   in sorted(entries))
    return data.hash_object(tree.encode(), 'tree')
  

def _iter_tree_enrties(oid):
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid, name


def get_tree(oid, base_path=''):
    result = {}
    for type_, oid, name in _iter_tree_enrties(oid):
        assert '/' not in name
        assert name not in ('..', '.')
        path = base_path + name
        if type_ == 'blob':
            result[path] = oid
        elif type_ == 'tree':
            result.update(get_tree(oid, f'{path}/'))
        else:
            assert False, f'Unknown tree entry {type_}'
    return result


def get_working_tree():
    result = {}
    for root, _, filenames in os.walk('.'):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path) or not os.path.isfile(path):
                continue
            with open(path, 'rb') as f:
                result[path] = data.hash_object(f.read())
    return result


def _empty_current_directory():
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for filename in filenames:
            path = os.path.relpath(f'{root}/{filename}')
            if is_ignored(path):
                continue
            os.remove(path)
        for dirname in dirnames:
            path = os.path.relpath(f'{root}/{dirname}')
            if is_ignored(path):
                continue
            try:
                os.rmdir(path)
            except(FileNotFoundError, OSError):
                # 删除操作可能会失败，如果目录中包含被忽略的文件，
                # 所以这是可以接受的。
                pass

def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid))


def read_tree_merged(t_HEAD, t_other):
    _empty_current_directory()
    for path, blob in diff.merge_trees(get_tree(t_HEAD), get_tree(t_other)).items():
        os.makedirs(f'./{os.path.dirname(path)}', exist_ok=True)
        with open(path, 'wb') as f:
            f.write(blob)

def commit(message):
    commit = f'tree {write_tree()}\n'

    HEAD = data.get_ref('HEAD').value
    if HEAD:
        commit += f'parent {HEAD}\n'
        
    commit += '\n'
    commit += f'{message}\n'
    
    oid = data.hash_object(commit.encode(), 'commit')

    data.update_ref('HEAD',data.RefValue(symbolic=False, value=oid))

    return oid


def checkout (name):
    oid = get_oid(name)
    commit = get_commit(oid)
    read_tree (commit.tree)

    if is_branch(name):
        HEAD = data.RefValue(symbolic=True, value=f'refs/heads/{name}')
    else:
        HEAD = data.RefValue(symbolic=False, value=oid)

    data.update_ref('HEAD', HEAD, deref=False)


def reset(oid):
    data.update_ref('HEAD', data.RefValue(symbolic=False, value=oid))


def merge (other):
    HEAD = data.get_ref('HEAD').value
    assert HEAD
    c_HEAD = get_commit(HEAD)
    c_other = get_commit(other) 

    read_tree_merged(c_HEAD.tree, c_other.tree)
    print('Merged in working directory. Use "commit" to finish merge.')


def create_tag(name, oid):
    data.update_ref(f'refs/tags/{name}', data.RefValue(symbolic=False, value=oid))


def create_branch(name, oid):
    data.update_ref(f'refs/heads/{name}', data.RefValue(symbolic=False, value=oid))


def iter_branch_names():
    for refname, _ in data.iter_refs('refs/heads/'):
        yield os.path.relpath(refname, 'refs/heads/')

        
def is_branch(branch):
    return data.get_ref(f'refs/heads/{branch}').value is not None


def get_branch_name():
    HEAD = data.get_ref('HEAD', deref=False)
    if not HEAD.symbolic:
        return None
    HEAD = HEAD.value
    assert HEAD.startswith('refs/heads/')
    return os.path.relpath(HEAD, 'refs/heads/')


Commit = namedtuple('Commit', ['tree', 'parent', 'message'])



def get_commit(oid):
    parent = None

    commit = data.get_object(oid, 'commit').decode()
    lines = iter(commit.splitlines())
    for line in itertools.takewhile(operator.truth, lines):
        key, value = line.split(' ', 1)
        if key == 'tree':
            tree = value 
        elif key == 'parent':
            parent = value
        else:
            assert False, f'Unknown field {key}'
    
    message = '\n'.join(lines)
    return Commit(tree=tree, parent=parent, message=message)



def iter_commits_and_parents(oids):
    oids = deque(oids)
    visited = set()

    while oids:
        oid = oids.popleft() # 从左侧弹出，保持顺序
        if not oid or oid in visited:
            continue
        visited.add(oid)
        yield oid

        commit = get_commit(oid)
        # 从左侧添加父提交
        oids.appendleft(commit.parent)



def get_oid(name):
    if name == '@':name = 'HEAD' 
    # 使用名字
    refs_to_try = [
        f'{name}',  # 直接以支持直接使用HEAD
        f'refs/{name}',
        f'refs/tags/{name}',
        f'refs/heads/{name}',
    ]
    for ref in refs_to_try:
        if data.get_ref(ref, deref=False).value:
            return data.get_ref(ref).value

    # 使用SHA-1
    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name    
    
    assert False, f'Unknown name {name}'



# 通用的忽略函数
# 增强检查：同时检查 .git 和 .ugit
def is_ignored(path):
    normalized_path = path.replace('\\', '/')
    return '.ugit' in normalized_path.split('/') or '.git' in normalized_path.split('/')



# # linux 下的隐藏文件
# def is_ignored(path):
#     return '.ugit' in path.split('/')

# win 下的隐藏文件
# def is_ignored(path):
#     return '.ugit' in path.replace('\\', '/').split('/')