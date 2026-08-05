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

export type ChatStreamHandlers = {
  onToken: (token: string) => void;
  onDone: (info: ChatStreamDone) => void;
  onExtracted?: (query: string) => void;
  onPlanSteps?: (steps: string[], threadId?: string | null) => void;
};

type SsePayload = {
  token?: string;
  done?: boolean;
  model?: string;
  sources?: SourceChunk[] | null;
  trace_id?: string | null;
  extracted_query?: string | null;
  thread_id?: string | null;
  plan_steps?: string[] | null;
  error?: string;
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

/**
 * POST /chat/stream — 读 SSE，逐 token 回调；结束时 onDone。
 * 无 Abort：调用方在 loading 期间禁用发送即可。
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
