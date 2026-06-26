import { Link, useLocation } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { LLMStatusBar } from "@/components/LLMStatusBar";
import { cn } from "@/lib/utils";

function GradientBackground() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
      <div className="mesh-orb top-[-10%] left-[20%] h-[500px] w-[500px] bg-violet-600/20 animation-delay-100" />
      <div className="mesh-orb top-[30%] right-[-5%] h-[400px] w-[400px] bg-cyan-500/15 animation-delay-300" />
      <div className="mesh-orb bottom-[-10%] left-[-5%] h-[450px] w-[450px] bg-fuchsia-600/10 animation-delay-500" />
      <div className="absolute inset-0 bg-mesh-gradient opacity-60" />
      <div
        className="absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const isHome = location.pathname === "/";

  return (
    <div className="min-h-screen flex flex-col relative">
      <GradientBackground />

      <header className="sticky top-0 z-50 glass border-b border-white/[0.06]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 shadow-glow-sm transition-transform group-hover:scale-105">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-[15px] leading-tight tracking-tight">
                Atlas Research
              </span>
              <span className="text-[10px] text-muted-foreground leading-tight hidden sm:block">
                AI Business Intelligence
              </span>
            </div>
          </Link>

          <nav className="flex items-center gap-1">
            <Link
              to="/"
              className={cn(
                "btn-ghost text-xs sm:text-sm",
                isHome && "text-foreground bg-white/[0.06]"
              )}
            >
              Research
            </Link>
            <div className="hidden md:block ml-2 pl-2 border-l border-white/10">
              <LLMStatusBar compact />
            </div>
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-white/[0.06] py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-muted-foreground">
          <p>Multi-source verification · Source-attributed data · Ranked intelligence</p>
          <p className="font-mono text-[10px] opacity-60">
            LiteLLM · Firecrawl · SerpAPI · crawl4ai
          </p>
        </div>
      </footer>
    </div>
  );
}
