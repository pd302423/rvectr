interface SectionHeadingProps {
  /** Id of the h2, so the section can point at it with aria-labelledby. */
  id: string;
  eyebrow: string;
  children: React.ReactNode;
}

export function SectionHeading({ id, eyebrow, children }: SectionHeadingProps) {
  return (
    <div className="grid gap-2">
      <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">{eyebrow}</p>
      <h2 id={id} className="font-display text-balance text-3xl leading-[1.12] tracking-tight sm:text-4xl">
        {children}
      </h2>
    </div>
  );
}
