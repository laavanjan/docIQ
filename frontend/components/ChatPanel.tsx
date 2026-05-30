"use client";

import { useEffect, useRef, useState } from "react";

import { streamQuery } from "@/lib/query";
import type { StreamEvent } from "@/lib/types";

import MessageBubble, { type ChatMessage } from "./MessageBubble";

export default function ChatPanel({ documentId }: { documentId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** Update the last (assistant) message immutably from a stream event. */
  function applyEvent(event: StreamEvent) {
    setMessages((prev) => {
      const copy = prev.slice();
      const i = copy.length - 1;
      const last = { ...copy[i] };
      if (event.type === "delta") last.content += event.text;
      else if (event.type === "sources") last.sources = event.sources;
      else if (event.type === "done") {
        last.provider = event.provider;
        last.model = event.model;
      } else if (event.type === "error") {
        last.content += `\n\n_[error: ${event.detail}]_`;
      }
      copy[i] = last;
      return copy;
    });
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);
    try {
      await streamQuery(documentId, question, applyEvent);
    } catch (err) {
      applyEvent({ type: "error", detail: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <p className="mx-auto max-w-md text-center text-sm text-slate-500">
            Ask a question about this document. Answers are grounded in its content and cite page
            numbers.
          </p>
        )}
        {messages.map((m, idx) => (
          <MessageBubble key={idx} message={m} documentId={documentId} />
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSend} className="border-t border-slate-200 bg-white p-3">
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this document…"
            disabled={busy}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600"
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {busy ? "…" : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
