import type { Metadata } from "next";

// The page itself is a client component, so its title is set here.
export const metadata: Metadata = {
  title: "Live demo",
  description:
    "In-browser webcam squat demo for the exhibition stall, using MediaPipe. Separate from the two-phone measurement software.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
