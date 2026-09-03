"""国内 HuggingFace 镜像引导：必须在任何 langchain / hub 导入之前执行。

WinError 10060 连 huggingface.co 时，几乎都是「先 import 了 hub，再设 HF_ENDPOINT」——
hub 会在 import 时把 ENDPOINT 写死，事后改环境变量无效。

用法（入口脚本 / 模块顶）：
    import app.hf_bootstrap  # noqa: F401
或：
    from app.hf_bootstrap import ensure_hf_mirror
    ensure_hf_mirror()
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_MIRROR = "https://hf-mirror.com"
_BOOTSTRAPPED = False


def ensure_hf_mirror() -> str:
    """设置 HF_ENDPOINT，并热修补已加载的 huggingface_hub.constants.ENDPOINT。"""
    global _BOOTSTRAPPED

    # 尽量先读 .env（不依赖完整 config，避免循环 import）
    try:
        from dotenv import load_dotenv

        root = Path(__file__).resolve().parent.parent
        load_dotenv(root / ".env", encoding="utf-8-sig")
    except Exception:
        pass

    endpoint = os.getenv("HF_ENDPOINT", "").strip() or _DEFAULT_MIRROR
    # 空字符串或误配成官网时，国内一律回落到镜像（可用 HF_ENDPOINT 显式指定其它镜像）
    if "huggingface.co" in endpoint.replace("www.", ""):
        endpoint = _DEFAULT_MIRROR
    os.environ["HF_ENDPOINT"] = endpoint

    try:
        import huggingface_hub.constants as constants

        constants.ENDPOINT = endpoint.rstrip("/")
    except ImportError:
        pass

    _BOOTSTRAPPED = True
    return endpoint


# 模块被 import 时立即执行一次
ensure_hf_mirror()
