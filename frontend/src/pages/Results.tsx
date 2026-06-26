import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Sparkles,
  Clock,
} from "lucide-react";
import { DataQualitySummary } from "@/components/DataQualitySummary";
import {
  getJob,
  getResults,
  type BusinessRecord,
  type ResearchJob,
  type ResearchReport,
} from "@/api/client";
import { ResearchProgress } from "@/components/ResearchProgress";
import { BusinessTable } from "@/components/BusinessTable";
import { ExportPanel } from "@/components/ExportPanel";
import { cn } from "@/lib/utils";

export function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  const [businesses, setBusinesses] = useState<BusinessRecord[]>([]);
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [report, setReport] = useState<ResearchReport | null>(null);

  useEffect(() => {
    if (!jobId) return;
    getJob(jobId)
      .then(async (j) => {
        setJob(j);
        if (j.status === "complete") {
          setIsComplete(true);
          const results = await getResults(jobId, {
            page_size: 500,
            sort_by: "rank_score",
            sort_order: "desc",
          });
          setBusinesses(results.items);
        }
      })
      .catch(() => undefined);
  }, [jobId]);

  const handleBusinessFound = useCallback((business: BusinessRecord) => {
    setBusinesses((prev) => {
      const exists = prev.some((b) => b.id === business.id);
      if (exists) return prev;
      return [...prev, business];
    });
  }, []);

  const handleComplete = useCallback(
    async (completedJob: ResearchJob) => {
      setJob(completedJob);
      if (completedJob.research_report) {
        setReport(completedJob.research_report);
      }
      setIsComplete(true);
      if (!jobId) return;
      try {
        const results = await getResults(jobId, {
          page_size: 500,
          sort_by: "rank_score",
          sort_order: "desc",
        });
        setBusinesses(results.items);
      } catch {
        /* keep streamed rows if refresh fails */
      }
    },
    [jobId]
  );

  if (!jobId) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-muted-foreground">
        Invalid job ID
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
        <div className="space-y-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
            New research
          </Link>

          {job && (
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-2xl sm:text-3xl font-bold tracking-tight gradient-text">
                  {job.query}
                </h1>
                <StatusPill complete={isComplete} />
              </div>
              {job.category && job.location && (
                <p className="text-muted-foreground flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  {job.category} in {job.location}
                </p>
              )}
            </div>
          )}
        </div>

        {isComplete && jobId && (
          <div className="shrink-0">
            <ExportPanel jobId={jobId} />
          </div>
        )}
      </div>

      {job && job.error && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-200">
          {job.error}
        </div>
      )}

      {/* Progress or Report */}
      {!isComplete ? (
        <div className="card-premium">
          <ResearchProgress
            jobId={jobId}
            onBusinessFound={handleBusinessFound}
            onComplete={handleComplete}
          />
        </div>
      ) : (
        <DataQualitySummary report={report} job={job} />
      )}

      {/* Results Table */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Ranked Results
            {businesses.length > 0 && (
              <span className="text-sm font-normal text-muted-foreground">
                ({businesses.length} businesses)
              </span>
            )}
          </h2>
          {!isComplete && businesses.length > 0 && (
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin text-primary" />
              Live updates
            </span>
          )}
        </div>

        <BusinessTable
          jobId={jobId}
          businesses={businesses}
          loading={!isComplete && businesses.length === 0}
        />
      </div>
    </div>
  );
}

function StatusPill({ complete }: { complete: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border",
        complete
          ? "badge-glow-emerald border"
          : "bg-primary/10 text-primary border-primary/30"
      )}
    >
      {complete ? (
        <>
          <CheckCircle2 className="h-3 w-3" />
          Complete
        </>
      ) : (
        <>
          <Clock className="h-3 w-3 animate-pulse" />
          Running
        </>
      )}
    </span>
  );
}
