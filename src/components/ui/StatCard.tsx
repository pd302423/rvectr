"use client";

import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  subtext?: string;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  status?: "nominal" | "caution" | "error" | "neutral";
}

export function StatCard({
  label,
  value,
  icon: Icon,
  subtext,
  trend,
  status = "neutral",
}: StatCardProps) {
  const statusStyles = {
    nominal: "border-emerald-500/30 bg-emerald-500/5 text-emerald-700 dark:text-emerald-400",
    caution: "border-amber-500/30 bg-amber-500/5 text-amber-700 dark:text-amber-400",
    error: "border-red-500/30 bg-red-500/5 text-red-700 dark:text-red-400",
    neutral: "border-border bg-card text-foreground",
  };

  return (
    <div className={`p-5 rounded-xl border transition-all hover:border-border/80 ${statusStyles[status]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">{label}</span>
        <div className="p-2 rounded-lg bg-secondary text-secondary-foreground">
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline justify-between">
        <p className="text-2xl font-bold font-sans tracking-tight">{value}</p>
        {trend && (
          <span
            className={`text-xs font-mono px-2 py-0.5 rounded-full ${
              trend.isPositive
                ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400"
                : "bg-red-500/10 text-red-700 dark:text-red-400"
            }`}
          >
            {trend.isPositive ? "↑" : "↓"} {trend.value}
          </span>
        )}
      </div>
      {subtext && <p className="mt-1 text-xs text-muted-foreground font-mono">{subtext}</p>}
    </div>
  );
}
