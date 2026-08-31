import { API_BASE_URL } from "../config";
import type { ChatRequestBody, SourceChunk } from "./chat";

export type ChatStreamDone = {
  model: string;
  sources: SourceChunk[] | null;
  trace_id?: string | null;
  extracted_query?: string | null;
  thread_id?: string | null;
  plan_steps?: string[] | null;
};

/** U-003：中间进度（vision / tool / status / plan） */
export type ChatStreamProgress = {
  event: string;
  message?: string;
  phase?: string;
  tool?: string;
  agent?: string;
  summary?: string;
  extracted_query?: string;
  plan_steps?: string[];
  thread_id?: string | null;
  args?: Record<string, unknown>;
};

export type ChatStreamHandlers = {
  onToken: (token: string) => void;
  onDone: (info: ChatStreamDone) => void;
  onExtracted?: (query: string) => void;
  onPlanSteps?: (steps: string[], threadId?: string | null) => void;
  onProgress?: (progress: ChatStreamProgress) => void;
};

type SsePayload = {
  event?: string;
  token?: string;
  done?: boolean;
  model?: string;
  sources?: SourceChunk[] | null;
  trace_id?: string | null;
  extracted_query?: string | null;
  thread_id?: string | null;
  plan_steps?: string[] | null;
  error?: string;
  warning?: string;
  message?: string;
  phase?: string;
  tool?: string;
  agent?: string;
  summary?: string;
  args?: Record<string, unknown>;
};

function parseSseDataLines(block: string): string[] {
  const lines: string[] = [];
  for (const line of block.split("\n")) {
    const trimmed = line.trimEnd();
    if (trimmed.startsWith("data:")) {
      lines.push(trimmed.slice(5).trimStart());
    }
  }
  return lines;
}

function progressLabel(payload: SsePayload): string {
  const ev = payload.event ?? "";
  if (ev === "vision_extract") {
    return `读图识别：${payload.extracted_query ?? "…"}`;
  }
  if (ev === "status") {
    return payload.message ?? "处理中…";
  }
  if (ev === "tool_start") {
    return `调用工具 ${payload.tool ?? payload.agent ?? "…"}`;
  }
  if (ev === "tool_end") {
    const tip = payload.summary ? `：${payload.summary}` : "";
    return `工具完成 ${payload.tool ?? payload.agent ?? ""}${tip}`;
  }
  if (ev === "plan_steps") {
    return "已生成排查计划";
  }
  return payload.message ?? ev;
}

/**
 * POST /chat/stream — 读 SSE；进度事件走 onProgress，token / done 同前。
 */
export async function postChatStream(
  body: ChatRequestBody,
  handlers: ChatStreamHandlers,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      use_rag: true,
      top_k: 3,
      ...body,
    }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = (await response.json()) as { detail?: string };
      if (err.detail) detail = err.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error("响应无 body，无法读流");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;

      const dataLines = parseSseDataLines(part);
      if (dataLines.length === 0) continue;

      let payload: SsePayload;
      try {
        payload = JSON.parse(dataLines.join("\n")) as SsePayload;
      } catch {
        throw new Error("SSE 事件 JSON 解析失败");
      }

      if (payload.error) {
        throw new Error(payload.error);
      }

      if (payload.event && handlers.onProgress) {
        handlers.onProgress({
          event: payload.event,
          message: progressLabel(payload),
          phase: payload.phase,
          tool: payload.tool,
          agent: payload.agent,
          summary: payload.summary,
          extracted_query: payload.extracted_query,
          plan_steps: payload.plan_steps ?? undefined,
          thread_id: payload.thread_id ?? null,
          args: payload.args,
        });
      }

      if (payload.plan_steps?.length && handlers.onPlanSteps) {
        handlers.onPlanSteps(payload.plan_steps, payload.thread_id ?? null);
      }

      if (typeof payload.token === "string") {
        handlers.onToken(payload.token);
      }

      if (payload.done) {
        if (payload.extracted_query && handlers.onExtracted) {
          handlers.onExtracted(payload.extracted_query);
        }
        handlers.onDone({
          model: payload.model ?? "",
          sources: payload.sources ?? null,
          trace_id: payload.trace_id ?? null,
          extracted_query: payload.extracted_query ?? null,
          thread_id: payload.thread_id ?? null,
          plan_steps: payload.plan_steps ?? null,
        });
        finished = true;
        return;
      }
    }
  }

  if (!finished) {
    throw new Error("流式中断：未收到结束事件");
  }
}
