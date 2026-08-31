"""事故锚点：多轮检索 query 钉住当前故障（不连库）。"""

from app.rag.session_context import (
    format_anchor_system_note,
    resolve_incident_anchor,
)


def test_first_turn_stores_candidate_as_anchor():
    search, anchor = resolve_incident_anchor(
        query="怎么处理？",
        prior_anchor=None,
        candidate="DROP DATABASE shiplog_payments by app_migrator",
    )
    assert "DROP DATABASE" in (anchor or "")
    assert "DROP DATABASE" in search
    assert "怎么处理" in search


def test_followup_keeps_prior_and_prefixes_search():
    search, anchor = resolve_incident_anchor(
        query="你刚才说 OOM 错了，重新答截图那个",
        prior_anchor="DROP DATABASE shiplog_payments unauthorized_ddl",
        candidate=None,
    )
    assert anchor == "DROP DATABASE shiplog_payments unauthorized_ddl"
    assert search.startswith("DROP DATABASE")
    assert "OOM" in search


def test_clear_markers_replace_anchor():
    search, anchor = resolve_incident_anchor(
        query="新告警：Redis 连接超时怎么查",
        prior_anchor="DROP DATABASE shiplog_payments",
        candidate=None,
    )
    assert "DROP" not in (anchor or "")
    assert "Redis" in (anchor or "")
    assert "Redis" in search


def test_text_only_first_turn_uses_query_as_anchor():
    search, anchor = resolve_incident_anchor(
        query="Pod OOMKilled 反复重启怎么办？",
        prior_anchor=None,
        candidate=None,
    )
    assert anchor == "Pod OOMKilled 反复重启怎么办？"
    assert search == "Pod OOMKilled 反复重启怎么办？"


def test_anchor_system_note_mentions_pin():
    note = format_anchor_system_note("DROP DATABASE prod")
    assert "DROP DATABASE" in note
    assert "锚点" in note
