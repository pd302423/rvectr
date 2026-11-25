import { cn } from "@/lib/utils";

interface ContainerProps extends React.ComponentProps<"div"> {
  /** Reading pages stay narrow; tool pages need the full width. */
  size?: "reading" | "default" | "wide";
}

const SIZES = {
  reading: "max-w-3xl",
  default: "max-w-5xl",
  wide: "max-w-7xl",
} as const;

/** Centered column with a 16px minimum side gutter. */
export function Container({ size = "default", className, ...props }: ContainerProps) {
  return <div className={cn("mx-auto w-full px-4 sm:px-6 lg:px-8", SIZES[size], className)} {...props} />;
}
