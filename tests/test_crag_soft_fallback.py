"""M6.27 / U-018：CRAG soft-fallback 路由纯函数测试。"""

from langchain_core.documents import Document

from app.rag.graph import decide_route_when_no_relevant


def _docs(n: int = 2) -> list[Document]:
    return [Document(page_content=f"chunk-{i}", metadata={"source": f"s{i}"}) for i in range(n)]


def test_no_relevant_first_pass_rewrites():
    assert (
        decide_route_when_no_relevant(
            rewrite_count=0,
            documents=_docs(),
            soft_fallback_enabled=True,
        )
        == "rewrite"
    )


def test_soft_fallback_after_rewrite_with_docs():
    assert (
        decide_route_when_no_relevant(
            rewrite_count=1,
            documents=_docs(),
            soft_fallback_enabled=True,
        )
        == "soft_generate"
    )


def test_hard_abstain_when_soft_disabled():
    assert (
        decide_route_when_no_relevant(
            rewrite_count=1,
            documents=_docs(),
            soft_fallback_enabled=False,
        )
        == "abstain"
    )


def test_hard_abstain_when_empty_docs_even_if_soft_on():
    assert (
        decide_route_when_no_relevant(
            rewrite_count=1,
            documents=[],
            soft_fallback_enabled=True,
        )
        == "abstain"
    )
