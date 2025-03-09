import os
import subprocess

from collections import defaultdict
from tempfile import NamedTemporaryFile as Temp

from . import data
from . import myers_diff


def compare_trees(*trees):
    entries = defaultdict(lambda: [None] * len(trees))
    for i, tree in enumerate(trees):
        for path, oid in tree.items():
            entries[path][i] = oid 
    
    for path, oids in entries.items():
        yield (path, *oids)


def iter_changed_files(t_from, t_to):
    for path, o_from, o_to in compare_trees(t_from, t_to):
        if o_from != o_to:
            action = ('new file' if not o_from else
                      'deleted' if not o_to else
                      'modified')
            yield path, action


def diff_trees(t_from, t_to):
    output = b''
    for path, o_from, o_to in compare_trees(t_from, t_to):
            if o_from != o_to:
                output += diff_blobs(o_from, o_to, path)
    return output


def diff_blobs(o_from, o_to, path='blob'):
    """使用 Myers 算法比较两个文件对象"""
    try:
        # 尝试作为文本处理
        content_from = data.get_object(o_from).decode().splitlines() if o_from else []
        content_to = data.get_object(o_to).decode().splitlines() if o_to else []
        
        diff_result = myers_diff.shortest_edit(content_from, content_to)
        return myers_diff.format_diff(diff_result)
    except UnicodeDecodeError:
        # 如果是二进制文件，只显示文件已更改
        return f'Binary files {path} differ\n'.encode()


def merge_trees(t_HEAD, t_other):
    tree = {}
    for path, o_HEAD, o_other in compare_trees(t_HEAD, t_other):
        tree[path] = merge_blobs(o_HEAD, o_other)
    return tree


def merge_blobs(o_HEAD, o_other):
    """使用标准的 diff3 格式实现合并"""
    try:
        # 获取内容
        content_HEAD = data.get_object(o_HEAD).decode().splitlines() if o_HEAD else []
        content_other = data.get_object(o_other).decode().splitlines() if o_other else []
        
        # 处理特殊情况
        if not content_HEAD:
            return '\n'.join(content_other).encode()
        if not content_other:
            return '\n'.join(content_HEAD).encode()
        if content_HEAD == content_other:
            return '\n'.join(content_HEAD).encode()
        
        # 获取差异
        diff_result = myers_diff.shortest_edit(content_HEAD, content_other)
        
        # 预处理差异结果以检测重复行
        processed_diff = []
        common_lines = set()
        
        # 识别共同行
        for op, line in diff_result:
            if op == '=':
                common_lines.add(line)
                
        # 构建差异
        for op, line in diff_result:
            if op == '+' and line in common_lines:
                continue
            processed_diff.append((op, line))
        
        # 使用标准 diff3 格式构建输出
        output = []
        in_conflict = False
        
        for op, line in processed_diff:
            if op == '=':
                if in_conflict:
                    output.append('>>>>>>>')
                    in_conflict = False
                output.append(line)
            elif op == '-' and not in_conflict:
                output.append('<<<<<<< HEAD')
                output.append(line)
                output.append('=======')
                in_conflict = True
            elif op == '+':
                if not in_conflict:
                    output.append('<<<<<<< HEAD')
                    output.append('=======')
                    in_conflict = True
                output.append(line)
                
        if in_conflict:
            output.append('>>>>>>>')
            
        return '\n'.join(output).encode()
        
    except UnicodeDecodeError:
        return b'Binary files differ\n'

def find_git_diff():
    """查找 Git diff 命令的位置"""
    # 1. 检查环境变量
    git_path = os.getenv('GIT_PATH')
    if git_path:
        diff_path = os.path.join(git_path, 'usr', 'bin', 'diff.exe')
        if os.path.exists(diff_path):
            return diff_path

    # 2. 常见安装路径
    possible_paths = [
        r'C:\Program Files\Git\usr\bin\diff.exe',
        r'C:\Program Files (x86)\Git\usr\bin\diff.exe',
        r'D:\Program Files\Git\usr\bin\diff.exe',
        r'E:\Program Files\Git\usr\bin\diff.exe',
    ]
    
    # 3. 从 PATH 环境变量搜索
    for path in os.getenv('PATH', '').split(os.pathsep):
        diff_path = os.path.join(path, 'diff.exe')
        if os.path.exists(diff_path):
            return diff_path
            
    # 4. 检查可能的安装路径
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    raise FileNotFoundError('未找到 Git diff 命令，请确保 Git 已安装并添加到 PATH')