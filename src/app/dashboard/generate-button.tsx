"use client";

import { useFormStatus } from "react-dom";

type Props = {
  focusLabel: string;
};

export function GenerateButton({ focusLabel }: Props) {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="inline-flex items-center gap-2 rounded bg-foreground px-6 py-3 font-mono text-sm text-background hover:opacity-90 disabled:opacity-50 transition-opacity"
    >
      {pending ? (
        <>
          <span className="inline-block h-3 w-3 rounded-full border-2 border-background/40 border-t-background animate-spin" />
          Generating session…
        </>
      ) : (
        <>Generate {focusLabel} session →</>
      )}
    </button>
  );
}
