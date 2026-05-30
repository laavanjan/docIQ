"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Source } from "@/lib/types";

import CitedImages from "./CitedImages";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  provider?: string;
  model?: string;
}

export default function MessageBubble({
  message,
  documentId,
}: {
  message: ChatMessage;
  documentId: string;
}) {
  const [showSources, setShowSources] = useState(false);
  const isUser = message.role === "user";

  // Pages the answer actually cites via [p.N]; fall back to retrieved source pages.
  const citedPages = useMemo(() => {
    if (isUser) return [];
    const set = new Set<number>();
    for (const m of message.content.matchAll(/\[p\.(\d+)\]/g)) set.add(Number(m[1]));
    if (set.size === 0 && message.sources) {
      message.sources.forEach((s) => set.add(s.page_number));
    }
    return Array.from(set).sort((a, b) => a - b);
  }, [isUser, message.content, message.sources]);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
          isUser ? "bg-brand-600 text-white" : "border border-slate-200 bg-white text-slate-800"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : message.content ? (
          <div className="prose prose-sm max-w-none prose-slate prose-p:my-1.5 prose-headings:mb-1 prose-headings:mt-2 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-pre:my-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        ) : (
          <p className="text-slate-400">…</p>
        )}

        {!isUser && message.provider && (
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-400">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
              {message.provider}
              {message.model ? ` · ${message.model}` : ""}
            </span>
            {message.sources && message.sources.length > 0 && (
              <button
                onClick={() => setShowSources((s) => !s)}
                className="underline hover:text-slate-600"
              >
                {showSources ? "Hide" : "Show"} {message.sources.length} source
                {message.sources.length > 1 ? "s" : ""}
              </button>
            )}
          </div>
        )}

        {!isUser && showSources && message.sources && (
          <ul className="mt-2 space-y-1.5 border-t border-slate-100 pt-2">
            {message.sources.map((s) => (
              <li key={s.chunk_id} className="text-xs text-slate-500">
                <span className="font-medium text-slate-600">p.{s.page_number}</span>{" "}
                <span className="text-slate-400">(score {s.score})</span> — {s.preview}
              </li>
            ))}
          </ul>
        )}

        {/* Figures from the pages the answer cites (only once the answer is complete). */}
        {!isUser && message.provider && citedPages.length > 0 && (
          <CitedImages documentId={documentId} pages={citedPages} />
        )}
      </div>
    </div>
  );
}
