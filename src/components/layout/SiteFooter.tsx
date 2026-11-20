import { ArrowUpRight } from "lucide-react";
import { Container } from "@/components/site/Container";
import { GITHUB_URL } from "@/lib/site";

/** The one site footer. Rendered once, from the root layout. */
export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-border">
      <Container
        size="wide"
        className="flex flex-col gap-3 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between"
      >
        <p>Rvectr &middot; CBSE Science Exhibition 2026&ndash;27</p>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-10 items-center gap-1 rounded-md text-foreground underline-offset-4 hover:underline"
        >
          GitHub
          <ArrowUpRight aria-hidden="true" className="size-4" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      </Container>
    </footer>
  );
}
