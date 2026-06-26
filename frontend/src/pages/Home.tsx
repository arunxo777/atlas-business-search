import { SearchBar } from "@/components/SearchBar";
import {
  ShieldCheck,
  Layers,
  Zap,
  Globe2,
  BarChart3,
  FileCheck2,
  ArrowRight,
} from "lucide-react";

const PIPELINE = [
  { step: "01", label: "Search", desc: "8+ sources in parallel" },
  { step: "02", label: "Scrape", desc: "LLM-ready extraction" },
  { step: "03", label: "Enrich", desc: "Websites & social" },
  { step: "04", label: "Dedup", desc: "Fuzzy + AI merge" },
  { step: "05", label: "Verify", desc: "Cross-source proof" },
  { step: "06", label: "Rank", desc: "Trust-weighted score" },
];

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Hallucination-Resistant",
    desc: "Every field requires a source URL. Unsourced data is stripped — far less hallucination than typical scrapers.",
    gradient: "from-emerald-500/20 to-emerald-500/5",
    iconColor: "text-emerald-400",
  },
  {
    icon: Layers,
    title: "Smart Deduplication",
    desc: "Phone matching, fuzzy names, and LLM confirmation merge duplicate listings.",
    gradient: "from-violet-500/20 to-violet-500/5",
    iconColor: "text-violet-400",
  },
  {
    icon: Globe2,
    title: "Multi-Source Engine",
    desc: "SerpAPI, Firecrawl, Google Scraper, Yelp, YellowPages, Maps & more.",
    gradient: "from-cyan-500/20 to-cyan-500/5",
    iconColor: "text-cyan-400",
  },
  {
    icon: BarChart3,
    title: "Trust Ranking",
    desc: "Businesses scored by verification, completeness, ratings, and source reliability.",
    gradient: "from-fuchsia-500/20 to-fuchsia-500/5",
    iconColor: "text-fuchsia-400",
  },
  {
    icon: FileCheck2,
    title: "Research Report",
    desc: "Data quality metrics, source recommendations, and exportable insights.",
    gradient: "from-amber-500/20 to-amber-500/5",
    iconColor: "text-amber-400",
  },
  {
    icon: Zap,
    title: "Live Pipeline",
    desc: "Watch businesses appear in real-time as the agent searches, verifies, and ranks.",
    gradient: "from-orange-500/20 to-orange-500/5",
    iconColor: "text-orange-400",
  },
];

export function Home() {
  return (
    <div className="relative">
      {/* Hero */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 pt-20 pb-16 text-center">
        <div
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-xs font-medium text-muted-foreground mb-8 animate-fade-in"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          Production-grade business intelligence agent
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6 animate-fade-in-up">
          <span className="gradient-text">Discover businesses</span>
          <br />
          <span className="gradient-text-accent">you can trust</span>
        </h1>

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed animate-fade-in-up animation-delay-100 opacity-0 [animation-fill-mode:forwards]">
          Multi-source research with cross-verification, deduplication, and
          trust-weighted ranking — with source proof on every field, not blind LLM guesses.
        </p>

        <div className="animate-fade-in-up animation-delay-200 opacity-0 [animation-fill-mode:forwards]">
          <SearchBar />
        </div>
      </section>

      {/* Pipeline */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16">
        <div className="text-center mb-10">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Research Pipeline
          </h2>
          <p className="text-2xl font-bold gradient-text">
            Six stages of verified intelligence
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {PIPELINE.map((item, i) => (
            <div
              key={item.step}
              className="group relative rounded-2xl glass p-4 text-center transition-all duration-300 hover:bg-white/[0.06] hover:border-white/[0.12] hover:-translate-y-1"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              <div className="text-[10px] font-mono text-primary/60 mb-2">
                {item.step}
              </div>
              <div className="font-semibold text-sm mb-1">{item.label}</div>
              <div className="text-[11px] text-muted-foreground leading-snug">
                {item.desc}
              </div>
              {i < PIPELINE.length - 1 && (
                <ArrowRight className="hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-white/20" />
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16 pb-24">
        <div className="text-center mb-12">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground mb-2">
            Why Atlas
          </h2>
          <p className="text-2xl font-bold gradient-text">
            Built for hackathon judges who've seen 50 scrapers
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="card-premium group cursor-default"
            >
              <div
                className={`inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ${feature.gradient} mb-4 transition-transform group-hover:scale-110`}
              >
                <feature.icon className={`h-5 w-5 ${feature.iconColor}`} />
              </div>
              <h3 className="font-semibold text-[15px] mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
