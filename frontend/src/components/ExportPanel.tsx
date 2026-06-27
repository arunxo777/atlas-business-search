import { Download, FileJson, FileSpreadsheet, FileText, Table2 } from "lucide-react";
import { getExportUrl } from "@/api/client";
import { cn } from "@/lib/utils";

interface ExportPanelProps {
  jobId: string;
  className?: string;
}

export function ExportPanel({ jobId, className }: ExportPanelProps) {
  const formats = [
    { format: "pdf" as const, label: "PDF", icon: FileText, primary: true },
    { format: "json" as const, label: "JSON", icon: FileJson },
    { format: "csv" as const, label: "CSV", icon: Table2 },
    { format: "xlsx" as const, label: "Excel", icon: FileSpreadsheet },
  ];

  return (
    <div className={cn("flex flex-col sm:flex-row items-start sm:items-center gap-2", className)}>
      <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground mr-1">
        Export
      </span>
      <div className="flex flex-wrap gap-2">
        {formats.map(({ format, label, icon: Icon, primary }) => (
          <a
            key={format}
            href={getExportUrl(jobId, format)}
            download
            className={cn(
              "inline-flex items-center gap-1.5 !py-1.5 !px-3 !text-xs group",
              primary ? "btn-primary" : "btn-outline"
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
            <Download className="h-3 w-3 opacity-60" />
          </a>
        ))}
      </div>
    </div>
  );
}
