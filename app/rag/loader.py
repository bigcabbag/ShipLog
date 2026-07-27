from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

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


def load_and_split_pdf(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """读取 PDF 并切成多个 Document 块。"""
    loader = PyPDFLoader(str(file_path))
    pages = loader.load()
    return _split_documents(pages, chunk_size, chunk_overlap)


def load_and_split_markdown(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """读取 Markdown 并切块；metadata.source 用文件名。"""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []

    doc = Document(
        page_content=text,
        metadata={"source": path.name, "page": 0},
    )
    return _split_documents([doc], chunk_size, chunk_overlap)


def load_and_split_document(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """按后缀选择 PDF 或 Markdown 加载器。"""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return load_and_split_pdf(file_path, chunk_size, chunk_overlap)
    if suffix == ".md":
        return load_and_split_markdown(file_path, chunk_size, chunk_overlap)
    raise ValueError(f"不支持的文件类型: {suffix}，仅 {sorted(SUPPORTED_SUFFIXES)}")
