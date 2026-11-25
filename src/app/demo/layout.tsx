import type { Metadata } from "next";

// The page itself is a client component, so its title is set here.
export const metadata: Metadata = {
  title: "3D viewer",
  description:
    "A 3D viewer showing a sample body model. It is not a measurement of anyone.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
