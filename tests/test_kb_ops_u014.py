"""U-014：清洗 / 元数据 / 冲突策略单测（不连库）。"""

from langchain_core.documents import Document

from app.rag.clean import clean_text
from app.rag.conflict import resolve_kb_conflicts
from app.rag.kb_meta import content_version, infer_doc_type, infer_topic


def test_clean_collapses_blank_lines_and_strips_comments():
    raw = "a  \n\n\n\n<!-- note -->\nb\n"
    out = clean_text(raw)
    assert "<!--" not in out
    assert "\n\n\n" not in out
    assert out.startswith("a")
    assert out.endswith("b")


def test_infer_topic_strips_date_prefix():
    assert infer_topic("postmortems/2024-01-redis-cache-flush.md") == "redis-cache-flush"
    assert infer_topic("runbooks/redis-timeout.md") == "redis-timeout"
    assert infer_doc_type("runbooks/redis-timeout.md") == "runbook"
    assert infer_doc_type("postmortems/2024-01-redis-cache-flush.md") == "postmortem"


def test_content_version_stable():
    assert content_version("hello") == content_version("hello")
    assert content_version("hello") != content_version("hello!")


def test_conflict_prefers_runbook_over_postmortem_same_topic():
    docs = [
        Document(
            page_content="old pm",
            metadata={
                "source": "postmortems/2024-01-redis-timeout.md",
                "topic": "redis-timeout",
                "doc_type": "postmortem",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ),
        Document(
            page_content="runbook",
            metadata={
                "source": "runbooks/redis-timeout.md",
                "topic": "redis-timeout",
                "doc_type": "runbook",
                "updated_at": "2023-01-01T00:00:00Z",
            },
        ),
    ]
    ordered, notes = resolve_kb_conflicts(docs)
    assert ordered[0].metadata["doc_type"] == "runbook"
    assert ordered[1].metadata["doc_type"] == "postmortem"
    assert notes and "Runbook" in notes[0]


def test_conflict_newer_wins_same_type():
    docs = [
        Document(
            page_content="old",
            metadata={
                "source": "runbooks/a-v1.md",
                "topic": "disk-full",
                "doc_type": "runbook",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ),
        Document(
            page_content="new",
            metadata={
                "source": "runbooks/a-v2.md",
                "topic": "disk-full",
                "doc_type": "runbook",
                "updated_at": "2025-06-01T00:00:00Z",
            },
        ),
    ]
    ordered, notes = resolve_kb_conflicts(docs)
    assert ordered[0].page_content == "new"
    assert notes
