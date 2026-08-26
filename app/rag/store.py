"""M5.1：向量存储层（Chroma → PostgreSQL + pgvector）。

对外接口不变：get_vector_store() / index_chunks() / get_index_stats()。
retriever.py 依赖 store._collection.count()，用 PGVectorAdapter 兼容。
"""

import app.hf_bootstrap  # noqa: F401

from langchain_core.documents import Document
from langchain_postgres import PGVector
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

from app.config import get_database_url
from app.rag.bm25_index import get_bm25_stats, sync_chunks
from app.rag.embeddings import get_embeddings

COLLECTION_NAME = "rag_documents"


class PGVectorAdapter:
    """包装 PGVector，提供 retriever 依赖的 _collection.count() 兼容接口。"""

    def __init__(self, store: PGVector, connection: str):
        self._store = store
        self._connection = connection

    @property
    def _collection(self):
        """兼容 retriever.py 的 store._collection.count() 调用。"""

        class _CountProxy:
            def __init__(self, conn_str: str, collection: str):
                self._conn_str = conn_str
                self._collection = collection

            def count(self) -> int:
                return _count_vectors(self._conn_str, self._collection)

        return _CountProxy(self._connection, COLLECTION_NAME)

    def __getattr__(self, name: str):
        """其余方法直接代理给 PGVector（similarity_search 等）。"""
        return getattr(self._store, name)


def _count_vectors(conn_str: str, collection: str) -> int:
    """统计某 collection 下的向量数；表不存在时返回 0。"""
    engine = create_engine(conn_str)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                    WHERE c.name = :name
                    """
                ),
                {"name": collection},
            )
            row = result.fetchone()
            return int(row[0]) if row else 0
    except ProgrammingError:
        return 0


def get_vector_store() -> PGVectorAdapter:
    conn = get_database_url()
    store = PGVector(
        collection_name=COLLECTION_NAME,
        connection=conn,
        embeddings=get_embeddings(),
    )
    return PGVectorAdapter(store, conn)


def clear_collection() -> int:
    """清空当前向量集合全部 embedding（切块消融 / 全量重建前用）。"""
    engine = create_engine(get_database_url())
    deleted = 0
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                DELETE FROM langchain_pg_embedding e
                USING langchain_pg_collection c
                WHERE e.collection_id = c.uuid AND c.name = :name
                """
            ),
            {"name": COLLECTION_NAME},
        )
        deleted = int(result.rowcount or 0)
    # BM25 随 rebuild_from_vector_store / 空库同步
    from app.rag.bm25_index import _save_records

    _save_records([])
    return deleted


def index_chunks(chunks: list[Document], source: str) -> int:
    """把切块写入 PG + BM25；同名文件会先删旧再写入。"""
    sync_chunks(chunks, source)

    store = get_vector_store()
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT c.uuid FROM langchain_pg_collection c "
                "JOIN langchain_pg_embedding e ON c.uuid = e.collection_id "
                "WHERE c.name = :name AND e.cmetadata->>'source' = :source"
            ),
            {"name": COLLECTION_NAME, "source": source},
        )
        ids = [str(row[0]) for row in result]

    if ids:
        store._store.delete(ids=ids)

    store._store.add_documents(chunks)
    return len(chunks)


def get_index_stats() -> dict[str, str | int]:
    """M5.1：统计 PG 向量数。空库时表可能还没建，返回 0。"""
    vector_count = _count_vectors(get_database_url(), COLLECTION_NAME)
    return {
        "collection": COLLECTION_NAME,
        "vector_count": int(vector_count),
        **get_bm25_stats(),
    }
