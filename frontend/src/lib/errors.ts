/**
 * Narrow an unknown thrown value to a readable message.
 *
 * `catch` bindings are `unknown` under `strict`, so every call site used to
 * annotate them as `any` just to read `.message`. This helper keeps the same
 * ergonomics without disabling type safety.
 */
export function errorMessage(error: unknown, fallback = 'Terjadi kesalahan'): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string' && error) return error;
  if (error && typeof error === 'object' && 'message' in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === 'string' && message) return message;
  }
  return fallback;
}

/** True when a fetch was aborted via AbortController. */
export function isAbortError(error: unknown): boolean {
  return (
    (error instanceof DOMException && error.name === 'AbortError') ||
    (error instanceof Error && error.name === 'AbortError')
  );
}
