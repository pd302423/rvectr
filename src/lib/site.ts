/** Shared site facts, so the header, footer and pages never disagree. */

export const GITHUB_URL = "https://github.com/pd302423/rvectr";

export interface NavLink {
  href: string;
  label: string;
}

export const NAV_LINKS: readonly NavLink[] = [
  { href: "/", label: "Home" },
  { href: "/results", label: "Results" },
  { href: "/test/squat", label: "Live demo" },
  { href: "/demo", label: "3D viewer" },
  { href: "/analysis", label: "Sample analysis" },
  { href: "/upload", label: "Recording kit" },
];
