/** Consume the backend's Server-Sent-Events answer stream via fetch (so we can send the
 *  Authorization header, which EventSource cannot). Parses `data: {json}` frames and
 *  forwards each decoded event to `onEvent`. */
import { apiBase } from "./api";
import { tokenStore } from "./auth";
import type { StreamEvent } from "./types";

export async function streamQuery(
  documentId: string,
  question: string,
  onEvent: (event: StreamEvent) => void,
  opts: { topK?: number; signal?: AbortSignal } = {},
): Promise<void> {
  const token = tokenStore.getAccess();
  const res = await fetch(`${apiBase}/documents/${documentId}/query/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ question, top_k: opts.topK ?? null }),
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`Query failed (${res.status})`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        onEvent(JSON.parse(json) as StreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
