import { useMemo, useState, Fragment } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  Search,
  Star,
  ExternalLink,
  Loader2,
} from "lucide-react";
import type { BusinessRecord } from "@/api/client";
import { VerificationBadge } from "./VerificationBadge";
import { BusinessCard } from "./BusinessCard";
import { cn } from "@/lib/utils";

interface BusinessTableProps {
  jobId: string;
  businesses: BusinessRecord[];
  loading?: boolean;
}

export function BusinessTable({
  jobId: _jobId,
  businesses,
  loading = false,
}: BusinessTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "rank_score", desc: true },
  ]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState(25);

  const columns = useMemo<ColumnDef<BusinessRecord>[]>(
    () => [
      {
        id: "rank_score",
        accessorKey: "rank_score",
        header: "Rank",
        cell: ({ row, table }) => {
          const position =
            table.getSortedRowModel().rows.findIndex((r) => r.id === row.id) + 1;
          const score = row.original.rank_score ?? 0;
          const isTop3 = position <= 3 && score > 0;

          return (
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-lg font-mono text-xs font-bold",
                  isTop3
                    ? "bg-gradient-to-br from-violet-500/30 to-fuchsia-500/30 text-violet-300"
                    : "bg-white/[0.04] text-muted-foreground"
                )}
              >
                {position}
              </div>
              {score > 0 && (
                <span className="text-[10px] text-muted-foreground font-mono hidden lg:block">
                  {score.toFixed(1)}
                </span>
              )}
            </div>
          );
        },
      },
      {
        accessorKey: "business_name",
        header: "Business",
        cell: ({ row }) => (
          <div className="min-w-[160px]">
            <span className="font-medium text-[13px] leading-snug">
              {row.original.business_name}
            </span>
          </div>
        ),
      },
      {
        accessorKey: "address",
        header: "Address",
        cell: ({ row }) => (
          <span className="text-xs text-muted-foreground truncate max-w-[180px] block">
            {row.original.address ?? "—"}
          </span>
        ),
      },
      {
        accessorKey: "phone",
        header: "Phone",
        cell: ({ row }) => (
          <span className="text-xs font-mono">
            {row.original.phone[0] ?? "—"}
            {row.original.phone.length > 1 && (
              <span className="text-muted-foreground ml-1">
                +{row.original.phone.length - 1}
              </span>
            )}
          </span>
        ),
        enableSorting: false,
      },
      {
        accessorKey: "website",
        header: "Web",
        cell: ({ row }) =>
          row.original.website ? (
            <a
              href={row.original.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              {safeHostname(row.original.website)}
              <ExternalLink className="h-3 w-3 opacity-50" />
            </a>
          ) : (
            <span className="text-muted-foreground/50">—</span>
          ),
      },
      {
        accessorKey: "rating",
        header: "Rating",
        cell: ({ row }) =>
          row.original.rating != null ? (
            <span className="inline-flex items-center gap-1 text-xs font-medium">
              <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
              {row.original.rating.toFixed(1)}
            </span>
          ) : (
            <span className="text-muted-foreground/50">—</span>
          ),
      },
      {
        accessorKey: "verification_status",
        header: "Trust",
        cell: ({ row }) => (
          <VerificationBadge status={row.original.verification_status} />
        ),
      },
      {
        id: "sources_count",
        header: "Src",
        cell: ({ row }) => (
          <span className="text-xs font-mono text-muted-foreground">
            {row.original.raw_sources.length}
          </span>
        ),
        enableSorting: false,
      },
    ],
    []
  );

  const table = useReactTable({
    data: businesses,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    globalFilterFn: "includesString",
    initialState: { pagination: { pageSize } },
  });

  const SortIcon = ({ columnId }: { columnId: string }) => {
    const sorted = sorting.find((s) => s.id === columnId);
    if (!sorted) return <ChevronsUpDown className="h-3 w-3 opacity-40" />;
    return sorted.desc ? (
      <ChevronDown className="h-3 w-3 text-primary" />
    ) : (
      <ChevronUp className="h-3 w-3 text-primary" />
    );
  };

  if (loading && businesses.length === 0) {
    return (
      <div className="card-premium flex flex-col items-center justify-center py-20 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground text-sm">
          Searching across multiple sources...
        </p>
      </div>
    );
  }

  if (businesses.length === 0) {
    return (
      <div className="card-premium flex flex-col items-center justify-center py-20 gap-2">
        <Search className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-muted-foreground text-sm">No businesses found yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Filter results..."
          className="input-premium !py-2 !pl-10 !rounded-xl text-sm w-full"
        />
      </div>

      <div className="rounded-2xl glass-elevated overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm table-premium">
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3.5 text-left text-[11px] font-semibold uppercase tracking-wider text-muted-foreground"
                    >
                      {header.column.getCanSort() ? (
                        <button
                          type="button"
                          className="flex items-center gap-1.5 hover:text-foreground transition-colors"
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          <SortIcon columnId={header.id} />
                        </button>
                      ) : (
                        flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <Fragment key={row.id}>
                  <tr
                    onClick={() =>
                      setExpandedId(
                        expandedId === row.original.id ? null : row.original.id
                      )
                    }
                    className={cn(
                      "cursor-pointer",
                      expandedId === row.original.id && "bg-white/[0.04]"
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3.5">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </td>
                    ))}
                  </tr>
                  {expandedId === row.original.id && (
                    <tr>
                      <td
                        colSpan={columns.length}
                        className="p-0 bg-white/[0.02] border-t border-white/[0.06]"
                      >
                        <BusinessCard business={row.original} defaultExpanded />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-2">
          <span>Rows:</span>
          <select
            value={table.getState().pagination.pageSize}
            onChange={(e) => {
              const size = Number(e.target.value);
              setPageSize(size);
              table.setPageSize(size);
            }}
            className="rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40"
          >
            {[25, 50, 100].map((size) => (
              <option key={size} value={size} className="bg-zinc-900">
                {size}
              </option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono">
            {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
          </span>
          <button
            type="button"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="btn-outline !py-1 !px-3 disabled:opacity-30"
          >
            Prev
          </button>
          <button
            type="button"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="btn-outline !py-1 !px-3 disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

function safeHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url.slice(0, 20);
  }
}
