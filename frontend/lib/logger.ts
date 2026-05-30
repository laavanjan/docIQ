/**
 * Tiny structured client-side logger. Verbose in development, quiet (warn/error only)
 * in production. Keeps a single shape so logs are easy to scan in the browser console.
 */
type Level = "debug" | "info" | "warn" | "error";

const isDev = process.env.NODE_ENV !== "production";

/* eslint-disable no-console */
function emit(level: Level, message: string, meta?: Record<string, unknown>) {
  if (!isDev && (level === "debug" || level === "info")) return;
  const entry = { ts: new Date().toISOString(), level, message, ...(meta ?? {}) };
  const fn =
    level === "debug"
      ? console.debug
      : level === "info"
        ? console.info
        : level === "warn"
          ? console.warn
          : console.error;
  fn(`[${level}] ${message}`, meta ? entry : "");
}

export const logger = {
  debug: (m: string, meta?: Record<string, unknown>) => emit("debug", m, meta),
  info: (m: string, meta?: Record<string, unknown>) => emit("info", m, meta),
  warn: (m: string, meta?: Record<string, unknown>) => emit("warn", m, meta),
  error: (m: string, meta?: Record<string, unknown>) => emit("error", m, meta),
};
