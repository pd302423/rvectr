"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { Container } from "@/components/site/Container";
import { GITHUB_URL, NAV_LINKS } from "@/lib/site";
import { cn } from "@/lib/utils";

const MOBILE_MENU_ID = "mobile-menu";

/**
 * The one site header. Rendered once, from the root layout.
 * Wide screens: a row of links. Below 768px: a menu button that opens a list.
 */
export function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const closeMenu = () => setOpen(false);

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape" && open) {
      setOpen(false);
      buttonRef.current?.focus();
    }
  };

  const linkClass = (active: boolean) =>
    cn(
      "rounded-md text-muted-foreground transition-colors hover:text-foreground",
      active && "bg-muted text-foreground",
    );

  return (
    <header onKeyDown={onKeyDown} className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur-md">
      <Container size="wide" className="flex h-14 items-center justify-between gap-4">
        <Link href="/" onClick={closeMenu} className="flex items-center gap-2 rounded-md font-display text-2xl leading-none tracking-tight">
          <span aria-hidden="true" className="size-2 rounded-full bg-data" />
          Rvectr
        </Link>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-0.5">
            {NAV_LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(linkClass(active), "block px-2 py-1.5 text-sm")}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
            <li>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-1 flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-sm text-foreground transition-colors hover:bg-muted"
              >
                GitHub
                <ArrowUpRight aria-hidden="true" className="size-3.5" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </li>
          </ul>
        </nav>

        <button
          ref={buttonRef}
          type="button"
          aria-expanded={open}
          aria-controls={MOBILE_MENU_ID}
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((value) => !value)}
          className="-mr-2 inline-flex size-11 items-center justify-center rounded-md text-foreground hover:bg-muted md:hidden"
        >
          {open ? <X aria-hidden="true" className="size-6" /> : <Menu aria-hidden="true" className="size-6" />}
        </button>
      </Container>

      <nav id={MOBILE_MENU_ID} aria-label="Main" hidden={!open} className="border-t border-border md:hidden">
        <Container size="wide" className="py-3">
          <ul className="grid gap-1">
            {NAV_LINKS.map((link) => {
              const active = pathname === link.href;
              return (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    onClick={closeMenu}
                    aria-current={active ? "page" : undefined}
                    className={cn(linkClass(active), "flex min-h-11 items-center px-3 text-base")}
                  >
                    {link.label}
                  </Link>
                </li>
              );
            })}
            <li>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                onClick={closeMenu}
                className="flex min-h-11 items-center gap-1.5 rounded-md px-3 text-base text-muted-foreground transition-colors hover:text-foreground"
              >
                GitHub
                <ArrowUpRight aria-hidden="true" className="size-4" />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </li>
          </ul>
        </Container>
      </nav>
    </header>
  );
}
