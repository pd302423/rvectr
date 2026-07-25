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
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center p-6 border border-[#262626] bg-[#0a0a0a] text-[#ffffff] font-mono">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#262626"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#ffffff"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="square"
            fill="transparent"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className="text-4xl font-bold font-sans tracking-tight text-[#ffffff]">{score}</span>
          <span className="text-[10px] font-mono uppercase tracking-widest text-[#a3a3a3]">SCORE / 100</span>
        </div>
      </div>

      <div className="mt-4 px-3 py-1 border border-[#ffffff] bg-[#ffffff] text-[#000000] text-xs font-bold uppercase tracking-widest">
        {grade} Form Alignment
      </div>

      {description && (
        <p className="mt-3 text-center text-xs text-[#a3a3a3] max-w-xs leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}
