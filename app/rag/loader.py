from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.clean import clean_text
from app.rag.kb_meta import stamp_document_metadata

# 默认切块参数（M2.1 先用这组，M2.2 后可调）
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50

SUPPORTED_SUFFIXES = {".pdf", ".md"}


def _split_documents(
    documents: list[Document],
    chunk_size: int,
    chunk_overlap: int,
) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(documents)


def _stamp_chunks(chunks: list[Document], base_meta: dict) -> list[Document]:
    for chunk in chunks:
        merged = {**base_meta, **dict(chunk.metadata or {})}
        # 文档级字段以 base 为准（避免 splitter 冲掉）
        for key in ("source", "doc_type", "topic", "doc_version", "updated_at"):
            if key in base_meta:
                merged[key] = base_meta[key]
        chunk.metadata = merged
    return chunks


def load_and_split_pdf(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    *,
    source: str | None = None,
) -> list[Document]:
    """读取 PDF 并切成多个 Document 块（U-014：清洗 + 版本元数据）。"""
    path = Path(file_path)
    src = source or path.name
    loader = PyPDFLoader(str(path))
    pages = loader.load()
    cleaned_pages: list[Document] = []
    full_text_parts: list[str] = []
    for page in pages:
        cleaned = clean_text(page.page_content)
        if not cleaned.strip():
            continue
        full_text_parts.append(cleaned)
        cleaned_pages.append(
            Document(page_content=cleaned, metadata=dict(page.metadata or {}))
        )
    if not cleaned_pages:
        return []
    base_meta = stamp_document_metadata(
        source=src,
        cleaned_text="\n\n".join(full_text_parts),
        path=path,
    )
    chunks = _split_documents(cleaned_pages, chunk_size, chunk_overlap)
    return _stamp_chunks(chunks, base_meta)


def load_and_split_markdown(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    *,
    source: str | None = None,
) -> list[Document]:
    """读取 Markdown 并切块；U-014：清洗 + doc_version / updated_at / topic。"""
    path = Path(file_path)
    text = clean_text(path.read_text(encoding="utf-8"))
    if not text.strip():
        return []

    src = source or path.name
    base_meta = stamp_document_metadata(
        source=src,
        cleaned_text=text,
        path=path,
    )
    doc = Document(page_content=text, metadata=dict(base_meta))
    chunks = _split_documents([doc], chunk_size, chunk_overlap)
    return _stamp_chunks(chunks, base_meta)


def load_and_split_document(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    *,
    source: str | None = None,
) -> list[Document]:
    """按后缀选择 PDF 或 Markdown 加载器。"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_and_split_pdf(
            path, chunk_size, chunk_overlap, source=source or path.name
        )
    if suffix == ".md":
        return load_and_split_markdown(
            path, chunk_size, chunk_overlap, source=source or path.name
        )
    raise ValueError(f"不支持的文件类型: {suffix}，仅 {sorted(SUPPORTED_SUFFIXES)}")
