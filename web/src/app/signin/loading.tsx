export default function SignInLoading() {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row bg-background">

      {/* ── Left panel skeleton ── */}
      <div className="relative flex flex-col justify-between overflow-hidden border-b border-border bg-card p-10 lg:w-1/2 lg:border-b-0 lg:border-r animate-pulse">
        <div className="h-7 w-16 rounded bg-muted" />

        <div className="max-w-lg space-y-4">
          <div className="h-2.5 w-40 rounded bg-muted/60" />
          <div className="space-y-2">
            <div className="h-10 w-72 rounded bg-muted" />
            <div className="h-10 w-56 rounded bg-muted" />
            <div className="h-10 w-44 rounded bg-muted" />
          </div>
          {/* Data callouts */}
          <div className="mt-8 grid grid-cols-3 gap-px border border-border bg-border">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-card p-4 space-y-2">
                <div className="h-6 w-10 rounded bg-muted" />
                <div className="h-3 w-16 rounded bg-muted/50" />
              </div>
            ))}
          </div>
        </div>

        <div className="h-2.5 w-32 rounded bg-muted/40" />
      </div>

      {/* ── Right panel skeleton ── */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16 bg-background animate-pulse">
        <div className="w-full max-w-sm space-y-6">
          <div className="h-2.5 w-24 rounded bg-muted/60" />
          <div className="h-9 w-56 rounded bg-muted" />
          <div className="h-3 w-64 rounded bg-muted/50" />

          {/* Mode toggle */}
          <div className="flex gap-6 border-b border-border pb-2">
            <div className="h-3 w-28 rounded bg-muted" />
            <div className="h-3 w-20 rounded bg-muted/50" />
          </div>

          {/* Form fields */}
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="h-2.5 w-24 rounded bg-muted/60" />
              <div className="h-11 w-full rounded bg-muted/40" />
            </div>
            <div className="space-y-1.5">
              <div className="h-2.5 w-16 rounded bg-muted/60" />
              <div className="h-11 w-full rounded bg-muted/40" />
            </div>
            <div className="h-px w-full bg-border mt-6" />
          </div>
        </div>
      </div>

    </div>
  );
}
