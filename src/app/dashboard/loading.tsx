export default function DashboardLoading() {
  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-4xl">

        {/* ── Header skeleton ── */}
        <header className="mb-12 flex items-start justify-between border-b border-border pb-8 animate-pulse">
          <div>
            <div className="h-2.5 w-24 rounded bg-muted mb-4" />
            <div className="h-9 w-44 rounded bg-muted mb-3" />
            <div className="flex gap-2">
              <div className="h-5 w-28 rounded bg-muted/60" />
              <div className="h-5 w-36 rounded bg-muted/40" />
            </div>
          </div>
          <div className="h-3 w-12 rounded bg-muted/40" />
        </header>

        {/* ── Assessment CTA skeleton ── */}
        <div className="mb-8 rounded border border-border bg-card p-6 animate-pulse">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <div className="h-2.5 w-28 rounded bg-muted/60" />
              <div className="h-5 w-56 rounded bg-muted" />
              <div className="h-3 w-80 rounded bg-muted/40" />
            </div>
            <div className="h-11 w-44 rounded bg-muted shrink-0" />
          </div>
        </div>

        {/* ── Data grid skeleton ── */}
        <div className="grid grid-cols-1 gap-px border border-border sm:grid-cols-2 animate-pulse">
          {[
            { pills: 5 },
            { pills: 3 },
            { pills: 4 },
            { lines: 3 },
          ].map((shape, i) => (
            <div key={i} className="bg-card p-5">
              <div className="h-2.5 w-32 rounded bg-muted/60 mb-4" />
              {"pills" in shape ? (
                <div className="flex flex-wrap gap-1.5">
                  {Array.from({ length: shape.pills as number }).map((_, j) => (
                    <div
                      key={j}
                      className="h-6 rounded bg-muted/50"
                      style={{ width: `${52 + (j * 17) % 36}px` }}
                    />
                  ))}
                </div>
              ) : (
                <div className="space-y-1.5">
                  {Array.from({ length: shape.lines as number }).map((_, j) => (
                    <div
                      key={j}
                      className="h-3 rounded bg-muted/40"
                      style={{ width: `${60 + (j * 15) % 35}%` }}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

      </div>
    </main>
  );
}
