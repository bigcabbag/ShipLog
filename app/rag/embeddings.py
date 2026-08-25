from functools import lru_cache

# 必须先加载 config：设置 HF_ENDPOINT 镜像，再 import huggingface 相关包
# （huggingface_hub 在 import 时会把 ENDPOINT 写死进常量）
import app.config  # noqa: F401
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_embedding_model


@lru_cache
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=get_embedding_model(),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
