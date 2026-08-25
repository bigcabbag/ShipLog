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
def is_rerank_enabled() -> bool:
    """M6.25：二阶段 Rerank。默认关闭（CPU/Docker 首请求会拉模型）；演示设 RERANK_ENABLED=1。"""
    raw = os.getenv("RERANK_ENABLED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@lru_cache
def get_rerank_model() -> str:
    return os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base").strip()


@lru_cache
def get_rerank_pool() -> int:
    """RRF/向量粗排池大小，再交给 CrossEncoder 截断到最终 top_k。"""
    try:
        return max(1, int(os.getenv("RERANK_POOL", "20").strip() or "20"))
    except ValueError:
        return 20


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
    dashscope_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    vision_model = os.getenv("VISION_MODEL", "").strip() or (
        "qwen3.7-flash" if dashscope_key else model
    )
    # 读图走通义 OpenAI 兼容接口（image_url）；Key 可用 VISION_API_KEY 或 DASHSCOPE_API_KEY
    vision_api_key = (
        os.getenv("VISION_API_KEY", "").strip() or dashscope_key or api_key
    ).strip()
    vision_base_env = os.getenv("VISION_BASE_URL", "").strip()
    if vision_base_env:
        vision_base_url = vision_base_env
    elif dashscope_key or os.getenv("VISION_API_KEY", "").strip():
        vision_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    else:
        vision_base_url = base_url

    if not api_key:
        raise RuntimeError("未找到 DEEPSEEK_API_KEY，请检查 .env 文件")
    if vision_model != model and not dashscope_key and not os.getenv("VISION_API_KEY", "").strip():
        raise RuntimeError(
            "已配置 VISION_MODEL 但未设置 DASHSCOPE_API_KEY 或 VISION_API_KEY"
        )
    if "dashscope.aliyuncs.com" in vision_base_url and vision_api_key == api_key:
        raise RuntimeError(
            "读图需通义 DashScope API Key：请在 .env 设置 DASHSCOPE_API_KEY，"
            "不能使用 DEEPSEEK_API_KEY（设置后需 docker compose up -d --build backend）"
        )

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "vision_model": vision_model,
        "vision_api_key": vision_api_key,
        "vision_base_url": vision_base_url,
        "embedding_model": get_embedding_model(),
    }