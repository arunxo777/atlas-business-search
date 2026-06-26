import { useEffect, useState } from "react";
import { getLLMStatus, type LLMStatus } from "@/api/client";
import { cn } from "@/lib/utils";
import { Cpu } from "lucide-react";

interface LLMStatusBarProps {
  compact?: boolean;
}

export function LLMStatusBar({ compact = false }: LLMStatusBarProps) {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    const fetchStatus = async () => {
      try {
        const data = await getLLMStatus();
        setStatus(data);
      } catch {
        setStatus({
          provider: "none",
          model: "unavailable",
          latency_ms: null,
          available_providers: [],
        });
      } finally {
        clearTimeout(timeout);
        setLoading(false);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => {
      clearTimeout(timeout);
      clearInterval(interval);
      controller.abort();
    };
  }, []);

  const isAvailable = status && status.provider !== "none";

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        {!compact && "Checking LLM..."}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs",
        isAvailable
          ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
          : "border-red-500/20 bg-red-500/5 text-red-400"
      )}
    >
      <Cpu className="h-3 w-3 shrink-0" />
      {isAvailable ? (
        <span className={cn(compact && "max-w-[140px] truncate")}>
          <span className="font-medium">{status.provider}</span>
          {!compact && (
            <>
              <span className="opacity-50 mx-1">·</span>
              <span className="text-muted-foreground">{status.model}</span>
              {status.latency_ms != null && (
                <span className="opacity-50 ml-1 font-mono">
                  {Math.round(status.latency_ms)}ms
                </span>
              )}
            </>
          )}
        </span>
      ) : (
        <span>Backend offline</span>
      )}
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full shrink-0",
          isAvailable ? "bg-emerald-400" : "bg-red-400"
        )}
      />
    </div>
  );
}
