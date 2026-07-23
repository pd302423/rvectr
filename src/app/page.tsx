"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { Activity, ShieldCheck, ArrowRight, Video, Cpu, BarChart3, ChevronRight } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden border-b border-border/40 py-20 lg:py-28">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="flex flex-col items-center text-center max-w-3xl mx-auto">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-secondary border border-border text-xs font-mono text-muted-foreground mb-6">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>AI-Powered Precision Motion Capture</span>
              </div>

              <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-foreground font-sans leading-[1.1]">
                Biomechanical Analysis with <span className="underline decoration-primary/40 underline-offset-8">Precision</span>
              </h1>

              <p className="mt-6 text-lg text-muted-foreground leading-relaxed max-w-2xl font-sans">
                Upload any video or stream multi-camera feeds to perform clinical body landmark tracking, joint angle measurement, posture scoring, and movement telemetry.
              </p>

              <div className="mt-8 flex flex-wrap gap-4 justify-center">
                <Link
                  href="/upload"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors shadow-sm"
                >
                  <span>Start Analysis</span>
                  <ArrowRight className="h-4 w-4" />
                </Link>

                <Link
                  href="/demo"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-secondary border border-border text-foreground font-semibold text-sm hover:bg-secondary/80 transition-colors"
                >
                  <Cpu className="h-4 w-4 text-emerald-600" />
                  <span>3-Cam Command Center</span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Feature Cards Grid */}
        <section className="py-16 bg-muted/20">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <span className="text-xs font-mono uppercase tracking-widest text-muted-foreground">Capabilities</span>
              <h2 className="text-2xl font-bold tracking-tight text-foreground mt-1">
                Clinical Precision Engineering
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  icon: Activity,
                  title: "3D Landmark Estimation",
                  desc: "33-point skeletal landmark recovery using GPU acceleration for precise joint tracking.",
                },
                {
                  icon: BarChart3,
                  title: "Kinematic Joint Telemetry",
                  desc: "Real-time vector angle calculations, range of motion bounds, and stability index scoring.",
                },
                {
                  icon: Cpu,
                  title: "Multi-Camera Triangulation",
                  desc: "Synchronize 3 camera feeds via audio clap peak detection to eliminate depth occlusion.",
                },
              ].map((feat, idx) => {
                const Icon = feat.icon;
                return (
                  <div
                    key={idx}
                    className="p-6 rounded-xl border border-border bg-card hover:border-border/80 transition-all shadow-xs flex flex-col justify-between"
                  >
                    <div>
                      <div className="p-3 rounded-lg bg-secondary text-secondary-foreground w-fit mb-4">
                        <Icon className="h-6 w-6" />
                      </div>
                      <h3 className="text-lg font-bold tracking-tight text-card-foreground">{feat.title}</h3>
                      <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{feat.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
