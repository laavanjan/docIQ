"use client";

import { useEffect, useMemo, useState } from "react";

import { fetchImageObjectUrl, listDocumentImages } from "@/lib/api";
import type { DocumentImage } from "@/lib/types";

import Lightbox from "./Lightbox";

function Thumbnail({
  documentId,
  image,
  onClick,
}: {
  documentId: string;
  image: DocumentImage;
  onClick: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked = false;
    let obj: string | null = null;
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

  return (
    <button
      onClick={onClick}
      title={`Page ${image.page_number}`}
      className="group relative h-24 w-24 shrink-0 overflow-hidden rounded-lg border border-slate-200 bg-slate-50 transition hover:border-brand-500 hover:shadow-md"
    >
      {url ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt={`Figure on page ${image.page_number}`}
          className="h-full w-full object-cover transition duration-200 group-hover:scale-105"
        />
      ) : (
        <div className="h-full w-full animate-pulse bg-slate-200" />
      )}
      <span className="absolute bottom-1 right-1 rounded bg-black/60 px-1 text-[10px] font-medium text-white">
        p.{image.page_number}
      </span>
    </button>
  );
}

export default function CitedImages({
  documentId,
  pages,
}: {
  documentId: string;
  pages: number[];
}) {
  const [images, setImages] = useState<DocumentImage[]>([]);
  const [active, setActive] = useState<number | null>(null);
  const key = useMemo(() => pages.join(","), [pages]);

  useEffect(() => {
    if (!pages.length) {
      setImages([]);
      return;
    }
    let cancelled = false;
    listDocumentImages(documentId, pages)
      .then((imgs) => !cancelled && setImages(imgs))
      .catch(() => !cancelled && setImages([]));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentId, key]);

  if (!images.length) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <p className="mb-1.5 text-xs font-medium text-slate-500">
        Figures from cited page{pages.length > 1 ? "s" : ""}
      </p>
      <div className="flex flex-wrap gap-2">
        {images.map((img, i) => (
          <Thumbnail
            key={img.id}
            documentId={documentId}
            image={img}
            onClick={() => setActive(i)}
          />
        ))}
      </div>
      {active !== null && (
        <Lightbox
          documentId={documentId}
          images={images}
          index={active}
          onClose={() => setActive(null)}
          onNavigate={setActive}
        />
      )}
    </div>
  );
}
