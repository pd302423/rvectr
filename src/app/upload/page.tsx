"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Grid3x3, Camera, UploadCloud } from "lucide-react";
import { Container } from "@/components/site/Container";
import { Notice } from "@/components/site/Notice";
import { PageHeader } from "@/components/site/PageHeader";
import { SectionHeading } from "@/components/site/SectionHeading";
import { GITHUB_URL } from "@/lib/site";

type SlotId = "calib" | "cam1" | "cam2";
type SetupMode = "multiview" | "monocular";

interface VideoSlot {
  id: SlotId;
  title: string;
  role: string;
  description: string;
  icon: typeof Camera;
  file: File | null;
  required: boolean;
}

const KIT_LIST = [
  "Two phones on stable supports for the one-versus-two comparison; a third phone is optional",
  "A flat, measured checkerboard with a physical mark beside the same corner for every camera",
  "A torch visible to all cameras at the start and end of the take",
  "A stick of known length for the five-position geometry check",
  "A stable stool with measured height settings, chosen with the supervisor",
  "A floor marker, a visible pelvis marker, a measured vertical scale and a notebook",
] as const;

const NEXT_STEPS = [
  "Calibrate each lens and each camera position. Compare the corner overlays with the marks on the same board, then check the stick at five positions.",
  "Use both torch flashes to align the videos and check drift. RTMPose estimates hip locations in the usable frames.",
  "Reconstruct the hip midpoint, then compare the estimated displacement with the independent scale reading. Use the same annotation IDs and baseline for every camera combination.",
] as const;

