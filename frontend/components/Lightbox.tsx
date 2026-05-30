"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchImageObjectUrl } from "@/lib/api";
import type { DocumentImage } from "@/lib/types";

interface Props {
  documentId: string;
  images: DocumentImage[];
  index: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export default function Lightbox({ documentId, images, index, onClose, onNavigate }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const image = images[index];

  const go = useCallback(
    (delta: number) => onNavigate((index + delta + images.length) % images.length),
    [index, images.length, onNavigate],
  );

  // Load the active image (authenticated) as an object URL.
  useEffect(() => {
    let revoked = false;
    let obj: string | null = null;
    setUrl(null);
    fetchImageObjectUrl(documentId, image.id)
      .then((u) => {
        if (revoked) URL.revokeObjectURL(u);
        else {
          obj = u;
          setUrl(u);
        }
      })
      .catch(() => {});
    return () => {
      revoked = true;
      if (obj) URL.revokeObjectURL(obj);
    };
  }, [documentId, image.id]);

  // Keyboard navigation.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") go(1);
      else if (e.key === "ArrowLeft") go(-1);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, go]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4 text-sm text-white/80">
        <span>
          Page {image.page_number} · {index + 1} / {images.length}
        </span>
        <button onClick={onClose} className="rounded px-3 py-1 text-lg hover:bg-white/10" aria-label="Close">
          ✕
        </button>
      </div>

      {images.length > 1 && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            go(-1);
          }}
          className="absolute left-3 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-2xl text-white hover:bg-white/20"
          aria-label="Previous"
        >
          ‹
        </button>
      )}

      <div className="max-h-[85vh] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
        {url ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={url}
            alt={`Figure on page ${image.page_number}`}
            className="max-h-[85vh] max-w-[90vw] rounded-lg object-contain shadow-2xl"
          />
        ) : (
          <div className="flex h-64 w-64 items-center justify-center text-white/60">Loading…</div>
        )}
      </div>

      {images.length > 1 && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            go(1);
          }}
          className="absolute right-3 flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-2xl text-white hover:bg-white/20"
          aria-label="Next"
        >
          ›
        </button>
      )}
    </div>
  );
}
