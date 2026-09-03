import type { SourceChunk } from "../api/chat";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  imagePreview?: string;
  sources?: SourceChunk[];
  model?: string;
  traceId?: string;
  extractedQuery?: string;
  planSteps?: string[];
  error?: boolean;
};
