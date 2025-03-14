import subprocess

from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp

from . import data


def compare_trees (*trees):
    entries = defaultdict (lambda: [None] * len (trees))
    for i, tree in enumerate (trees):
        for path, oid in tree.items ():
            entries[path][i] = oid

    for path, oids in entries.items ():
        yield (path, *oids)


def iter_changed_files (t_from, t_to):
    for path, o_from, o_to in compare_trees (t_from, t_to):
        if o_from != o_to:
            action = ('new file' if not o_from else
                      'deleted' if not o_to else
                      'modified')
            yield path, action


def diff_trees (t_from, t_to):
    output = b''
    for path, o_from, o_to in compare_trees (t_from, t_to):
        if o_from != o_to:
            output += diff_blobs (o_from, o_to, path)
    return output


def diff_blobs (o_from, o_to, path='blob'):
    with Temp () as f_from, Temp () as f_to:
        for oid, f in ((o_from, f_from), (o_to, f_to)):
            if oid:
                f.write (data.get_object (oid))
                f.flush ()

        with subprocess.Popen (
            ['diff', '--unified', '--show-c-function',
             '--label', f'a/{path}', f_from.name,
             '--label', f'b/{path}', f_to.name],
            stdout=subprocess.PIPE) as proc:
            output, _ = proc.communicate ()

        return output


def merge_trees (t_base, t_HEAD, t_other):
    tree = {}
    for path, o_base, o_HEAD, o_other in compare_trees (t_base, t_HEAD, t_other):
        tree[path] = data.hash_object(merge_blobs(o_base, o_HEAD, o_other))
    return tree


def merge_blobs(o_base, o_HEAD, o_other):
    """三方合并实现"""
    with Temp() as f_base, Temp() as f_HEAD, Temp() as f_other:
        # 写入文件内容
        for oid, f in ((o_base, f_base), (o_HEAD, f_HEAD), (o_other, f_other)):
            if oid:
                try:
                    content = data.get_object(oid)
                    # 检查是否为二进制文件
                    try:
                        content.decode()
                    except UnicodeDecodeError:
                        return b'Binary files differ\n'
                    f.write(content)
                    f.flush()
                except:
                    continue

        try:
            # 调用 diff3
            with subprocess.Popen(
                ['diff3', '-m',
                 '-L', 'HEAD', f_HEAD.name,
                 '-L', 'BASE', f_base.name,
                 '-L', 'MERGE_HEAD', f_other.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE) as proc:
                output, stderr = proc.communicate()
                
                # diff3 返回值说明:
                # 0: 无冲突
                # 1: 有冲突
                # 2: 发生错误
                if proc.returncode == 2:
                    # 如果是二进制文件，返回特殊标记
                    if b'binary files' in stderr.lower():
                        return b'Binary files differ\n'
                    raise Exception(f'diff3 failed: {stderr.decode()}')
                    
                return output
                
        except FileNotFoundError:
            raise Exception("diff3 command not found. Please install diffutils.")