import type { ResearchJob } from "@/api/client";
import {
  BarChart3,
  Clock,
  Database,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

interface DataQualitySummaryProps {
  report?: {
    data_quality_summary?: Record<string, number>;
    search_summary?: Record<string, unknown>;
    source_recommendations?: Record<string, string>;
  } | null;
  job?: ResearchJob | null;
}

export function DataQualitySummary({ report, job }: DataQualitySummaryProps) {
  const quality = report?.data_quality_summary;
  const summary = report?.search_summary;
  const sourceRecs = report?.source_recommendations;
  const activeSources = summary?.active_sources as string[] | undefined;

  if (!quality && !job) return null;

  const metrics = quality
    ? [
        { label: "Website", value: quality.records_with_website, color: "bg-violet-500" },
        { label: "Phone", value: quality.records_with_phone, color: "bg-cyan-500" },
        { label: "Email", value: quality.records_with_email, color: "bg-fuchsia-500" },
        {
          label: "Hours",
          value: quality.records_with_hours ?? quality.records_with_working_hours,
          color: "bg-amber-500",
        },
        { label: "License", value: quality.records_with_license, color: "bg-emerald-500" },
        {
          label: "Highly Verified",
          value: quality.records_highly_verified,
          color: "bg-blue-500",
        },
      ]
    : [];

  const summaryItems = [
    {
      icon: Database,
      label: "Found",
      value: String(summary?.businesses_found ?? job?.businesses_found ?? 0),
    },
    {
      icon: ShieldCheck,
      label: "Verified",
      value: String(summary?.businesses_verified ?? job?.businesses_verified ?? 0),
    },
    {
      icon: Sparkles,
      label: "Dupes Removed",
      value: String(summary?.duplicates_removed ?? job?.duplicates_removed ?? 0),
    },
    {
      icon: BarChart3,
      label: "Sources",
      value: String(summary?.sources_searched ?? job?.sources_searched ?? 0),
    },
    {
      icon: Clock,
      label: "Duration",
      value:
        summary?.research_duration_seconds != null
          ? `${Number(summary.research_duration_seconds).toFixed(1)}s`
          : job?.duration_seconds != null
            ? `${job.duration_seconds.toFixed(1)}s`
            : "—",
    },
  ];

  return (
    <div className="card-premium space-y-8">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20">
          <BarChart3 className="h-5 w-5 text-violet-400" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Research Report</h2>
          <p className="text-sm text-muted-foreground">
            Data quality & pipeline summary
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {summaryItems.map((item) => (
          <div key={item.label} className="stat-card">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
              <item.icon className="h-3.5 w-3.5" />
              {item.label}
            </div>
            <p className="text-xl font-bold font-mono">{item.value}</p>
          </div>
        ))}
      </div>

      {activeSources && activeSources.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            Active Sources
          </h3>
          <div className="flex flex-wrap gap-2">
            {activeSources.map((s) => (
              <span
                key={s}
                className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs font-medium text-muted-foreground"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {metrics.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">
            Field Completeness
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {metrics.map((m) => (
              <div key={m.label} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{m.label}</span>
                  <span className="font-mono font-medium">{m.value ?? 0}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                  <div
                    className={`h-full rounded-full ${m.color} transition-all duration-700`}
                    style={{ width: `${m.value ?? 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {sourceRecs && Object.keys(sourceRecs).length > 0 && (
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">
            Best Source Per Field
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(sourceRecs)
              .slice(0, 9)
              .map(([field, source]) => (
                <div
                  key={field}
                  className="rounded-xl glass px-3 py-2.5 text-xs"
                >
                  <span className="text-muted-foreground capitalize">
                    {field.replace(/_/g, " ")}
                  </span>
                  <p className="font-medium mt-0.5 text-foreground">{source}</p>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
