"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import AuthGuard from "@/components/AuthGuard";
import ChatPanel from "@/components/ChatPanel";
import { getDocument } from "@/lib/api";
import type { DocumentRead } from "@/lib/types";

function ChatView({ documentId }: { documentId: string }) {
  const [doc, setDoc] = useState<DocumentRead | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDocument(documentId)
      .then(setDoc)
      .catch((e) => setError((e as Error).message));
  }, [documentId]);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <Link href="/documents" className="text-sm text-slate-500 hover:text-slate-800">
          ← Documents
        </Link>
        <span className="truncate font-medium text-slate-800">
          {doc?.filename ?? "Document"}
        </span>
      </div>

      {error && <p className="p-4 text-sm text-red-600">{error}</p>}

      {doc && doc.status !== "ready" ? (
        <p className="p-6 text-center text-slate-500">
          This document is <strong>{doc.status}</strong> and can’t be queried yet.
        </p>
      ) : (
        <ChatPanel documentId={documentId} />
      )}
    </div>
  );
}

export default function ChatPage() {
  const params = useParams();
  const documentId = String(params.docId);
  return (
    <AuthGuard>
      <ChatView documentId={documentId} />
    </AuthGuard>
  );
}
