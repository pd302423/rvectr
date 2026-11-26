import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { HeadlineStats } from "@/components/results/HeadlineStats";
import { Container } from "@/components/site/Container";
import { SectionHeading } from "@/components/site/SectionHeading";
import { TriangulationDiagram } from "@/components/site/TriangulationDiagram";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: { absolute: "Rvectr · Squat depth from phone cameras" },
  description:
    "Do a second and a third phone make a 3D movement measurement more accurate? Rvectr is a student research project that tests this on one number: how deep a squat goes.",
};

const STATUS = [
  { label: "Software built", detail: "ready for pilot validation", dot: "bg-data" },
  { label: "Tested on simulated data", detail: "no real footage yet", dot: "bg-warm" },
  { label: "Pilot recording next", detail: "", dot: "border border-muted-foreground" },
] as const;

const STEPS = [
  {
    title: "Film from two or three angles",
    body: "Two (or three) ordinary phones stand on tripods and film the same squats at the same time.",
  },
  {
    title: "Calibrate with a checkerboard",
    body: "A printed checkerboard is shown to every phone. From it the software learns each phone's lens and where each phone stands.",
  },
  {
    title: "Line up the clocks with two torch flashes",
    body: "A flash near the start and another near the end of each take are seen by every phone. The software uses the two flash times to line up the phones' clocks and to check whether the clocks drift apart during the take.",
  },
  {
    title: "Find the hips and combine them",
    body: "A pose model (RTMPose, a program that finds body joints in a picture) marks the hips in every frame. Triangulation then joins the views: it finds where the lines of sight from each phone cross, which gives one 3D position.",
  },
  {
    title: "Measure depth and label each squat",
    body: "Pelvis height over time gives each squat's depth. Squats are compared with the explicitly selected reference repetition from the same take and labelled “reached reference”, “shallower” or “unclear”. A short gap between two real observations may be bridged; a longer gap, or a joint that was never seen, stays missing.",
  },
] as const;

const LIMITS = [
  {
    lead: "No real footage yet.",
    body: "No real two-phone video has been recorded. The results page uses computer-simulation output; the webcam demo and sample analysis use generated or live demo data and are not research measurements.",
  },
  {
    lead: "The results depend on the assumed settings.",
    body: "The simulation includes slow drift in the hip positions, error shared by the cameras and timing offsets between phones. It does not show how often these happen in real phone footage.",
  },
  {
    lead: "One camera leaves depth ambiguous.",
    body: "In this simulation, a front-oblique camera underestimated depth when the pelvis moved away from it during the squat. That result depends on the simulated camera placement and path; extra views still depend on good calibration and timing.",
  },
] as const;

const TRY_IT = [
  {
    href: "/test/squat",
    tag: "Webcam demo",
    title: "Live demo",
    body: "Stand in front of a webcam and see a pose model draw a skeleton on you and count squats. Made for the exhibition stall. It runs in the browser with MediaPipe and is separate from the two-phone measurement software.",
  },
  {
    href: "/demo",
    tag: "Sample model",
    title: "3D viewer",
    body: "Rotate and zoom a 3D body model. It is a sample model, not a measurement of anyone.",
  },
  {
    href: "/analysis",
    tag: "Synthetic data",
    title: "Sample analysis",
    body: "A mock-up of a result page. Every number on it is a placeholder, not output from the software.",
  },
] as const;

const BUTTON =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-5 text-sm font-medium transition-colors";

