"use client";

import AuthGuard from "@/components/AuthGuard";
import DocumentList from "@/components/DocumentList";

export default function DocumentsPage() {
  return (
    <AuthGuard>
      <DocumentList />
    </AuthGuard>
  );
}