export default function UploadPage() {
  const [mode, setMode] = useState<SetupMode>("multiview");

  const [calibFile, setCalibFile] = useState<File | null>(null);
  const [cam1File, setCam1File] = useState<File | null>(null);
  const [cam2File, setCam2File] = useState<File | null>(null);

  const calibInputRef = useRef<HTMLInputElement>(null);
  const cam1InputRef = useRef<HTMLInputElement>(null);
  const cam2InputRef = useRef<HTMLInputElement>(null);

  const slots: VideoSlot[] = [
    {
      id: "calib",
      title: "1. Example board clip",
      role: "Lens and phone positions",
      description:
        "Keep a varied lens-calibration clip for each phone and a shared still-board clip from every view. This slot previews one of those files.",
      icon: Grid3x3,
      file: calibFile,
      required: mode === "multiview",
    },
    {
      id: "cam1",
      title: "2. Phone 1 squat video",
      role: "First view",
      description: "One continuous take containing the designated baseline and the test attempts.",
      icon: Camera,
      file: cam1File,
      required: true,
    },
    {
      id: "cam2",
      title: "3. Phone 2 squat video",
      role: "Second view",
      description: "The same attempts filmed by phone 2, with the same start and end flashes.",
      icon: Camera,
      file: cam2File,
      required: mode === "multiview",
    },
  ];

  const inputRefs = { calib: calibInputRef, cam1: cam1InputRef, cam2: cam2InputRef };
  const setters = { calib: setCalibFile, cam1: setCam1File, cam2: setCam2File };

  const handleFileSelect = (slotId: SlotId, e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) setters[slotId](selected);
  };

  const visibleSlots = slots.filter((s) => mode === "multiview" || s.id === "cam1");
  const chosen = visibleSlots.filter((s) => s.file);
  const totalMb = chosen.reduce((sum, s) => sum + (s.file ? s.file.size : 0), 0) / (1024 * 1024);

  return (
    <Container className="grid gap-10 py-10 sm:py-14">
      <PageHeader eyebrow="Recording kit" title="What to record for the two-phone squat test">
        <p>
          A short guide to what you need and what to film, with a place to line up your video files before you take
          them to the laptop.
        </p>
      </PageHeader>

      <Notice tone="info" title="Nothing is uploaded or processed online.">
        <p>
          Files you choose here stay in your browser. They are not sent anywhere. Processing runs on a laptop with the
          Python <code className="font-mono text-foreground">rvectr</code> software. The step-by-step filming list is
          in <code className="font-mono text-foreground">docs/PILOT_RECORDING_CHECKLIST.md</code> in the{" "}
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground underline underline-offset-4"
          >
            GitHub repository
          </a>
          .
        </p>
      </Notice>

      <section aria-labelledby="kit-title" className="grid gap-5">
        <SectionHeading id="kit-title" eyebrow="Before you film">
          What you need
        </SectionHeading>
        <ul className="grid max-w-[65ch] list-disc gap-2 pl-5 leading-relaxed text-muted-foreground marker:text-data">
          {KIT_LIST.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="max-w-[65ch] text-sm leading-relaxed text-muted-foreground">
          Keep the marker and vertical scale in the same plane. Before opening any software result, record standing and bottom readings, timing and reader uncertainty for each attempt.
        </p>
      </section>

      <section aria-labelledby="files-title" className="grid gap-5">
        <SectionHeading id="files-title" eyebrow="Your files">
          Preview local clips
        </SectionHeading>

        <div role="group" aria-label="Clips to preview" className="flex flex-wrap gap-2">
          {(
            [
              { id: "multiview", label: "Two-phone take" },
              { id: "monocular", label: "Preview one clip" },
            ] as const
          ).map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={mode === option.id}
              onClick={() => setMode(option.id)}
              className="min-h-10 rounded-full border border-border px-4 text-sm transition-colors hover:bg-muted aria-pressed:border-foreground aria-pressed:bg-foreground aria-pressed:text-background"
            >
              {option.label}
            </button>
          ))}
        </div>

        <p className="max-w-[65ch] text-sm text-muted-foreground">
          Run the pilot from a synchronized take with at least two phones. You can preview a single file here.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {visibleSlots.map((slot) => {
            const Icon = slot.icon;
            const inputRef = inputRefs[slot.id];
            return (
              <div
                key={slot.id}
                className={`flex min-w-0 flex-col justify-between rounded-lg border p-5 transition-colors ${
                  slot.file ? "border-data/50 bg-data/5" : "border-border bg-card"
                }`}
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept=".mp4,.avi,.mov,.mkv,.webm"
                  onChange={(e) => handleFileSelect(slot.id, e)}
                  className="hidden"
                  tabIndex={-1}
                />

                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <div className="rounded-md border border-border bg-background p-2 text-foreground">
                      <Icon aria-hidden="true" className="h-5 w-5" />
                    </div>
                    {slot.file ? (
                      <span className="flex items-center gap-1 font-mono text-[11px] text-data">
                        <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5" /> Chosen
                      </span>
                    ) : (
                      <span className="font-mono text-[10px] uppercase text-muted-foreground">
                        {slot.required ? "Required" : "Optional"}
                      </span>
                    )}
                  </div>

                  <h3 className="mb-1 text-sm font-semibold">{slot.title}</h3>
                  <p className="mb-3 font-mono text-[11px] text-muted-foreground">{slot.role}</p>
                  <p className="mb-4 text-sm leading-relaxed text-muted-foreground">{slot.description}</p>
                </div>

                <div>
                  {slot.file ? (
                    <div className="mb-3 rounded-sm border border-border bg-background/80 p-2.5 font-mono text-xs">
                      <p className="truncate font-semibold text-foreground">{slot.file.name}</p>
                      <p className="mt-0.5 text-[10px] text-muted-foreground">
                        {(slot.file.size / (1024 * 1024)).toFixed(2)} MB &middot; {slot.file.type || "video"}
                      </p>
                    </div>
                  ) : null}

                  <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="flex min-h-10 w-full items-center justify-center gap-2 border border-border px-3 text-xs uppercase tracking-wider transition-colors hover:bg-foreground hover:text-background"
                  >
                    <UploadCloud aria-hidden="true" className="h-3.5 w-3.5" />
                    <span>{slot.file ? "Replace file" : "Choose video"}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <p aria-live="polite" className="font-mono text-sm text-muted-foreground">
          {chosen.length === 0
            ? "No files chosen yet."
            : `${chosen.length} of ${visibleSlots.length} chosen (${totalMb.toFixed(1)} MB). Kept in this browser only.`}
        </p>
      </section>

      <section aria-labelledby="next-title" className="grid gap-5 rounded-lg border border-border bg-card p-5 sm:p-6">
        <SectionHeading id="next-title" eyebrow="Then, on a laptop">
          What the software does with them
        </SectionHeading>
        <ol className="grid max-w-[65ch] list-decimal gap-2 pl-5 leading-relaxed text-muted-foreground marker:font-mono marker:text-data">
          {NEXT_STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <p>
          <Link
            href="/analysis"
            className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-data underline-offset-4 hover:underline"
          >
            See a mock-up of a result page (sample data)
            <ArrowRight aria-hidden="true" className="size-4" />
          </Link>
        </p>
      </section>
    </Container>
  );
}
