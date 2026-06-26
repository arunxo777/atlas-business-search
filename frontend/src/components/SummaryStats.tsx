import type { ResearchJob } from "@/api/client";
import { cn } from "@/lib/utils";
import {
  Building2,
  CheckCircle,
  Copy,
  Globe,
  Timer,
} from "lucide-react";

interface SummaryStatsProps {
  job: ResearchJob | null;
  elapsedSeconds?: number;
}

export function SummaryStats({ job, elapsedSeconds }: SummaryStatsProps) {
  const stats = [
    {
      label: "Found",
      value: job?.businesses_found ?? 0,
      icon: Building2,
      color: "text-violet-400",
      bg: "from-violet-500/10 to-transparent",
    },
    {
      label: "Verified",
      value: job?.businesses_verified ?? 0,
      icon: CheckCircle,
      color: "text-emerald-400",
      bg: "from-emerald-500/10 to-transparent",
    },
    {
      label: "Dupes Removed",
      value: job?.duplicates_removed ?? 0,
      icon: Copy,
      color: "text-amber-400",
      bg: "from-amber-500/10 to-transparent",
    },
    {
      label: "Sources",
      value: job?.sources_searched ?? 0,
      icon: Globe,
      color: "text-cyan-400",
      bg: "from-cyan-500/10 to-transparent",
    },
    {
      label: "Elapsed",
      value: elapsedSeconds != null ? `${Math.round(elapsedSeconds)}s` : "—",
      icon: Timer,
      color: "text-fuchsia-400",
      bg: "from-fuchsia-500/10 to-transparent",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {stats.map((stat) => (
        <div key={stat.label} className="stat-card relative overflow-hidden">
          <div
            className={cn(
              "absolute inset-0 bg-gradient-to-br opacity-50",
              stat.bg
            )}
          />
          <div className="relative">
            <div className="flex items-center gap-2 text-muted-foreground text-xs mb-2">
              <stat.icon className={cn("h-3.5 w-3.5", stat.color)} />
              {stat.label}
            </div>
            <div className="text-2xl font-bold font-mono tracking-tight">
              {stat.value}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
