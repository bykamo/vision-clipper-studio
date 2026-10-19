/* ─────────────────────────────────────────────────────────────
   SHIMMER PRIMITIVE
   A soft sweeping highlight used by every skeleton block.
   ───────────────────────────────────────────────────────────── */
export function Shimmer({ className = '' }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden rounded-md bg-slate-800/70 ${className}`}
      aria-hidden="true"
    >
      <div className="absolute inset-0 -translate-x-full animate-[skeleton-shimmer_1.8s_infinite] bg-gradient-to-r from-transparent via-white/[0.07] to-transparent" />
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   ANALYZING SKELETON
   Mimics the clip-candidate card list that will appear after
   analysis finishes: header line + 3 candidate card shapes.
   ───────────────────────────────────────────────────────────── */
export function AnalyzingSkeleton() {
  return (
    <div
      className="flex flex-col h-full gap-2.5"
      role="status"
      aria-label="Sedang menganalisis video"
    >
      {/* Header skeleton */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Shimmer className="h-4 w-4 !rounded-full" />
          <Shimmer className="h-3 w-36" />
        </div>
        <Shimmer className="h-3 w-10" />
      </div>

      {/* Candidate card skeletons */}
      <div className="flex-1 min-h-0 space-y-2.5 overflow-hidden pr-1">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3"
            style={{ animation: `skeleton-fade-in 0.5s ease-out ${i * 0.15}s both` }}
          >
            <div className="flex items-start gap-2.5">
              <Shimmer className="h-6 w-6 !rounded-lg flex-shrink-0" />
              <div className="flex-1 min-w-0 space-y-1.5">
                <Shimmer className="h-2.5 w-3/4" />
                <Shimmer className="h-2 w-1/2" />
              </div>
              <Shimmer className="h-5 w-9 !rounded-full flex-shrink-0" />
            </div>
            <div className="mt-2.5 space-y-1.5">
              <Shimmer className="h-2 w-full" />
              <Shimmer className="h-2 w-11/12" />
              <Shimmer className="h-2 w-4/6" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   RENDERING SKELETON
   Mimics the output clip grid (2 columns) that will appear
   after rendering finishes.
   ───────────────────────────────────────────────────────────── */
export function RenderingSkeleton({ count = 4 }: { count?: number }) {
  const tiles = Math.min(4, Math.max(2, count));
  return (
    <div className="flex flex-col h-full gap-2.5" role="status" aria-label="Sedang merender video">
      {/* Header skeleton */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Shimmer className="h-4 w-4 !rounded-full" />
          <Shimmer className="h-3 w-40" />
        </div>
        <Shimmer className="h-3 w-10" />
      </div>

      {/* Output banner skeleton */}
      <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-2.5 flex items-center gap-2.5 flex-shrink-0">
        <Shimmer className="h-8 w-8 !rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <Shimmer className="h-2.5 w-28" />
          <Shimmer className="h-2 w-44" />
        </div>
        <Shimmer className="h-6 w-20 !rounded-xl" />
      </div>

      {/* Clip tile skeletons (2-col grid like the real output) */}
      <div className="flex-1 min-h-0 grid grid-cols-1 sm:grid-cols-2 gap-2 overflow-hidden pr-1">
        {Array.from({ length: tiles }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-2.5 flex flex-col gap-2"
            style={{ animation: `skeleton-fade-in 0.5s ease-out ${i * 0.12}s both` }}
          >
            <div className="flex items-center gap-2.5">
              <Shimmer className="h-7 w-7 !rounded-lg flex-shrink-0" />
              <div className="flex-1 min-w-0 space-y-1.5">
                <Shimmer className="h-2.5 w-4/5" />
                <Shimmer className="h-2 w-2/5" />
              </div>
            </div>
            {/* 9:16-ish thumbnail placeholder */}
            <div className="relative flex-1 min-h-[64px] rounded-lg overflow-hidden">
              <Shimmer className="absolute inset-0 !rounded-lg" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="h-6 w-6 rounded-full bg-slate-700/80 border border-slate-600/60" />
              </div>
            </div>
            <Shimmer className="h-5 w-full !rounded-lg" />
          </div>
        ))}
      </div>
    </div>
  );
}
