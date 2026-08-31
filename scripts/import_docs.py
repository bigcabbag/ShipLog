"""M5.2：把 docs/kb/**/*.md 一键导入 PostgreSQL 向量库。

用法（项目根目录）：
    uv run python scripts/import_docs.py
    uv run python scripts/import_docs.py --chunk-size 300 --chunk-overlap 30 --clear
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 先设 HF 镜像并热补 hub.ENDPOINT，再加载会间接 import huggingface_hub 的模块
import app.hf_bootstrap  # noqa: E402, F401
from app.rag.bm25_index import rebuild_from_vector_store  # noqa: E402
from app.rag.loader import (  # noqa: E402
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    load_and_split_markdown,
)
from app.rag.store import clear_collection, get_index_stats, index_chunks  # noqa: E402

KB_DIR = ROOT / "docs" / "kb"


def import_kb(*, chunk_size: int, chunk_overlap: int, clear: bool) -> None:
    md_files = sorted(KB_DIR.rglob("*.md"))
    if not md_files:
        print(f"No markdown files in {KB_DIR}")
        sys.exit(1)

    if clear:
        deleted = clear_collection()
        print(f"cleared collection embeddings={deleted}")

    total_chunks = 0
    for path in md_files:
        source = path.relative_to(KB_DIR).as_posix()
        chunks = load_and_split_markdown(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            source=source,
        )
        if not chunks:
            print(f"skip (empty): {path.name}")
            continue
        indexed = index_chunks(chunks, source=source)
        total_chunks += indexed
        ver = chunks[0].metadata.get("doc_version", "?")
        print(f"OK {source}: {indexed} chunks (v={ver})")

    stats = get_index_stats()
    bm25_count = rebuild_from_vector_store()
    print(
        f"\nDone: chunk={chunk_size}/{chunk_overlap}, {len(md_files)} files, "
        f"{total_chunks} chunks indexed; "
        f"vector_count={stats['vector_count']}, bm25_count={bm25_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import docs/kb into pgvector + BM25")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"切块大小（默认 {DEFAULT_CHUNK_SIZE}）",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help=f"切块 overlap（默认 {DEFAULT_CHUNK_OVERLAP}）",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="导入前清空向量集合（消融实验必开）",
    )
    args = parser.parse_args()
    if args.chunk_overlap >= args.chunk_size:
        print("chunk-overlap 必须小于 chunk-size")
        sys.exit(1)
    import_kb(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        clear=args.clear,
    )


if __name__ == "__main__":
    main()
