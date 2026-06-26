import { useEffect, useRef, useState } from "react";
import {
  Sparkles,
  ChevronDown,
  Check,
  Cpu,
  Zap,
  Cloud,
  Bot,
} from "lucide-react";
import { getLLMStatus } from "@/api/client";
import { cn } from "@/lib/utils";

export type ProviderValue = "auto" | "ollama" | "groq" | "mistral" | "openai";

interface ProviderOption {
  value: ProviderValue;
  label: string;
  description: string;
  icon: typeof Sparkles;
  iconBg: string;
  iconColor: string;
}

const ALL_PROVIDERS: ProviderOption[] = [
  {
    value: "auto",
    label: "Auto",
    description: "Routes to the best available model",
    icon: Sparkles,
    iconBg: "from-violet-500/20 to-fuchsia-500/20",
    iconColor: "text-violet-300",
  },
  {
    value: "groq",
    label: "Groq",
    description: "Ultra-fast cloud inference",
    icon: Zap,
    iconBg: "from-orange-500/20 to-amber-500/20",
    iconColor: "text-orange-300",
  },
  {
    value: "ollama",
    label: "Ollama",
    description: "Local model on your machine",
    icon: Cpu,
    iconBg: "from-emerald-500/20 to-teal-500/20",
    iconColor: "text-emerald-300",
  },
  {
    value: "mistral",
    label: "Mistral",
    description: "Mistral AI cloud",
    icon: Cloud,
    iconBg: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-300",
  },
  {
    value: "openai",
    label: "GPT",
    description: "OpenAI models",
    icon: Bot,
    iconBg: "from-gray-500/20 to-zinc-500/20",
    iconColor: "text-gray-300",
  },
];

interface ModelSelectorProps {
  value: ProviderValue;
  onChange: (value: ProviderValue) => void;
  disabled?: boolean;
  className?: string;
}

export function ModelSelector({
  value,
  onChange,
  disabled = false,
  className,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const [available, setAvailable] = useState<string[]>([]);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getLLMStatus()
      .then((s) => {
        setAvailable(s.available_providers ?? []);
        if (s.provider !== "none" && s.model) {
          setActiveModel(`${s.provider} · ${s.model}`);
        }
      })
      .catch(() => setAvailable([]));
  }, []);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const options = ALL_PROVIDERS.filter(
    (p) => p.value === "auto" || available.includes(p.value)
  );

  useEffect(() => {
    if (value !== "auto" && !available.includes(value) && available.length > 0) {
      onChange("auto");
    }
  }, [available, value, onChange]);

  const selected =
    ALL_PROVIDERS.find((p) => p.value === value) ?? ALL_PROVIDERS[0];
  const SelectedIcon = selected.icon;

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04]",
          "px-3 py-1.5 text-xs font-medium transition-all duration-200",
          "hover:bg-white/[0.08] hover:border-white/20",
          open && "bg-white/[0.08] border-white/20 ring-1 ring-primary/20",
          disabled && "opacity-50 pointer-events-none"
        )}
      >
        <span
          className={cn(
            "flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br",
            selected.iconBg
          )}
        >
          <SelectedIcon className={cn("h-3 w-3", selected.iconColor)} />
        </span>
        <span className="text-foreground/90">{selected.label}</span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-muted-foreground transition-transform duration-200",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div
          className={cn(
            "absolute bottom-full left-0 mb-2 z-50 w-72",
            "rounded-2xl border border-white/10 bg-zinc-950/95 backdrop-blur-xl",
            "shadow-elevated p-1.5 animate-fade-in"
          )}
          style={{ boxShadow: "0 8px 32px -8px rgba(0,0,0,0.6)" }}
        >
          <div className="px-3 py-2 border-b border-white/[0.06] mb-1">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
              Model
            </p>
            {activeModel && (
              <p className="text-[10px] text-muted-foreground/70 mt-0.5 truncate">
                Active: {activeModel}
              </p>
            )}
          </div>

          <div className="max-h-64 overflow-y-auto">
            {options.map((opt) => {
              const Icon = opt.icon;
              const isSelected = value === opt.value;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className={cn(
                    "w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-left",
                    "transition-colors duration-150",
                    isSelected
                      ? "bg-primary/10 border border-primary/20"
                      : "hover:bg-white/[0.05] border border-transparent"
                  )}
                >
                  <span
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br",
                      opt.iconBg
                    )}
                  >
                    <Icon className={cn("h-4 w-4", opt.iconColor)} />
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{opt.label}</p>
                    <p className="text-[11px] text-muted-foreground leading-snug">
                      {opt.description}
                    </p>
                  </div>
                  {isSelected && (
                    <Check className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </button>
              );
            })}
          </div>

          {options.length <= 1 && (
            <p className="px-3 py-2 text-[10px] text-muted-foreground">
              Start the backend to detect available models.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
