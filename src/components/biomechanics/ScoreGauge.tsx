"use client";

interface ScoreGaugeProps {
  score: number;
  grade: "Excellent" | "Good" | "Fair" | "Poor" | "Critical";
  description?: string;
  size?: number;
}

export function ScoreGauge({
  score,
  grade,
  description,
  size = 180,
}: ScoreGaugeProps) {
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const gradeColors = {
    Excellent: "text-emerald-600 border-emerald-500/20 bg-emerald-500/5",
    Good: "text-blue-600 border-blue-500/20 bg-blue-500/5",
    Fair: "text-amber-600 border-amber-500/20 bg-amber-500/5",
    Poor: "text-orange-600 border-orange-500/20 bg-orange-500/5",
    Critical: "text-red-600 border-red-500/20 bg-red-500/5",
  };

  const strokeColors = {
    Excellent: "#10b981",
    Good: "#3b82f6",
    Fair: "#f59e0b",
    Poor: "#f97316",
    Critical: "#ef4444",
  };

  return (
    <div className="flex flex-col items-center justify-center p-6 rounded-xl border border-border bg-card text-card-foreground">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="transparent"
            className="text-muted/30"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={strokeColors[grade] || "#10b981"}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-4xl font-extrabold font-sans tracking-tight">{score}</span>
          <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Score</span>
        </div>
      </div>

      <div className={`mt-4 px-3 py-1 rounded-full border text-xs font-semibold uppercase tracking-wider ${gradeColors[grade]}`}>
        {grade} Alignment
      </div>

      {description && (
        <p className="mt-3 text-center text-xs text-muted-foreground max-w-xs leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}
