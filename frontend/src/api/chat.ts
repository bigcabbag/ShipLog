import { API_BASE_URL } from "../config";

export type SourceChunk = {
  source: string;
  page: number | string;
  content: string;
};

export type ChatRequestBody = {
  message: string;
  use_rag?: boolean;
  top_k?: number;
  system_prompt?: string | null;
};

export type ChatResponseBody = {
  reply: string;
  model: string;
  sources: SourceChunk[] | null;
  trace_id?: string | null;
};

export async function postChat(body: ChatRequestBody): Promise<ChatResponseBody> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
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

  return response.json() as Promise<ChatResponseBody>;
}
