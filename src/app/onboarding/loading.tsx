export default function OnboardingLoading() {
  return (
    <main className="min-h-screen bg-background px-6 py-10">
      <div className="mx-auto max-w-2xl space-y-6">

        {/* header skeleton */}
        <div className="mb-10 border-b border-border pb-8">
          <div className="h-2.5 w-24 rounded bg-muted animate-pulse mb-4" />
          <div className="h-8 w-56 rounded bg-muted animate-pulse mb-3" />
          <div className="h-3 w-80 rounded bg-muted/60 animate-pulse" />
        </div>

        {/* section cards */}
        {[
          { rows: 1, pillRows: 0 },  // athlete ID
          { rows: 2, pillRows: 0 },  // schedule
          { rows: 0, pillRows: 2 },  // equipment
          { rows: 0, pillRows: 3 },  // current skills
          { rows: 0, pillRows: 3 },  // goal skills
          { rows: 1, pillRows: 0 },  // contraindications
        ].map((shape, i) => (
          <div key={i} className="rounded border border-border bg-card p-5 space-y-4 animate-pulse">
            {/* card header */}
            <div className="h-4 w-40 rounded bg-muted" />
            <div className="h-2.5 w-64 rounded bg-muted/50" />

            {/* input rows */}
            {Array.from({ length: shape.rows }).map((_, j) => (
              <div key={j} className="h-10 w-full rounded bg-muted/60" />
            ))}

            {/* pill rows */}
            {Array.from({ length: shape.pillRows }).map((_, j) => (
              <div key={j} className="flex flex-wrap gap-2">
                {Array.from({ length: j === 0 ? 5 : j === 1 ? 7 : 4 }).map((_, k) => (
                  <div
                    key={k}
                    className="h-7 rounded-full bg-muted/60"
                    style={{ width: `${56 + (k * 13) % 40}px` }}
                  />
                ))}
              </div>
            ))}
          </div>
        ))}

        {/* submit button skeleton */}
        <div className="flex justify-end">
          <div className="h-11 w-48 rounded bg-muted animate-pulse" />
        </div>
      </div>
    </main>
  );
}
