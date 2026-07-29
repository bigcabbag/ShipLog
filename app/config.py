import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

load_dotenv(_ENV_FILE, encoding="utf-8-sig")

# 国内默认走 HuggingFace 镜像（可在 .env 里覆盖 HF_ENDPOINT）
_hf_endpoint = os.getenv("HF_ENDPOINT", "").strip()
if not _hf_endpoint:
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"


@lru_cache
def get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5").strip()


@lru_cache
def get_database_url() -> str:
    """M5.1：PostgreSQL 连接串（Docker 由 compose 注入，本地开发可在 .env 配置）。"""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "未找到 DATABASE_URL，请在 .env 或环境变量中配置 "
            "（Docker 用户由 docker-compose.yml 自动注入）"
        )
    return url


@lru_cache
def get_settings() -> dict[str, str]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip()
    model = os.getenv("LLM_MODEL", "deepseek-v4-flash").strip()

    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查 .env 文件")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "embedding_model": get_embedding_model(),
    }