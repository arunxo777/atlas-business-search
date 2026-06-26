import { cn } from "@/lib/utils";
import type { VerificationStatus } from "@/api/client";
import { ShieldCheck, ShieldQuestion, AlertTriangle } from "lucide-react";

const STATUS_CONFIG: Record<
  VerificationStatus,
  { label: string; className: string; icon: typeof ShieldCheck }
> = {
  highly_verified: {
    label: "Highly Verified",
    className: "badge-glow-emerald border",
    icon: ShieldCheck,
  },
  verified: {
    label: "Verified",
    className: "badge-glow-blue border",
    icon: ShieldCheck,
  },
  unverified: {
    label: "Unverified",
    className: "badge-muted border",
    icon: ShieldQuestion,
  },
  conflicted: {
    label: "Conflicted",
    className: "badge-glow-amber border",
    icon: AlertTriangle,
  },
};

interface VerificationBadgeProps {
  status: VerificationStatus;
  className?: string;
  showIcon?: boolean;
}

export function VerificationBadge({
  status,
  className,
  showIcon = true,
}: VerificationBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.unverified;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium",
        config.className,
        className
      )}
    >
      {showIcon && <Icon className="h-3 w-3" />}
      {config.label}
    </span>
  );
}
