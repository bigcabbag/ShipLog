const STORAGE_KEY = "shiplog_thread_id";

export function getOrCreateThreadId(): string {
  try {
    const existing = localStorage.getItem(STORAGE_KEY)?.trim();
    if (existing) return existing;
    const created = crypto.randomUUID();
    localStorage.setItem(STORAGE_KEY, created);
    return created;
  } catch {
    return crypto.randomUUID();
  }
}

export function resetThreadId(): string {
  const created = crypto.randomUUID();
  try {
    localStorage.setItem(STORAGE_KEY, created);
  } catch {
    /* ignore */
  }
  return created;
}
