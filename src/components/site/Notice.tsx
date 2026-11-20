import { Info, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

interface NoticeProps {
  /** "caution" = orange (simulation or sample data). "info" = neutral. */
  tone?: "caution" | "info";
  title: string;
  children?: React.ReactNode;
  className?: string;
}

/** A short, honest note at the top of a page. Not a toast: it stays put. */
export function Notice({ tone = "caution", title, children, className }: NoticeProps) {
  const Icon = tone === "caution" ? TriangleAlert : Info;
  return (
    <div
      role="note"
      className={cn(
        "flex gap-3 rounded-xl border p-4 text-sm leading-relaxed sm:p-5",
        tone === "caution" ? "border-warm/50 bg-warm/10" : "border-border bg-card",
        className,
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn("mt-0.5 size-5 shrink-0", tone === "caution" ? "text-warm" : "text-data")}
      />
      <div className="grid min-w-0 gap-1">
        <p className={cn("font-semibold", tone === "caution" ? "text-warm" : "text-foreground")}>{title}</p>
        {children ? <div className="max-w-[65ch] text-foreground/85">{children}</div> : null}
      </div>
    </div>
  );
}
