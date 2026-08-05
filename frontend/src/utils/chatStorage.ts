/** M6.2：按 thread_id 在 localStorage 缓存聊天气泡（刷新后 UI 恢复）。 */

import type { ChatMessage } from "../types/chat";

const STORAGE_PREFIX = "shiplog_messages_";

type StoredChatMessage = Omit<ChatMessage, "imagePreview"> & {
  hadImage?: boolean;
};

function storageKey(threadId: string): string {
  return `${STORAGE_PREFIX}${threadId.trim()}`;
}

function isPersistable(message: ChatMessage): boolean {
  if (message.role === "user") {
    return Boolean(message.content.trim() || message.imagePreview);
  }
  return Boolean(
    message.content.trim() ||
      message.planSteps?.length ||
      message.error ||
      message.sources?.length,
  );
}

function toStored(message: ChatMessage): StoredChatMessage {
  const { imagePreview, ...rest } = message;
  return imagePreview ? { ...rest, hadImage: true } : rest;
}

function fromStored(message: StoredChatMessage): ChatMessage {
  const { hadImage: _hadImage, ...rest } = message;
  return rest;
}

export function loadChatMessages(threadId: string): ChatMessage[] {
  const tid = threadId.trim();
  if (!tid) return [];
  try {
    const raw = localStorage.getItem(storageKey(tid));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((item): item is StoredChatMessage => {
        return (
          typeof item === "object" &&
          item !== null &&
          typeof (item as StoredChatMessage).id === "string" &&
          ((item as StoredChatMessage).role === "user" ||
            (item as StoredChatMessage).role === "assistant")
        );
      })
      .map(fromStored);
  } catch {
    return [];
  }
}

export function saveChatMessages(
  threadId: string,
  messages: ChatMessage[],
): void {
  const tid = threadId.trim();
  if (!tid) return;
  try {
    const payload = messages.filter(isPersistable).map(toStored);
    localStorage.setItem(storageKey(tid), JSON.stringify(payload));
  } catch {
    /* quota exceeded — 静默降级，不影响对话 */
  }
}

export function clearChatMessages(threadId: string): void {
  const tid = threadId.trim();
  if (!tid) return;
  try {
    localStorage.removeItem(storageKey(tid));
  } catch {
    /* ignore */
  }
}
