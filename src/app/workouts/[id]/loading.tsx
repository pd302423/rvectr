export default function WorkoutLoading() {
  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-3xl">

        {/* Header skeleton */}
        <div className="mb-10 border-b border-border pb-8 animate-pulse">
          <div className="h-2.5 w-24 rounded bg-muted mb-4" />
          <div className="h-9 w-56 rounded bg-muted mb-3" />
          <div className="flex gap-2">
            <div className="h-5 w-24 rounded bg-muted/60" />
            <div className="h-5 w-16 rounded bg-muted/60" />
          </div>
        </div>

        {/* Rationale skeleton */}
        <div className="mb-8 rounded border border-border bg-card p-5 animate-pulse space-y-2">
          <div className="h-2.5 w-28 rounded bg-muted mb-3" />
          <div className="h-3 w-full rounded bg-muted/50" />
          <div className="h-3 w-5/6 rounded bg-muted/50" />
          <div className="h-3 w-4/6 rounded bg-muted/50" />
        </div>

        {/* Exercise skeletons */}
        <div className="space-y-px border border-border rounded overflow-hidden">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className={`bg-card p-5 animate-pulse ${i !== 1 ? "border-t border-border" : ""}`}
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-baseline gap-3">
                  <div className="h-3 w-5 rounded bg-muted/40" />
                  <div className="h-4 w-36 rounded bg-muted" />
                </div>
                <div className="h-5 w-20 rounded bg-muted/60" />
              </div>

              <div className="flex gap-6 mb-4">
                {[1, 2, 3].map((j) => (
                  <div key={j}>
                    <div className="h-2 w-16 rounded bg-muted/40 mb-1.5" />
                    <div className="h-4 w-20 rounded bg-muted/60" />
                  </div>
                ))}
              </div>

              <div className="space-y-1.5">
                <div className="h-2 w-24 rounded bg-muted/40" />
                <div className="h-3 w-full rounded bg-muted/40" />
                <div className="h-3 w-5/6 rounded bg-muted/40" />
              </div>
            </div>
          ))}
        </div>

      </div>
    </main>
  );
}
