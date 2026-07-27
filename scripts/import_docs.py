"""M4.0：把 docs/*.md 一键导入 Chroma 向量库。

用法（项目根目录）：
    uv run python scripts/import_docs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rag.bm25_index import rebuild_from_vector_store
from app.rag.loader import load_and_split_markdown
from app.rag.store import get_index_stats, index_chunks

DOCS_DIR = ROOT / "docs"


def main() -> None:
    md_files = sorted(DOCS_DIR.glob("*.md"))
    if not md_files:
        print(f"No markdown files in {DOCS_DIR}")
        sys.exit(1)

    total_chunks = 0
    for path in md_files:
        chunks = load_and_split_markdown(path)
        if not chunks:
            print(f"skip (empty): {path.name}")
            continue
        indexed = index_chunks(chunks, source=path.name)
        total_chunks += indexed
        print(f"OK {path.name}: {indexed} chunks")

    stats = get_index_stats()
    bm25_count = rebuild_from_vector_store()
    print(
        f"\nDone: {len(md_files)} files, {total_chunks} chunks indexed; "
        f"vector_count={stats['vector_count']}, bm25_count={bm25_count}"
    )


if __name__ == "__main__":
    main()
