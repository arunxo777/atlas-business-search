import { Download, FileJson, FileSpreadsheet, Table2 } from "lucide-react";
import { getExportUrl } from "@/api/client";
import { cn } from "@/lib/utils";

interface ExportPanelProps {
  jobId: string;
  className?: string;
}

export function ExportPanel({ jobId, className }: ExportPanelProps) {
  const formats = [
    { format: "json" as const, label: "JSON", icon: FileJson },
    { format: "csv" as const, label: "CSV", icon: Table2 },
    { format: "xlsx" as const, label: "Excel", icon: FileSpreadsheet },
  ];

  return (
    <div className={cn("flex flex-col sm:flex-row items-start sm:items-center gap-2", className)}>
      <span className="text-xs font-medium uppercase tracking-widest text-muted-foreground mr-1">
        Export
      </span>
      <div className="flex gap-2">
        {formats.map(({ format, label, icon: Icon }) => (
          <a
            key={format}
            href={getExportUrl(jobId, format)}
            download
            className="btn-outline !py-1.5 !px-3 !text-xs group"
          >
            <Icon className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary transition-colors" />
            {label}
            <Download className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity -ml-1" />
          </a>
        ))}
      </div>
    </div>
  );
}
