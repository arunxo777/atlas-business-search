import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Loader2, Sparkles } from "lucide-react";
import { startResearch } from "@/api/client";
import { LLMStatusBar } from "./LLMStatusBar";
import { ModelSelector, type ProviderValue } from "./ModelSelector";
import { cn } from "@/lib/utils";

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
  const [provider, setProvider] = useState<ProviderValue>("auto");
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
            <ModelSelector
              value={provider}
              onChange={setProvider}
              disabled={loading}
            />

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
