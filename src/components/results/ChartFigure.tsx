import type { ReactNode } from "react";

interface ChartFigureProps {
  /** Shown above the chart (for example the scenario buttons). */
  controls?: ReactNode;
  /** Colour key. */
  legend?: ReactNode;
  /** Plain-words caption. Every chart has one. */
  caption: ReactNode;
  /** Narrowest the chart is drawn; below this it scrolls inside the card. */
  minWidth?: number;
  children: ReactNode;
}

/**
 * Card around a chart. The chart scrolls sideways inside the card on narrow
 * screens, so the page itself never scrolls sideways.
 */
export function ChartFigure({ controls, legend, caption, minWidth = 440, children }: ChartFigureProps) {
  return (
    <figure className="m-0 grid min-w-0 gap-4 rounded-xl border border-border bg-card p-4 sm:p-5">
      {controls}
      <div
        role="group"
        aria-label="Chart. Scrolls sideways on narrow screens."
        tabIndex={0}
        className="overflow-x-auto rounded-md"
      >
        <div style={{ minWidth }}>{children}</div>
      </div>
      {legend}
      <figcaption className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground">{caption}</figcaption>
    </figure>
  );
}

interface LegendItem {
  /** Tailwind background class for the swatch, for example "bg-data". */
  swatch: string;
  label: string;
}

export function ChartLegend({ items }: { items: readonly LegendItem[] }) {
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-2">
          <span aria-hidden="true" className={`inline-block size-3 rounded-[3px] ${item.swatch}`} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
