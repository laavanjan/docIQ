"use client";

import { useCallback, useEffect, useState } from "react";

import { deleteDocument, listDocuments } from "@/lib/api";
import { logger } from "@/lib/logger";
import type { DocumentRead } from "@/lib/types";

import DocumentCard from "./DocumentCard";
import UploadForm from "./UploadForm";

export default function DocumentList() {
  const [documents, setDocuments] = useState<DocumentRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  // Poll while any document is still processing.
  useEffect(() => {
    if (!documents.some((d) => d.status === "processing")) return;
    const timer = setInterval(() => {
      refresh().catch((e) => logger.warn("poll failed", { error: String(e) }));
    }, 3000);
    return () => clearInterval(timer);
  }, [documents, refresh]);

  async function handleDelete(id: string) {
    await deleteDocument(id);
    refresh();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8">
      <UploadForm onUploaded={refresh} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-800">Your documents</h2>
        {loading && <p className="text-slate-500">Loading…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && documents.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 p-6 text-center text-slate-500">
            No documents yet. Upload a PDF to get started.
          </p>
        )}
        {documents.map((doc) => (
          <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} />
        ))}
      </section>
    </div>
  );
}
