"use client";

import Link from "next/link";

import type { DocumentRead, DocumentStatus } from "@/lib/types";

const STATUS_STYLES: Record<DocumentStatus, string> = {
  processing: "bg-amber-100 text-amber-800",
  ready: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface Props {
  document: DocumentRead;
  onDelete: (id: string) => void;
}

export default function DocumentCard({ document, onDelete }: Props) {
  const ready = document.status === "ready";
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium text-slate-800">{document.filename}</p>
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[document.status]}`}
          >
            {document.status}
          </span>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {document.extraction_method.toUpperCase()} · {formatBytes(document.size_bytes)} ·{" "}
          {document.page_count} pages · {document.chunk_count} chunks
        </p>
        {document.error && <p className="mt-1 text-xs text-red-600">{document.error}</p>}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {ready && (
          <Link
            href={`/chat/${document.id}`}
            className="rounded-md bg-brand-600 px-3 py-1.5 text-sm text-white hover:bg-brand-700"
          >
            Chat
          </Link>
        )}
        <button
          onClick={() => onDelete(document.id)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
