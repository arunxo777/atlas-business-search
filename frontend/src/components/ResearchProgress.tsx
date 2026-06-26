import { useEffect, useRef, useState, useCallback } from "react";
import {
  useSSE,
  type BusinessRecord,
  type ResearchJob,
  type ProgressEvent,
} from "@/api/client";
import { SummaryStats } from "./SummaryStats";
import { cn } from "@/lib/utils";
import {
  Search,
  Globe,
  Sparkles,
  Copy,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

const PHASES = [
  { id: "searching", label: "Search", icon: Search },
  { id: "scraping", label: "Scrape", icon: Globe },
  { id: "enriching", label: "Enrich", icon: Sparkles },
  { id: "deduplicating", label: "Dedup", icon: Copy },
  { id: "verifying", label: "Verify", icon: ShieldCheck },
  { id: "complete", label: "Done", icon: CheckCircle2 },
];

interface ResearchProgressProps {
  jobId: string;
  onBusinessFound?: (business: BusinessRecord) => void;
  onComplete?: (job: ResearchJob) => void;
}

export function ResearchProgress({
  jobId,
  onBusinessFound,
  onComplete,
}: ResearchProgressProps) {
  const [phase, setPhase] = useState("queued");
  const [progressPct, setProgressPct] = useState(0);
  const [message, setMessage] = useState("Initializing research pipeline...");
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startTimeRef = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - startTimeRef.current) / 1000);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handlers = useCallback(
    () => ({
      onProgress: (data: ProgressEvent) => {
        setPhase(data.phase);
        setProgressPct(data.progress_pct);
        setMessage(data.message);
        if (data.phase === "complete") setProgressPct(100);
      },
      onBusiness: (business: BusinessRecord) => {
        onBusinessFound?.(business);
        setJob((prev) =>
          prev
            ? { ...prev, businesses_found: (prev.businesses_found || 0) + 1 }
            : prev
        );
      },
      onSummary: (summary: ResearchJob) => {
        setJob(summary);
        setPhase("complete");
        setProgressPct(100);
        setMessage("Research complete — results ranked and verified.");
        onComplete?.(summary);
      },
      onError: (msg: string) => {
        setError(msg);
        setPhase("failed");
      },
    }),
    [onBusinessFound, onComplete]
  );

  useSSE(jobId, handlers());

  const phaseIndex = PHASES.findIndex((p) => p.id === phase);

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <div className="flex justify-between items-end">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground mb-1">
              Pipeline Status
            </p>
            <p className="text-lg font-semibold capitalize">
              {phase === "failed" ? "Failed" : phase === "queued" ? "Starting..." : phase}
            </p>
          </div>
          <span className="text-3xl font-bold font-mono gradient-text-accent">
            {Math.round(progressPct)}%
          </span>
        </div>

        <div className="progress-bar">
          <div
            className={cn(
              "progress-bar-fill",
              phase === "failed" && "!from-red-500 !to-red-400"
            )}
            style={{ width: `${progressPct}%` }}
          />
        </div>

        <p className="text-sm text-muted-foreground">{message}</p>
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>

      {/* Phase pills with icons */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
        {PHASES.map((p, i) => {
          const done = i < phaseIndex || phase === "complete";
          const active = p.id === phase && phase !== "complete";
          const Icon = p.icon;

          return (
            <div
              key={p.id}
              className={cn(
                "flex flex-col items-center gap-2 rounded-xl px-2 py-3 text-center transition-all duration-300 border",
                done && "phase-pill-done",
                active && "phase-pill-active scale-105",
                !done && !active && "phase-pill-pending"
              )}
            >
              <Icon className={cn("h-4 w-4", active && "animate-pulse")} />
              <span className="text-[10px] font-medium">{p.label}</span>
            </div>
          );
        })}
      </div>

      <SummaryStats job={job} elapsedSeconds={elapsed} />
    </div>
  );
}
