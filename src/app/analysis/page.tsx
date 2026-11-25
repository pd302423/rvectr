"use client";

import Link from "next/link";
import { Container } from "@/components/site/Container";
import { Notice } from "@/components/site/Notice";
import { PageHeader } from "@/components/site/PageHeader";
import { useBiomechanicsStore, isSampleAnalysis } from "@/lib/store";
import { DualViewport } from "@/components/biomechanics/DualViewport";
import { ScoreGauge } from "@/components/biomechanics/ScoreGauge";
import { TelemetryTable } from "@/components/biomechanics/TelemetryTable";
import { TimelineScrubber } from "@/components/biomechanics/TimelineScrubber";
import { KinematicWaveformChart } from "@/components/biomechanics/KinematicWaveformChart";
import { BilateralAsymmetryMatrix } from "@/components/biomechanics/BilateralAsymmetryMatrix";
import { Activity, Award, Lightbulb, FileText, RefreshCw, Scale, LineChart, ShieldCheck } from "lucide-react";

export default function AnalysisPage() {
  const { currentAnalysis, activeTab, setActiveTab } = useBiomechanicsStore();

  if (!currentAnalysis) return null;

  const { analysis, metadata, video_id } = currentAnalysis;

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "joints", label: "Joint Telemetry", icon: Award },
    { id: "waveform", label: "Waveform Studio", icon: LineChart },
    { id: "asymmetry", label: "Bilateral Asymmetry", icon: Scale },
    { id: "posture", label: "Posture summary", icon: FileText },
    { id: "recommendations", label: "Recommendations", icon: Lightbulb },
  ] as const;

  return (
    <Container size="wide" className="grid grid-cols-[minmax(0,1fr)] gap-6 py-10 sm:py-14">
      <PageHeader eyebrow="Sample analysis" title="A mock-up of a result page">
        <p>
          This shows how a Rvectr result could be laid out: a 3D viewport, a timeline, joint tables and charts. It is
          not a result.
        </p>
      </PageHeader>

      <Notice title="Sample data, not a measurement.">
        <p>
          Every number on this page is a synthetic placeholder, generated from a sine wave, so the layout can be
          shown. Nothing has been analysed and no real recording was used.
          {isSampleAnalysis(currentAnalysis)
            ? " It is not the output of the Rvectr software and must not be cited or screenshotted as a result."
            : ""}
        </p>
      </Notice>

      <div className="flex flex-col justify-between gap-4 border-b border-border pb-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-wrap items-center gap-2 font-mono text-xs text-muted-foreground">
          <span className="font-bold uppercase tracking-widest">Session ID</span>
          <span className="max-w-full break-words border border-border bg-secondary px-2 py-0.5 font-bold text-foreground">
            {video_id}
          </span>
        </div>
        <Link
          href="/demo"
          className="inline-flex min-h-10 w-fit items-center gap-2 border border-border px-3.5 text-sm transition-colors hover:bg-muted"
        >
          <RefreshCw aria-hidden="true" className="h-3.5 w-3.5" />
          <span>Open the 3D viewer</span>
        </Link>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 font-mono">
        {/* Dual Viewport (EasyMocap 3D Surface Mesh) */}
        <DualViewport />

        {/* Timeline Scrubber */}
        <TimelineScrubber totalFrames={metadata?.total_frames || 291} fps={metadata?.fps || 30} />

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-[#262626] pb-2 overflow-x-auto" role="group" aria-label="Sample analysis sections">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-mono font-bold uppercase tracking-widest transition-colors border ${
                  isActive
                    ? "bg-[#ffffff] text-[#000000] border-[#ffffff]"
                    : "bg-[#000000] text-[#a3a3a3] border-[#262626] hover:text-[#ffffff] hover:bg-[#121212]"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Panels */}
        <div className="space-y-6">
          {activeTab === "overview" && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <ScoreGauge
                score={analysis.posture_report.score}
                grade={analysis.posture_report.grade}
                description={analysis.posture_report.description}
              />
              <div className="md:col-span-2">
                <TelemetryTable jointData={analysis.joint_analysis} />
              </div>
            </div>
          )}

          {activeTab === "joints" && (
            <TelemetryTable jointData={analysis.joint_analysis} />
          )}

          {activeTab === "waveform" && (
            <KinematicWaveformChart />
          )}

          {activeTab === "asymmetry" && (
            <BilateralAsymmetryMatrix />
          )}

          {activeTab === "posture" && (
            <div className="p-6 border border-[#262626] bg-[#0a0a0a] space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-widest text-[#ffffff] flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[#ffffff]" />
                <span>Posture summary (sample)</span>
              </h3>
              <p className="text-xs text-[#a3a3a3] leading-relaxed">
                {analysis.posture_report.description}
              </p>
              <div className="grid grid-cols-2 gap-4 text-xs pt-2">
                <div className="p-3 border border-[#262626] bg-[#000000]">
                  <span className="text-[#a3a3a3] block text-[10px] uppercase">Form Score</span>
                  <span className="text-lg font-bold text-[#ffffff]">{analysis.posture_report.score}%</span>
                </div>
                <div className="p-3 border border-[#262626] bg-[#000000]">
                  <span className="text-[#a3a3a3] block text-[10px] uppercase">Movement Consistency</span>
                  <span className="text-lg font-bold text-[#ffffff]">{analysis.posture_report.consistency}%</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === "recommendations" && (
            <div className="p-6 border border-[#262626] bg-[#0a0a0a] space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-widest text-[#ffffff] flex items-center gap-2">
                <Lightbulb className="h-4 w-4 text-[#ffffff]" />
                <span>Recommendations (sample)</span>
              </h3>
              <ul className="space-y-2 text-xs">
                {analysis.recommendations.map((rec, idx) => (
                  <li key={idx} className="p-3 border border-[#262626] bg-[#000000] text-[#ffffff] flex items-center gap-3">
                    <span className="font-bold text-[#a3a3a3]">0{idx + 1}.</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

      </div>
    </Container>
  );
}
