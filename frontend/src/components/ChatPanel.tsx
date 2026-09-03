import { useEffect, useRef, useState } from "react";
import { postChat } from "../api/chat";
import type { ChatMessage } from "../types/chat";
import { postChatStream } from "../api/chatStream";
import {
  prepareImageFile,
  prepareImageFromClipboard,
  type PendingImage,
} from "../utils/imageUtils";
import {
  getOrCreateThreadId,
  resetThreadId,
} from "../utils/threadId";
import {
  clearChatMessages,
  loadChatMessages,
  saveChatMessages,
} from "../utils/chatStorage";
import "./ChatPanel.css";

const EXAMPLE_QUESTIONS = [
  "Redis 连接超时怎么排查？",
  "Pod OOMKilled 反复重启怎么办？",
  "502 Bad Gateway 怎么定位？",
];

type ChatPanelProps = {
  disabled?: boolean;
};

/** 距底部小于该值视为「仍在跟读最新」 */
const NEAR_BOTTOM_PX = 80;

function ChatPanel({ disabled = false }: ChatPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const initialThreadId = getOrCreateThreadId();
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    loadChatMessages(initialThreadId),
  );
  const [input, setInput] = useState("");
  const [pendingImage, setPendingImage] = useState<PendingImage | null>(null);
  const [useRag, setUseRag] = useState(true);
  const [streamOn, setStreamOn] = useState(true);
  const [loading, setLoading] = useState(false);
  const [imageError, setImageError] = useState<string | null>(null);
  const [threadId, setThreadId] = useState(initialThreadId);
  /** 用户在底部附近时自动跟滚；上滑阅读则暂停，避免流式抢滚动条 */
  const [stickToBottom, setStickToBottom] = useState(true);
  /** U-003：SSE 中间状态文案 */
  const [streamStatus, setStreamStatus] = useState<string | null>(null);

  function isNearBottom(el: HTMLDivElement): boolean {
    return el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX;
  }

  function scrollMessagesToBottom() {
    const el = messagesRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }

  function handleMessagesScroll() {
    const el = messagesRef.current;
    if (!el) return;
    setStickToBottom(isNearBottom(el));
  }

  function jumpToLatest() {
    setStickToBottom(true);
    scrollMessagesToBottom();
  }

  useEffect(() => {
    if (!stickToBottom) return;
    scrollMessagesToBottom();
  }, [messages, loading, stickToBottom]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      saveChatMessages(threadId, messages);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [messages, threadId]);

  function patchMessage(id: string, patch: Partial<ChatMessage>) {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    );
  }

  async function attachImage(file: File) {
    setImageError(null);
    try {
      const img = await prepareImageFile(file);
      setPendingImage(img);
    } catch (err: unknown) {
      setImageError(err instanceof Error ? err.message : "图片处理失败");
    }
  }

  async function sendMessage(text: string, image: PendingImage | null = pendingImage) {
    const trimmed = text.trim();
    if ((!trimmed && !image) || loading || disabled) return;
    if (image && !useRag) {
      setImageError("截图提问需开启「基于知识库」");
      return;
    }

    const displayContent = trimmed || "（附带告警截图）";
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: displayContent,
      imagePreview: image?.previewUrl,
    };
    setStickToBottom(true);
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setPendingImage(null);
    setImageError(null);
    setStreamStatus(null);
    setLoading(true);

    const body = {
      message: trimmed,
      use_rag: useRag,
      thread_id: threadId,
      ...(image
        ? {
            image_base64: image.base64,
            image_media_type: image.mediaType,
          }
        : {}),
    };

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
        await postChatStream(body, {
          onPlanSteps: (steps, returnedThreadId) => {
            if (returnedThreadId) {
              setThreadId(returnedThreadId);
            }
            patchMessage(assistantId, { planSteps: steps });
          },
          onProgress: (progress) => {
            if (progress.message) {
              setStreamStatus(progress.message);
            }
            if (progress.event === "vision_extract" && progress.extracted_query) {
              patchMessage(assistantId, {
                extractedQuery: progress.extracted_query,
              });
            }
            if (progress.thread_id) {
              setThreadId(progress.thread_id);
            }
          },
          onToken: (token) => {
            setStreamStatus(null);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + token }
                  : m,
              ),
            );
          },
          onDone: ({ model, sources, trace_id, extracted_query, thread_id, plan_steps }) => {
            setStreamStatus(null);
            if (thread_id) {
              setThreadId(thread_id);
            }
            patchMessage(assistantId, {
              model: model || undefined,
              sources: sources ?? undefined,
              traceId: trace_id ?? undefined,
              extractedQuery: extracted_query ?? undefined,
              planSteps: plan_steps ?? undefined,
            });
          },
        });
      } catch (err: unknown) {
        setStreamStatus(null);
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
      const data = await postChat(body);
      if (data.thread_id) {
        setThreadId(data.thread_id);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.reply,
          sources: data.sources ?? undefined,
          model: data.model,
          traceId: data.trace_id ?? undefined,
          extractedQuery: data.extracted_query ?? undefined,
          planSteps: data.plan_steps ?? undefined,
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

  function handleNewSession() {
    clearChatMessages(threadId);
    setMessages([]);
    setInput("");
    setPendingImage(null);
    setStickToBottom(true);
    setThreadId(resetThreadId());
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void sendMessage(input);
  }

  async function handlePaste(e: React.ClipboardEvent) {
    const img = await prepareImageFromClipboard(e.clipboardData.items);
    if (img) {
      e.preventDefault();
      setPendingImage(img);
      setImageError(null);
    }
  }

  const canSend = !loading && !disabled && (input.trim().length > 0 || pendingImage !== null);

  return (
    <section className={`chat-panel card${disabled ? " chat-panel--disabled" : ""}`}>
      <div className="chat-panel__head">
        <h2>对话</h2>
        <div className="chat-panel__toggles">
          <button
            type="button"
            className="chat-panel__new-session"
            disabled={loading || disabled}
            onClick={handleNewSession}
          >
            新会话
          </button>
          <label className="chat-panel__rag-toggle">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
              disabled={loading || disabled}
            />
            知识库检索
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

      {disabled ? (
        <div className="chat-panel__gate">
          <strong>等待后端连接</strong>
          对话区会在服务就绪后启用。
          <br />
          请先运行 <code>docker compose up -d</code>
        </div>
      ) : (
        <>
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

      <div className="chat-panel__messages-wrap">
        <div
          className="chat-panel__messages"
          aria-live="polite"
          ref={messagesRef}
          onScroll={handleMessagesScroll}
        >
          {messages.length === 0 && (
            <p className="chat-panel__empty">
              输入问题开始排查。可粘贴告警截图（Ctrl+V）。先运行{" "}
              <code>uv run python scripts/import_docs.py</code> 导入 Runbook，或右侧上传 PDF。
            </p>
          )}
          {messages.map((msg) => (
            <article
              key={msg.id}
              className={`chat-bubble chat-bubble--${msg.role}${msg.error ? " chat-bubble--error" : ""}`}
            >
              <p className="chat-bubble__role">{msg.role === "user" ? "你" : "AI"}</p>
              {msg.planSteps && msg.planSteps.length > 0 && !msg.error && (
                <div className="chat-bubble__plan-wrap">
                  <p className="chat-bubble__plan-label">排查计划</p>
                  <ol className="chat-bubble__plan">
                    {msg.planSteps.map((step, i) => (
                      <li key={`${msg.id}-plan-${i}`}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
              {msg.imagePreview && (
                <img
                  className="chat-bubble__image"
                  src={msg.imagePreview}
                  alt="用户上传的告警截图"
                />
              )}
              <p className="chat-bubble__content">
                {msg.content}
                {loading &&
                  msg.role === "assistant" &&
                  !msg.error &&
                  msg.content &&
                  messages[messages.length - 1]?.id === msg.id && (
                    <span className="chat-panel__stream-cursor" aria-hidden="true" />
                  )}
                {!msg.content && loading && msg.role === "assistant" && (
                  <span className="chat-panel__typing" aria-hidden="true">
                    <span className="chat-panel__typing-dot" />
                    <span className="chat-panel__typing-dot" />
                    <span className="chat-panel__typing-dot" />
                  </span>
                )}
              </p>
              {msg.extractedQuery && !msg.error && (
                <p className="chat-bubble__meta">
                  已从截图识别：<code>{msg.extractedQuery}</code>
                </p>
              )}
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
          {loading && streamOn && (
            <p className="chat-panel__stream-status" aria-live="polite">
              <span className="chat-panel__typing" aria-hidden="true">
                <span className="chat-panel__typing-dot" />
                <span className="chat-panel__typing-dot" />
                <span className="chat-panel__typing-dot" />
              </span>
              {streamStatus ?? "检索与生成中"}
            </p>
          )}
          {loading && !streamOn && (
            <p className="chat-panel__loading">
              <span className="chat-panel__typing" aria-hidden="true">
                <span className="chat-panel__typing-dot" />
                <span className="chat-panel__typing-dot" />
                <span className="chat-panel__typing-dot" />
              </span>
              AI 正在思考
            </p>
          )}
          <div ref={messagesEndRef} />
        </div>
        {!stickToBottom && messages.length > 0 && (
          <button
            type="button"
            className="chat-panel__jump-latest"
            onClick={jumpToLatest}
          >
            ↓ 回到最新
          </button>
        )}
      </div>

      {pendingImage && (
        <div className="chat-panel__pending-image">
          <img src={pendingImage.previewUrl} alt="待发送截图预览" />
          <button
            type="button"
            className="chat-panel__remove-image"
            onClick={() => setPendingImage(null)}
            disabled={loading || disabled}
          >
            移除截图
          </button>
        </div>
      )}
      {imageError && <p className="chat-panel__image-error">{imageError}</p>}

      <form className="chat-panel__form" onSubmit={handleSubmit}>
        <textarea
          className="chat-panel__input"
          rows={2}
          placeholder="问 Runbook、事故复盘… 或粘贴告警截图"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading || disabled}
          onPaste={(e) => void handlePaste(e)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void sendMessage(input);
            }
          }}
        />
        <div className="chat-panel__actions">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            className="chat-panel__file-input"
            disabled={loading || disabled}
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void attachImage(file);
            }}
          />
          <button
            type="button"
            className="chat-panel__attach-btn"
            disabled={loading || disabled}
            onClick={() => fileInputRef.current?.click()}
          >
            贴图
          </button>
          <button type="submit" className="chat-panel__send" disabled={!canSend}>
            {loading ? "发送中" : "发送"}
          </button>
        </div>
      </form>
        </>
      )}
    </section>
  );
}

export type { ChatMessage } from "../types/chat";
export default ChatPanel;