export default function Home() {
  return (
    <>
      {/* Hero */}
      <section aria-labelledby="hero-title" className="border-b border-border">
        <Container className="grid items-center gap-12 py-14 sm:py-20 lg:grid-cols-[1.25fr_1fr] lg:gap-16">
          <div className="grid gap-7">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">
              CBSE Science Exhibition 2026&ndash;27 &middot; AI for Better Life
            </p>
            <h1
              id="hero-title"
              className="font-display text-balance text-5xl leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl"
            >
              Can ordinary phones measure how deep a squat is?
            </h1>
            <div className="grid max-w-[65ch] gap-4 text-lg leading-relaxed text-muted-foreground">
              <p>
                Rvectr tests how camera count and movement pace affect simulated squat-depth estimates, and whether
                the added setup is useful enough to justify the effort.
              </p>
              <p>The test is one number: how deep a squat goes.</p>
            </div>

            <ul
              aria-label="Project status"
              className="grid gap-x-6 gap-y-3 rounded-lg border border-border bg-card px-4 py-4 text-sm sm:flex sm:flex-wrap sm:px-5"
            >
              {STATUS.map((item) => (
                <li key={item.label} className="flex items-center gap-2.5">
                  <span aria-hidden="true" className={cn("size-2.5 shrink-0 rounded-full", item.dot)} />
                  <span>
                    {item.label}
                    {item.detail ? <span className="text-muted-foreground"> ({item.detail})</span> : null}
                  </span>
                </li>
              ))}
            </ul>

            <div className="flex flex-wrap gap-3">
              <Link href="/results" className={cn(BUTTON, "bg-foreground text-background hover:bg-foreground/85")}>
                See the simulated results
                <ArrowRight aria-hidden="true" className="size-4" />
              </Link>
              <a href="#how-it-works" className={cn(BUTTON, "border border-border hover:bg-muted")}>
                How it works
              </a>
            </div>
          </div>

          <figure className="m-0 grid gap-3 rounded-lg border border-border bg-card p-5">
            <TriangulationDiagram />
            <figcaption className="text-sm leading-relaxed text-muted-foreground">
              Two phones see the same hip from different angles. Where their lines of sight cross is the hip&apos;s 3D
              position. A drawing of the idea, not data.
            </figcaption>
          </figure>
        </Container>
      </section>

      {/* How it works */}
      <section id="how-it-works" aria-labelledby="how-title" className="border-b border-border">
        <Container className="grid gap-10 py-16 sm:py-20">
          <SectionHeading id="how-title" eyebrow="How it works">
            Five steps from phone video to squat depth
          </SectionHeading>
          <ol className="grid">
            {STEPS.map((step, i) => (
              <li
                key={step.title}
                className="grid gap-x-8 gap-y-2 border-t border-border py-6 sm:grid-cols-[4rem_minmax(0,16rem)_minmax(0,1fr)] lg:grid-cols-[4rem_minmax(0,20rem)_minmax(0,1fr)]"
              >
                <span aria-hidden="true" className="font-mono text-sm tabular-nums text-data">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="text-lg font-medium leading-snug">
                  {step.title}
                </h3>
                <p className="max-w-[65ch] leading-relaxed text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </Container>
      </section>

      {/* Headline numbers */}
      <section aria-labelledby="numbers-title" className="border-b border-border">
        <Container className="grid gap-8 py-16 sm:py-20">
          <SectionHeading id="numbers-title" eyebrow="Simulated results">
            How small a change can it catch?
          </SectionHeading>
          <p className="max-w-[65ch] text-lg leading-relaxed text-muted-foreground">
            In this computer simulation, the smallest depth change that met both limits depended on the number of
            cameras, the amount of random noise and the squat pace. The simulation picks its cutoff using half of the
            computer-made sessions and checks it once on the other half. Each card says whether that check passed, with
            the counts. Real recordings have not tested whether the pattern holds.
          </p>
          <HeadlineStats variant="home" />
          <p>
            <Link
              href="/results"
              className="inline-flex min-h-11 items-center gap-2 text-sm font-medium text-data underline-offset-4 hover:underline"
            >
              All results, charts and caveats
              <ArrowRight aria-hidden="true" className="size-4" />
            </Link>
          </p>
        </Container>
      </section>

      {/* What we can't claim */}
      <section aria-labelledby="limits-title" className="border-b border-border">
        <Container className="grid gap-8 py-16 sm:py-20">
          <SectionHeading id="limits-title" eyebrow="Honest limits">
            What we can&apos;t claim yet
          </SectionHeading>
          <ul className="grid gap-4 md:grid-cols-3">
            {LIMITS.map((item) => (
              <li key={item.lead} className="grid content-start gap-2 rounded-lg border border-warm/40 bg-warm/5 p-5">
                <p className="font-medium text-warm">{item.lead}</p>
                <p className="text-sm leading-relaxed text-foreground/85">{item.body}</p>
              </li>
            ))}
          </ul>
        </Container>
      </section>

      {/* Try it */}
      <section aria-labelledby="try-title">
        <Container className="grid gap-8 py-16 sm:py-20">
          <SectionHeading id="try-title" eyebrow="Try it">
            Three things to click on
          </SectionHeading>
          <ul className="grid gap-4 md:grid-cols-3">
            {TRY_IT.map((card) => (
              <li key={card.href} className="grid">
                <Link
                  href={card.href}
                  className="group grid content-start gap-3 rounded-lg border border-border bg-card p-5 transition-colors hover:border-foreground/50"
                >
                  <span className="w-fit rounded-full border border-border px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                    {card.tag}
                  </span>
                  <span className="flex items-center justify-between gap-3 text-xl font-medium">
                    {card.title}
                    <ArrowRight
                      aria-hidden="true"
                      className="size-5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground"
                    />
                  </span>
                  <span className="text-sm leading-relaxed text-muted-foreground">{card.body}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Container>
      </section>
    </>
  );
}
