interface PageHeaderProps {
  eyebrow: string;
  title: string;
  children?: React.ReactNode;
}

/** Top of every page except the home page: label, serif title, one short intro. */
export function PageHeader({ eyebrow, title, children }: PageHeaderProps) {
  return (
    <header className="grid gap-4">
      <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">{eyebrow}</p>
      <h1 className="font-display text-balance text-4xl leading-[1.05] tracking-tight sm:text-5xl">{title}</h1>
      {children ? <div className="max-w-[65ch] text-base leading-relaxed text-muted-foreground">{children}</div> : null}
    </header>
  );
}
