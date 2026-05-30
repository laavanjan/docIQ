export type ExtractionMethod = "text" | "ocr" | "vision";

export type DocumentStatus = "processing" | "ready" | "error";

export interface UserRead {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface DocumentRead {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  extraction_method: ExtractionMethod;
  status: DocumentStatus;
  page_count: number;
  chunk_count: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Source {
  chunk_id: string;
  page_number: number;
  score: number;
  preview: string;
}

export interface DocumentImage {
  id: string;
  page_number: number;
  image_index: number;
  width: number;
  height: number;
  ext: string;
}

/** Streaming SSE event shapes emitted by the /query/stream endpoint. */
export type StreamEvent =
  | { type: "sources"; sources: Source[] }
  | { type: "delta"; text: string }
  | {
      type: "done";
      provider: string;
      model: string;
      input_tokens: number;
      output_tokens: number;
      latency_ms: number;
      answer_chars: number;
    }
  | { type: "error"; detail: string };
