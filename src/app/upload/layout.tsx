import type { Metadata } from "next";

// The page itself is a client component, so its title is set here.
export const metadata: Metadata = {
  title: "Recording kit",
  description:
    "What to record for the two-phone squat test. Nothing is uploaded; files stay in your browser.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
