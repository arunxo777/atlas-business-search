import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Loader2, Sparkles, ChevronDown } from "lucide-react";
import { startResearch } from "@/api/client";
import { LLMStatusBar } from "./LLMStatusBar";
import { cn } from "@/lib/utils";

const PROVIDERS = [
  { value: "auto", label: "Auto" },
  { value: "ollama", label: "Ollama" },
  { value: "groq", label: "Groq" },
  { value: "mistral", label: "Mistral" },
  { value: "openai", label: "OpenAI" },
];

const EXAMPLE_QUERIES = [
  "Money exchange in Madurai",
  "Cardiologists in Birmingham",
  "Best restaurants in Austin TX",
  "Dental clinics in Chennai",
];

interface SearchBarProps {
  className?: string;
  variant?: "hero" | "compact";
}

export function SearchBar({ className, variant = "hero" }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [provider, setProvider] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const response = await startResearch({
        query: query.trim(),
        max_results: 100,
        llm_provider: provider === "auto" ? null : provider,
      });
      navigate(`/results/${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start research");
    } finally {
      setLoading(false);
    }
  };

  const setExample = (q: string) => {
    setQuery(q);
  };

  if (variant === "compact") {
    return (
      <form onSubmit={handleSubmit} className={cn("flex gap-2", className)}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="New search..."
          className="input-premium flex-1 !py-2 !rounded-xl text-sm"
          disabled={loading}
        />
        <button type="submit" disabled={loading || !query.trim()} className="btn-primary !py-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Go"}
        </button>
      </form>
    );
  }

  return (
    <div className={cn("w-full max-w-2xl mx-auto space-y-4", className)}>
      <form onSubmit={handleSubmit}>
        <div
          className={cn(
            "relative rounded-2xl glass-elevated transition-all duration-300",
            focused && "ring-2 ring-primary/30 shadow-glow border-primary/20"
          )}
        >
          <div className="flex items-start gap-3 p-4 sm:p-5">
            <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-fuchsia-500/20">
              <Sparkles className="h-4 w-4 text-violet-400" />
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="What businesses are you researching?"
              rows={2}
              className="flex-1 resize-none bg-transparent text-[15px] leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-50"
              disabled={loading}
            />
          </div>

          <div className="flex items-center justify-between gap-3 px-4 sm:px-5 pb-4 border-t border-white/[0.06] pt-3">
            <div className="relative">
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="appearance-none rounded-lg border border-white/10 bg-white/[0.04] pl-3 pr-8 py-1.5 text-xs font-medium text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40 cursor-pointer"
                disabled={loading}
              >
                {PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value} className="bg-zinc-900">
                    {p.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground pointer-events-none" />
            </div>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="btn-primary !rounded-xl !px-5 !py-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Research
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-3 text-sm text-red-400 text-center">{error}</p>
        )}
      </form>

      <div className="flex flex-wrap justify-center gap-2">
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => setExample(q)}
            className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1 text-xs text-muted-foreground transition-all hover:bg-white/[0.06] hover:text-foreground hover:border-white/15"
          >
            {q}
          </button>
        ))}
      </div>

      <div className="flex justify-center md:hidden">
        <LLMStatusBar />
      </div>
    </div>
  );
}
