/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * - Prepends the base URL + `/api/v1`.
 * - Attaches the bearer access token.
 * - On a 401, transparently tries a token refresh once, then retries the request.
 */
import { tokenStore } from "./auth";
import { logger } from "./logger";
import type { DocumentImage, DocumentRead, ExtractionMethod, UserRead } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PREFIX = "/api/v1";

export const apiBase = `${BASE}${PREFIX}`;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function toError(res: Response): Promise<ApiError> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, detail);
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  const res = await fetch(`${apiBase}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    tokenStore.clear();
    return false;
  }
  const data = await res.json();
  tokenStore.set(data.access_token, data.refresh_token);
  return true;
}

export async function apiFetch(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(options.headers ?? {});
  const token = tokenStore.getAccess();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${apiBase}${path}`, { ...options, headers });
  if (res.status === 401 && retry) {
    logger.debug("401 received, attempting token refresh");
    if (await refreshTokens()) return apiFetch(path, options, false);
  }
  return res;
}

export async function apiJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---- Auth ----------------------------------------------------------------

export async function login(email: string, password: string): Promise<void> {
  const body = new URLSearchParams({ username: email, password });
  const res = await fetch(`${apiBase}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw await toError(res);
  const data = await res.json();
  tokenStore.set(data.access_token, data.refresh_token);
}

export async function register(email: string, password: string): Promise<UserRead> {
  return apiJson<UserRead>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function fetchMe(): Promise<UserRead> {
  return apiJson<UserRead>("/auth/me");
}

// ---- Documents -----------------------------------------------------------

export async function listDocuments(): Promise<DocumentRead[]> {
  return apiJson<DocumentRead[]>("/documents");
}

export async function getDocument(id: string): Promise<DocumentRead> {
  return apiJson<DocumentRead>(`/documents/${id}`);
}

export async function uploadDocument(file: File, method: ExtractionMethod): Promise<DocumentRead> {
  const form = new FormData();
  form.append("file", file);
  form.append("method", method);
  // Do not set Content-Type; the browser sets the multipart boundary.
  return apiJson<DocumentRead>("/documents", { method: "POST", body: form });
}

export async function deleteDocument(id: string): Promise<void> {
  await apiJson<void>(`/documents/${id}`, { method: "DELETE" });
}

// ---- Document images -----------------------------------------------------

export async function listDocumentImages(
  documentId: string,
  pages?: number[],
): Promise<DocumentImage[]> {
  const query = pages && pages.length ? `?pages=${pages.join(",")}` : "";
  return apiJson<DocumentImage[]>(`/documents/${documentId}/images${query}`);
}

/** Fetch an image with auth and return an object URL (revoke it when done). */
export async function fetchImageObjectUrl(documentId: string, imageId: string): Promise<string> {
  const res = await apiFetch(`/documents/${documentId}/images/${imageId}`);
  if (!res.ok) throw new ApiError(res.status, "Failed to load image");
  return URL.createObjectURL(await res.blob());
}
