"""
DSA utilities
=============

This file implements small, *explicit* Data Structures & Algorithms primitives
used by ODIE. They are written in a clear educational style so you can reference
them in your DSA course report.

Included:
- Merge Sort (stable, O(n log n))
- Quick Sort (in-place partitioning, average O(n log n))
- Intersection of two sorted lists (two-pointer technique)
"""

from __future__ import annotations
from typing import List, Callable, TypeVar

T = TypeVar("T")

def merge_sort(arr: List[T], key: Callable[[T], object] = lambda x: x, reverse: bool = False) -> List[T]:
    """Stable merge sort."""
    if len(arr) <= 1:
        return arr[:]
    mid = len(arr) // 2
    left = merge_sort(arr[:mid], key=key, reverse=reverse)
    right = merge_sort(arr[mid:], key=key, reverse=reverse)
    return _merge(left, right, key=key, reverse=reverse)

def _merge(left: List[T], right: List[T], key: Callable[[T], object], reverse: bool) -> List[T]:
    out: List[T] = []
    # i and j are pointers into each sorted list
    i = j = 0
    while i < len(left) and j < len(right):
        a, b = key(left[i]), key(right[j])
        take_left = (a > b) if reverse else (a <= b)
        if take_left:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:])
    out.extend(right[j:])
    return out

def quick_sort(arr: List[T], key: Callable[[T], object] = lambda x: x, reverse: bool = False) -> List[T]:
    """Quick sort (in-place on a copy)."""
    a = arr[:]
    _quick_sort_inplace(a, 0, len(a) - 1, key, reverse)
    return a

def _quick_sort_inplace(a: List[T], lo: int, hi: int, key: Callable[[T], object], reverse: bool) -> None:
    if lo >= hi:
        return
    p = _partition(a, lo, hi, key, reverse)
    _quick_sort_inplace(a, lo, p - 1, key, reverse)
    _quick_sort_inplace(a, p + 1, hi, key, reverse)

def _partition(a: List[T], lo: int, hi: int, key: Callable[[T], object], reverse: bool) -> int:
    pivot = key(a[hi])
    i = lo
    for j in range(lo, hi):
        v = key(a[j])
        cond = (v >= pivot) if reverse else (v <= pivot)
        if cond:
            a[i], a[j] = a[j], a[i]
            i += 1
    a[i], a[hi] = a[hi], a[i]
    return i

def intersect_sorted(a: List[int], b: List[int]) -> List[int]:
    """Two-pointer intersection for sorted integer lists."""
    # i and j are pointers into each sorted list
    i = j = 0
    out: List[int] = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return out
