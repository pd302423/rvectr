"use client";

import { AlertTriangle, CheckCircle2, ShieldAlert, Scale } from "lucide-react";

interface AsymmetryItem {
  parameter: string;
  leftValue: number;
  rightValue: number;
  unit: string;
}

export function BilateralAsymmetryMatrix() {
  const items: AsymmetryItem[] = [
    { parameter: "Knee Flexion (Peak Depth)", leftValue: 92.4, rightValue: 91.8, unit: "°" },
    { parameter: "Hip Flexion (Bottom Phase)", leftValue: 104.2, rightValue: 95.8, unit: "°" },
    { parameter: "Ground Contact Time (GCT)", leftValue: 340, rightValue: 310, unit: "ms" },
    { parameter: "Ankle Dorsiflexion Range", leftValue: 32.1, rightValue: 28.5, unit: "°" },
  ];

  const calculateBSI = (left: number, right: number) => {
    const avg = (left + right) / 2;
    if (avg === 0) return 0;
    return Number(((Math.abs(left - right) / avg) * 100).toFixed(1));
  };

  return (
    <div className="p-6 rounded-xl border border-border bg-card shadow-xs space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-2">
          <Scale className="h-5 w-5 text-primary" />
          <div>
            <h3 className="text-base font-bold tracking-tight text-foreground font-sans">
              Bilateral Asymmetry & Injury Risk Matrix
            </h3>
            <p className="text-xs text-muted-foreground font-mono">
              Left vs. Right Limb Comparative Kinematics & Strain Risk Assessment
            </p>
          </div>
        </div>

        {/* Global Symmetry Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400 font-mono text-xs w-fit">
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          <span>Overall Asymmetry: 3.2% (🟢 Nominal)</span>
        </div>
      </div>

      {/* Asymmetry Telemetry Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-sans">
          <thead className="bg-muted/40 text-muted-foreground font-mono uppercase text-[10px] tracking-wider border-b border-border">
            <tr>
              <th className="py-3 px-4 font-semibold">Parameter</th>
              <th className="py-3 px-4 font-semibold text-right">Left Limb</th>
              <th className="py-3 px-4 font-semibold text-right">Right Limb</th>
              <th className="py-3 px-4 font-semibold text-right">BSI Asymmetry (%)</th>
              <th className="py-3 px-4 font-semibold text-center">Risk Zone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item, idx) => {
              const bsi = calculateBSI(item.leftValue, item.rightValue);
              const isNominal = bsi < 5;
              const isModerate = bsi >= 5 && bsi <= 15;

              return (
                <tr key={idx} className="hover:bg-muted/30 transition-colors font-mono">
                  <td className="py-3 px-4 font-sans font-medium text-foreground">{item.parameter}</td>
                  <td className="py-3 px-4 text-right">{item.leftValue} {item.unit}</td>
                  <td className="py-3 px-4 text-right">{item.rightValue} {item.unit}</td>
                  <td className="py-3 px-4 text-right font-bold">{bsi}%</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] uppercase font-semibold ${
                        isNominal
                          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                          : isModerate
                          ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20"
                          : "bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20"
                      }`}
                    >
                      {isNominal ? "🟢 Nominal (<5%)" : isModerate ? "🟡 Moderate (5-15%)" : "🔴 High Risk (>15%)"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Clinical Guidance Box */}
      <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/20 text-amber-950 dark:text-amber-300 text-xs font-sans space-y-1">
        <div className="flex items-center gap-2 font-semibold text-amber-700 dark:text-amber-400">
          <AlertTriangle className="h-4 w-4" />
          <span>Strength & Conditioning Diagnostic Alert</span>
        </div>
        <p className="text-amber-800 dark:text-amber-300/90 leading-relaxed">
          Moderate asymmetry (8.4%) detected in hip flexion angle. Right hip displays reduced ROM at peak depth. Recommend unilateral hip mobility exercises and single-leg load monitoring.
        </p>
      </div>
    </div>
  );
}
