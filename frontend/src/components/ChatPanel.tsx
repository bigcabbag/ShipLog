import { useState } from "react";
import { postChat, type SourceChunk } from "../api/chat";
import { postChatStream } from "../api/chatStream";
import "./ChatPanel.css";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceChunk[];
  model?: string;
  traceId?: string;
  error?: boolean;
};

const EXAMPLE_QUESTIONS = [
  "Redis 连接超时怎么排查？",
  "Pod OOMKilled 反复重启怎么办？",
  "502 Bad Gateway 怎么定位？",
];

type ChatPanelProps = {
  disabled?: boolean;
};

function ChatPanel({ disabled = false }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [useRag, setUseRag] = useState(true);
  const [streamOn, setStreamOn] = useState(true);
  const [loading, setLoading] = useState(false);

  function patchMessage(id: string, patch: Partial<ChatMessage>) {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    );
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading || disabled) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    if (streamOn) {
      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: "",
        },
      ]);

      try {
        await postChatStream(
          { message: trimmed, use_rag: useRag },
          {
            onToken: (token) => {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + token }
                    : m,
                ),
              );
            },
            onDone: ({ model, sources, trace_id }) => {
              patchMessage(assistantId, {
                model: model || undefined,
                sources: sources ?? undefined,
                traceId: trace_id ?? undefined,
              });
            },
          },
        );
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "发送失败";
        setMessages((prev) => {
          const target = prev.find((m) => m.id === assistantId);
          if (target && target.content) {
            return prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: `${m.content}\n\n[错误] ${message}`,
                    error: true,
                  }
                : m,
            );
          }
          return prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: message, error: true }
              : m,
          );
        });
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      const data = await postChat({ message: trimmed, use_rag: useRag });
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
          sources: data.sources ?? undefined,
          model: data.model,
          traceId: data.trace_id ?? undefined,
        },
      ]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "发送失败";
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: message,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void sendMessage(input);
  }

  return (
    <section className="chat-panel card">
      <div className="chat-panel__head">
        <h2>ShipLog On-call 助手</h2>
        <div className="chat-panel__toggles">
          <label className="chat-panel__rag-toggle">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              disabled={loading || disabled}
            />
            基于知识库（use_rag）
          </label>
          <label className="chat-panel__rag-toggle">
            <input
              type="checkbox"
              checked={streamOn}
              onChange={(e) => setStreamOn(e.target.checked)}
              disabled={loading || disabled}
            />
            流式输出
          </label>
        </div>
      </div>

      <div className="chat-panel__examples">
        <span className="chat-panel__examples-label">试试：</span>
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            className="chat-panel__example-btn"
            disabled={loading || disabled}
            onClick={() => void sendMessage(q)}
          >
            {q}
          </button>
        ))}
      </div>

      <div className="chat-panel__messages" aria-live="polite">
        {messages.length === 0 && (
          <p className="chat-panel__empty">
            输入问题开始排查。先运行 <code>uv run python scripts/import_docs.py</code> 导入 Runbook 知识库，或左侧上传 PDF。
          </p>
        )}
        {messages.map((msg) => (
          <article
            key={msg.id}
            className={`chat-bubble chat-bubble--${msg.role}${msg.error ? " chat-bubble--error" : ""}`}
          >
            <p className="chat-bubble__role">{msg.role === "user" ? "你" : "AI"}</p>
            <p className="chat-bubble__content">
              {msg.content || (loading && msg.role === "assistant" ? "…" : "")}
            </p>
            {msg.traceId && !msg.error && (
              <p className="chat-bubble__meta">
                trace：<code>{msg.traceId}</code>
              </p>
            )}
            {msg.model && !msg.error && (
              <p className="chat-bubble__meta">模型：{msg.model}</p>
            )}
            {msg.sources && msg.sources.length > 0 && (
              <details className="chat-bubble__sources">
                <summary>引用来源（{msg.sources.length}）</summary>
                <ul>
                  {msg.sources.map((s, i) => (
                    <li key={`${s.source}-${s.page}-${i}`}>
                      <strong>
                        {s.source} · 第 {s.page} 页
                      </strong>
                      <p>{s.content}</p>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </article>
        ))}
        {loading && (
          <p className="chat-panel__loading">
            {streamOn ? "AI 正在生成…" : "AI 正在思考…"}
          </p>
        )}
      </div>

      <form className="chat-panel__form" onSubmit={handleSubmit}>
        <textarea
          className="chat-panel__input"
          rows={2}
          placeholder="问 Runbook、事故复盘或架构相关的问题…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || disabled}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage(input);
            }
          }}
        />
        <button type="submit" className="chat-panel__send" disabled={loading || disabled || !input.trim()}>
          {loading ? "发送中…" : "发送"}
        </button>
      </form>
    </section>
  );
}

export default ChatPanel;
