"use client";

import Link from "next/link";
import { Navbar } from "@/components/layout/Navbar";
import { useBiomechanicsStore, isSampleAnalysis } from "@/lib/store";
import { DualViewport } from "@/components/biomechanics/DualViewport";
import { ScoreGauge } from "@/components/biomechanics/ScoreGauge";
import { TelemetryTable } from "@/components/biomechanics/TelemetryTable";
import { TimelineScrubber } from "@/components/biomechanics/TimelineScrubber";
import { KinematicWaveformChart } from "@/components/biomechanics/KinematicWaveformChart";
import { BilateralAsymmetryMatrix } from "@/components/biomechanics/BilateralAsymmetryMatrix";
import { Activity, Award, Lightbulb, FileText, Upload, RefreshCw, Scale, LineChart, ShieldCheck } from "lucide-react";

export default function AnalysisPage() {
  const { currentAnalysis, activeTab, setActiveTab } = useBiomechanicsStore();

  if (!currentAnalysis) return null;

  const { analysis, metadata, video_id } = currentAnalysis;

  const tabs = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "joints", label: "Joint Telemetry", icon: Award },
    { id: "waveform", label: "Waveform Studio", icon: LineChart },
    { id: "asymmetry", label: "Bilateral Asymmetry", icon: Scale },
    { id: "posture", label: "Posture Diagnostic", icon: FileText },
    { id: "recommendations", label: "Recommendations", icon: Lightbulb },
  ] as const;

  return (
    <div className="min-h-screen bg-[#000000] text-[#ffffff] font-sans flex flex-col selection:bg-[#ffffff] selection:text-[#000000]">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6 font-mono">

        {isSampleAnalysis(currentAnalysis) && (
          <div
            role="status"
            className="border border-amber-500/60 bg-amber-500/10 text-amber-200 px-4 py-3 text-xs leading-relaxed"
          >
            <strong className="uppercase tracking-widest">Sample data — not a measurement.</strong>{" "}
            Nothing has been analysed. Every number on this page is a synthetic
            placeholder generated from a sine wave, shown so the interface can be
            laid out. It is not the output of any capture pipeline and must not be
            cited or screenshotted as a result.
          </div>
        )}

        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#262626] pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-[#a3a3a3]">
              <span className="uppercase tracking-widest font-bold">SESSION ID</span>
              <span className="bg-[#121212] px-2 py-0.5 border border-[#262626] text-[#ffffff] font-bold">{video_id}</span>
              <span className="px-2 py-0.5 border border-[#ffffff] bg-[#ffffff] text-[#000000] font-bold uppercase tracking-widest text-[10px]">
                Professional MoCap Mode
              </span>
            </div>
            <h1 className="text-xl font-bold tracking-widest uppercase text-[#ffffff] font-sans mt-2">
              Biomechanical Kinematic Telemetry Workspace
            </h1>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/demo"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 border border-[#ffffff] bg-[#ffffff] text-[#000000] hover:bg-[#a3a3a3] text-xs font-mono font-bold uppercase tracking-widest transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>3D Motion Command</span>
            </Link>
          </div>
        </div>

        {/* Dual Viewport (EasyMocap 3D Surface Mesh) */}
        <DualViewport />

        {/* Timeline Scrubber */}
        <TimelineScrubber totalFrames={metadata?.total_frames || 291} fps={metadata?.fps || 30} />

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-[#262626] pb-2 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
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
                <span>Clinical Posture & Kinematic Diagnostic</span>
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
                <span>Biomechanics & Strength Coaching Recommendations</span>
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

      </main>
    </div>
  );
}
