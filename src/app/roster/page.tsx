"use client";

import { useState } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { AthleteRecord } from "@/lib/store";
import { Users, Filter, Download, ShieldAlert, CheckCircle2, AlertTriangle, Search } from "lucide-react";

export default function RosterPage() {
  const [filterPosition, setFilterPosition] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const athletes: AthleteRecord[] = [
    { id: "ath-1", name: "Marcus Vance", position: "Forward", formScore: 94.2, asymmetryIndex: 2.1, status: "optimal", lastAnalysisDate: "2026-07-22" },
    { id: "ath-2", name: "David Miller", position: "Guard", formScore: 78.5, asymmetryIndex: 8.4, status: "caution", lastAnalysisDate: "2026-07-21" },
    { id: "ath-3", name: "Alex Chen", position: "Center", formScore: 62.0, asymmetryIndex: 18.9, status: "high_risk", lastAnalysisDate: "2026-07-20" },
    { id: "ath-4", name: "Jordan Brooks", position: "Midfielder", formScore: 91.0, asymmetryIndex: 3.5, status: "optimal", lastAnalysisDate: "2026-07-23" },
    { id: "ath-5", name: "Elena Rostova", position: "Gymnast", formScore: 96.8, asymmetryIndex: 1.2, status: "optimal", lastAnalysisDate: "2026-07-22" },
    { id: "ath-6", name: "Tyrone Washington", position: "Quarterback", formScore: 71.4, asymmetryIndex: 14.2, status: "caution", lastAnalysisDate: "2026-07-19" },
  ];

  const filteredAthletes = athletes.filter((ath) => {
    const matchesPos = filterPosition === "all" || ath.position.toLowerCase() === filterPosition.toLowerCase();
    const matchesSearch = ath.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesPos && matchesSearch;
  });

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">High Performance Workspace</span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground font-sans mt-1">
              Squad Roster & Movement Readiness
            </h1>
            <p className="text-xs text-muted-foreground font-sans mt-0.5">
              Real-time telemetry roster for Strength Coaches and High-Performance Directors.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs">
              <Download className="h-4 w-4" />
              <span>Export Roster Telemetry</span>
            </button>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="p-4 rounded-xl border border-border bg-card flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search athlete by name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-lg bg-secondary text-xs font-sans border border-border focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
            <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
            {["all", "forward", "guard", "center", "midfielder", "quarterback"].map((pos) => (
              <button
                key={pos}
                onClick={() => setFilterPosition(pos)}
                className={`px-3 py-1.5 rounded-md text-xs font-mono capitalize transition-all whitespace-nowrap ${
                  filterPosition === pos
                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                    : "bg-secondary text-secondary-foreground hover:bg-muted"
                }`}
              >
                {pos}
              </button>
            ))}
          </div>
        </div>

        {/* Squad Table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-muted/40 text-muted-foreground font-mono uppercase text-[10px] tracking-wider border-b border-border">
                <tr>
                  <th className="py-3.5 px-4 font-semibold">Athlete Name</th>
                  <th className="py-3.5 px-4 font-semibold">Position</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Form Score</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Asymmetry Index</th>
                  <th className="py-3.5 px-4 font-semibold text-center">Readiness Status</th>
                  <th className="py-3.5 px-4 font-semibold text-right">Last Analysis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredAthletes.map((ath) => (
                  <tr key={ath.id} className="hover:bg-muted/30 transition-colors">
                    <td className="py-3.5 px-4 font-semibold text-foreground flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-primary" />
                      {ath.name}
                    </td>
                    <td className="py-3.5 px-4 text-muted-foreground font-mono">{ath.position}</td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold">{ath.formScore}</td>
                    <td className="py-3.5 px-4 text-right font-mono font-semibold">{ath.asymmetryIndex}%</td>
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] uppercase font-semibold font-mono ${
                          ath.status === "optimal"
                            ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20"
                            : ath.status === "caution"
                            ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20"
                            : "bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20"
                        }`}
                      >
                        {ath.status === "optimal" ? (
                          <CheckCircle2 className="h-3 w-3" />
                        ) : ath.status === "caution" ? (
                          <AlertTriangle className="h-3 w-3" />
                        ) : (
                          <ShieldAlert className="h-3 w-3" />
                        )}
                        {ath.status === "optimal" ? "Optimal" : ath.status === "caution" ? "Monitor Load" : "High Risk"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono text-muted-foreground">{ath.lastAnalysisDate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
