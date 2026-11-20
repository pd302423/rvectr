import type { Metadata } from "next";

// The page itself is a client component, so its title is set here.
export const metadata: Metadata = {
  title: "Sample analysis",
  description:
    "A mock-up of a Rvectr result page. Every number on it is a synthetic placeholder, not a measurement.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
