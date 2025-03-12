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


def merge_trees(t_base, t_HEAD, t_other):
    """三方合并树"""
    tree = {}
    for path, o_base, o_HEAD, o_other in compare_trees(t_base, t_HEAD, t_other):
        tree[path] = merge_blobs(o_base, o_HEAD, o_other)
    return tree


def merge_blobs(o_base, o_HEAD, o_other):
    """三方合并实现"""
    try:
        # 获取内容
        content_base = data.get_object(o_base).decode().splitlines() if o_base else []
        content_HEAD = data.get_object(o_HEAD).decode().splitlines() if o_HEAD else []
        content_other = data.get_object(o_other).decode().splitlines() if o_other else []
        
        # 处理特殊情况保持不变...

        # 修改差异收集逻辑
        base_to_HEAD = myers_diff.shortest_edit(content_base, content_HEAD)
        base_to_other = myers_diff.shortest_edit(content_base, content_other)
        
        # 更精确地收集变更
        HEAD_changes = []  # 改用列表保持顺序
        other_changes = []
        base_lines = content_base  # 不再使用集合，保持顺序
        
        # 收集 HEAD 的变更
        for op, line in base_to_HEAD:
            if op == '+':
                HEAD_changes.append(line)
            elif op == '-':
                # 记录删除的行
                base_idx = content_base.index(line)
                HEAD_changes.append(None)  # 标记删除
                
        # 收集 other 的变更
        for op, line in base_to_other:
            if op == '+':
                other_changes.append(line)
            elif op == '-':
                other_changes.append(None)  # 标记删除
        
        # 构建合并结果
        output = []
        in_conflict = False
        i = 0  # 跟踪当前处理的行位置
        
        while i < len(content_HEAD):
            line = content_HEAD[i]
            
            # 检查冲突：两边都改了相同行
            if line in other_changes and line not in base_lines:
                if not in_conflict:
                    output.append('<<<<<<< HEAD')
                    in_conflict = True
                output.append(line)
            # 检查冲突：一方修改另一方删除
            elif line in HEAD_changes and (
                any(l in other_changes for l in base_lines[i:i+1])):
                if not in_conflict:
                    output.append('<<<<<<< HEAD')
                    output.append(line)
                    output.append('||||||| base')
                    # 只添加相关的基准版本行
                    output.append(base_lines[i])
                    output.append('=======')
                    # 只添加相关的其他版本行
                    if i < len(other_changes) and other_changes[i]:
                        output.append(other_changes[i])
                    output.append('>>>>>>>')
            else:
                if in_conflict:
                    output.append('=======')
                    if i < len(other_changes) and other_changes[i]:
                        output.append(other_changes[i])
                    output.append('>>>>>>>')
                    in_conflict = False
                output.append(line)
            i += 1
        
        # 添加 other 中的新行（保持顺序）
        if not in_conflict:
            for i, line in enumerate(other_changes):
                if line and line not in HEAD_changes:
                    output.append(line)
        
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

def clean_merge_markers(content):
    """清理标准 diff3 格式的合并标记，但只在没有实际冲突的情况下"""
    lines = []
    head_section = []    # HEAD 部分的内容
    other_section = []   # OTHER 部分的内容
    current_section = None
    in_conflict = False
    has_conflict = False
    
    for line in content.splitlines():
        if line.startswith('<<<<<<< HEAD'):
            in_conflict = True
            current_section = head_section
            continue
        elif line == '=======':
            current_section = other_section
            continue
        elif line.startswith('>>>>>>>'):
            in_conflict = False
            # 检查这个冲突块是否有实际冲突
            if set(head_section) != set(other_section):
                # 发现冲突，恢复原始内容
                return content
            # 一个冲突块处理完毕，重置状态
            head_section = []
            other_section = []
            continue
            
        if in_conflict:
            current_section.append(line)
        else:
            lines.append(line)
    
    # 如果还在处理冲突块，说明格式有问题，返回原始内容
    if in_conflict:
        return content
        
    return '\n'.join(lines)