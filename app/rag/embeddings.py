from functools import lru_cache

# 必须先 bootstrap：设置并热补 HF 镜像，再 import huggingface 相关包
import app.hf_bootstrap  # noqa: F401
from app.hf_bootstrap import ensure_hf_mirror

ensure_hf_mirror()
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_embedding_model


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    ensure_hf_mirror()
    return HuggingFaceEmbeddings(
        model_name=get_embedding_model(),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
