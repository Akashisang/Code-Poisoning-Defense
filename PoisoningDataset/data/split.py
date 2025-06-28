#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import random
import argparse

def split_py_files(src_dir, dst1, dst2, move_files=True):
    # 1. 递归收集所有 .py 文件
    py_files = []
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))

    random.shuffle(py_files)
    half = len(py_files) // 2
    groups = [py_files[:half], py_files[half:]]

    for dst, group in zip((dst1, dst2), groups):
        for src_path in group:
            rel = os.path.relpath(src_path, src_dir)
            dst_path = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            if move_files:
                shutil.move(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)


def main():
    parser = argparse.ArgumentParser(description="随机平分 .py 文件到两个文件夹")
    parser.add_argument("src_dir", help="源目录（只扫描此目录下的 .py 文件）")
    parser.add_argument("dst1",   help="目标目录 1")
    parser.add_argument("dst2",   help="目标目录 2")
    parser.add_argument("--copy", action="store_true",
                        help="如果指定，则复制文件；默认是移动文件")
    args = parser.parse_args()

    split_py_files(args.src_dir, args.dst1, args.dst2, move_files=not args.copy)

if __name__ == "__main__":
    main()