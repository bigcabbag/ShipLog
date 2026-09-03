# 先于 langchain：否则 hub.ENDPOINT 会被钉死成 huggingface.co（WinError 10060）
import app.hf_bootstrap  # noqa: F401

from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    settings = get_settings()
    return ChatOpenAI(
        model=settings["model"],
        api_key=SecretStr(settings["api_key"]),
        base_url=settings["base_url"],
        temperature=0.7,
    )


@lru_cache
def _vision_llm_cached(model: str, api_key: str, base_url: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=temperature,
    )


def get_vision_llm(*, temperature: float = 0) -> ChatOpenAI:
    settings = get_settings()
    return _vision_llm_cached(
        settings["vision_model"],
        settings["vision_api_key"],
        settings["vision_base_url"],
        temperature,
    )


def _build_chat_messages(
    message: str,
    system_prompt: str | None,
    history: list[dict] | None,
) -> list:
    messages: list = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    for item in history or []:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=message))
    return messages


async def chat(
    message: str,
    system_prompt: str | None = None,
    *,
    history: list[dict] | None = None,
) -> str:
    llm = get_llm()
    messages = _build_chat_messages(message, system_prompt, history)

    response = await llm.ainvoke(messages)
    content = response.content
    if isinstance(content, str):
        return content
    return str(content)


async def chat_with_image(
    text: str,
    image_base64: str,
    *,
    media_type: str = "image/png",
    system_prompt: str | None = None,
    temperature: float = 0,
) -> str:
    """M5.3：多模态读图（image_url + base64）。"""
    llm = get_vision_llm(temperature=temperature)
    data_url = f"data:{media_type};base64,{image_base64}"
    content: list[str | dict[str, Any]] = [{"type": "text", "text": text}]
    content.append({"type": "image_url", "image_url": {"url": data_url}})
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=content))

    response = await llm.ainvoke(messages)
    body = response.content
    if isinstance(body, str):
        return body
    return str(body)


async def chat_stream(
    message: str,
    system_prompt: str | None = None,
    *,
    history: list[dict] | None = None,
):
    """逐 token 生成，供 SSE 流式接口使用。"""
    llm = get_llm()
    messages = _build_chat_messages(message, system_prompt, history)

    async for chunk in llm.astream(messages):
        content = chunk.content
        if not content:
            continue
        if isinstance(content, str):
            yield content
        else:
            yield str(content)
