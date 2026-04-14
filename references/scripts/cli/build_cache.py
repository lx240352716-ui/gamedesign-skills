# -*- coding: utf-8 -*-
"""
文档解析缓存构建脚本 -- /init workflow 调用此脚本。

功能：
  扫描 knowledge/gamedocs/ 下所有 docx/xlsx/md 文件，
  调用 doc_reader 解析为 Markdown 并写入 .cache/ 目录。

用法：
  python references/scripts/cli/build_cache.py           # 增量解析（有缓存则跳过）
  python references/scripts/cli/build_cache.py --force   # 强制重新解析所有文件
"""

import os
import sys
import time

# 路径设置
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(SCRIPTS_DIR, 'core')
sys.path.insert(0, CORE_DIR)

from constants import BASE_DIR

GAMEDOCS_DIR = os.path.join(BASE_DIR, 'knowledge', 'gamedocs')
SUPPORTED_EXTS = ('.docx', '.xlsx', '.xls', '.md')


def main():
    force = '--force' in sys.argv

    if not os.path.exists(GAMEDOCS_DIR):
        print(f"[WARN] gamedocs/ 目录不存在: {GAMEDOCS_DIR}")
        print("[i] 请先将设计文档放入 knowledge/gamedocs/ 后重新运行")
        return

    # 扫描所有支持的文档
    doc_files = []
    for root, dirs, files in os.walk(GAMEDOCS_DIR):
        # 跳过 .cache/ 目录本身
        dirs[:] = [d for d in dirs if d != '.cache']
        for f in files:
            if f.startswith('~$'):
                continue
            if any(f.endswith(ext) for ext in SUPPORTED_EXTS):
                doc_files.append(os.path.join(root, f))

    if not doc_files:
        print(f"[WARN] knowledge/gamedocs/ 下没有找到文档文件")
        print("[i] 支持格式: .docx .xlsx .xls .md")
        return

    print(f"[i] 发现 {len(doc_files)} 个文档文件，开始解析...")

    from doc_reader import read_doc, _get_cache_path, _read_cache

    ok, skipped, failed = 0, 0, 0
    t0 = time.time()

    for fpath in doc_files:
        fname = os.path.basename(fpath)
        # 有缓存且不强制刷新则跳过
        if not force and _read_cache(fpath) is not None:
            skipped += 1
            continue
        try:
            chunks = read_doc(fpath, force=force)
            ok += 1
            print(f"  [OK] {fname} -> {len(chunks)} chunks")
        except Exception as e:
            failed += 1
            print(f"  [ERR] {fname}: {e}")

    elapsed = time.time() - t0
    print(f"\n[OK] 解析完成: 新解析 {ok} 个, 跳过 {skipped} 个缓存, 失败 {failed} 个, 耗时 {elapsed:.1f}s")
    if failed:
        print(f"[WARN] {failed} 个文件解析失败，检查文件格式或安装 markitdown")


if __name__ == '__main__':
    main()
