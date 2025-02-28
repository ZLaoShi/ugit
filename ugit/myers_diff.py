from typing import List, Tuple, Dict, Set
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

def shortest_edit(a: List[str], b: List[str]) -> List[Tuple[str, str]]:
    """
    使用Myers差分算法计算两个序列间的最短编辑脚本。
    
    Args:
        a: 源序列
        b: 目标序列
        
    Returns:
        List[Tuple[str, str]]: 编辑操作列表，每个元素是(操作类型, 内容)的元组
            操作类型可以是：
            '+': 添加
            '-': 删除
            '=': 保持不变
            
    Raises:
        ValueError: 当输入序列为None时
    """

    # 边界处理
    if not a and not b:
        return []
    if not a:
        return [('+', x) for x in b]
    if not b:
        return [('-', x) for x in a]
    
    n, m = len(a), len(b)
    max_d = n + m
    
    # 存储每个d级别的路径端点1
    v: Dict[int, int] = {0: 0}
    # 存储路径
    paths: Dict[Tuple[int, int], Tuple[int, int]] = {}
    
    # 查找最短编辑路径
    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            # 确定是向下还是向右移动
            go_down = (k == -d or 
                      (k != d and v.get(k - 1, float('-inf')) < v.get(k + 1, float('-inf'))))
            
            # 获取起始点
            old_k = k + 1 if go_down else k - 1
            start_x = v.get(old_k, 0)
            start_y = start_x - old_k
            
            # 计算新位置
            x = start_x if go_down else start_x + 1
            y = x - k
            
            # 沿对角线移动
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            
            # 更新路径端点
            v[k] = x
            paths[(x, y)] = (start_x, start_y)
            
            # 找到终点
            if x >= n and y >= m:
                return _build_diff(a, b, paths, n, m)
    
    return []

def _build_diff(a: List[str], b: List[str], paths, n, m):
    """构建差异结果，按正确顺序"""
    diff = []
    x, y = n, m
    
    # 收集所有坐标点
    coords = []
    while x > 0 or y > 0:
        coords.append((x, y))
        prev_x, prev_y = paths.get((x, y), (0, 0))
        x, y = prev_x, prev_y
    
    # 反转并处理
    coords.reverse()
    x = y = 0
    
    # 按顺序构建差异
    for next_x, next_y in coords:
        # 处理未变化的行
        while x < next_x and y < next_y:
            diff.append(('=', a[x]))
            x += 1
            y += 1
        # 处理删除的行
        if x < next_x:
            diff.append(('-', a[x]))
            x += 1
        # 处理添加的行
        if y < next_y:
            diff.append(('+', b[y]))
            y += 1
            
    return diff

def format_diff(diff):
    """格式化diff输出, 对齐行序"""
    output = []
    
    # 按行处理
    for op, line in diff:
        if op == '+':
            output.append(f'+{line}')
        elif op == '-':
            output.append(f'-{line}')
        else:
            output.append(f' {line}')
    
    return '\n'.join(output).encode()