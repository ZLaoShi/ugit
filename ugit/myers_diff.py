from typing import List, Tuple, Dict, Set
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

def shortest_edit(a: List[str], b: List[str]) -> List[Tuple[str, str]]:
    """Myers差分算法核心实现"""
    n, m = len(a), len(b)
    max_d = n + m
    
    # 存储每个d级别的路径端点
    v: Dict[int, int] = {1: 0}
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

def _build_diff(a: List[str], b: List[str], 
                paths: Dict[Tuple[int, int], Tuple[int, int]], 
                n: int, m: int) -> List[Tuple[str, str]]:
    """构建差异结果"""
    diff = []
    x, y = n, m
    
    while x > 0 or y > 0:
        prev_x, prev_y = paths.get((x, y), (0, 0))
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            diff.append(('=', a[x]))
        if x > prev_x:
            x -= 1
            diff.append(('-', a[x]))
        elif y > prev_y:
            y -= 1
            diff.append(('+', b[y]))
            
    return list(reversed(diff))

def format_diff(diff: List[Tuple[str, str]]) -> bytes:
    """格式化差异输出"""
    output = []
    for op, line in diff:
        if op == '+':
            output.append(f'+{line}')
        elif op == '-':
            output.append(f'-{line}')
        else:
            output.append(f' {line}')
    return '\n'.join(output).encode()