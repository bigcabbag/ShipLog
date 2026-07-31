"""M5.3：告警截图 → 文本 query（通义 Qwen 等多模态，思路 A）。"""

from __future__ import annotations

from app.llm import chat_with_image

VISION_EXTRACT_PROMPT = """你是 On-call 告警信息提取器。根据截图和用户附言，只输出可用于检索 Runbook 的短文本。

要求：
1. 提取告警名称/规则名、服务名、Pod/实例、指标、阈值、错误码、HTTP 状态等
2. 不要给出排查步骤，不要编造 Runbook 内容
3. 只输出一行或几行关键词，中文或英文均可
4. 若无法识别，输出 UNKNOWN"""


def build_retrieval_query(user_message: str, extracted: str) -> str:
    """合并用户文字与读图结果，供混合检索使用。"""
    parts: list[str] = []
    text = user_message.strip()
    vision = extracted.strip()
    if vision and vision.upper() != "UNKNOWN":
        parts.append(vision)
    if text:
        parts.append(text)
    if parts:
        return " ".join(parts)
    return "On-call 告警排查"


async def extract_query_from_image(
    user_message: str,
    image_base64: str,
    *,
    media_type: str = "image/png",
) -> str:
    """从告警截图提取检索用 query。"""
    prompt = VISION_EXTRACT_PROMPT
    if user_message.strip():
        prompt = f"{VISION_EXTRACT_PROMPT}\n\n用户附言：{user_message.strip()}"
    try:
        raw = await chat_with_image(
            prompt,
            image_base64,
            media_type=media_type,
            system_prompt="只输出提取结果，不要解释。",
            temperature=0,
        )
    except Exception as exc:
        from app.config import get_settings

        s = get_settings()
        raise RuntimeError(
            f"调用通义读图失败 ({s['vision_model']}): {exc}"
        ) from exc
    return raw.strip() or "UNKNOWN"
