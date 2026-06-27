import { cn } from "@/lib/utils";

interface AtlasLogoProps {
  size?: number;
  className?: string;
  showGlow?: boolean;
}

const RAYS = Array.from({ length: 8 }, (_, i) => {
  const angle = (i * 45 * Math.PI) / 180;
  const cx = 16;
  const cy = 16;
  const inner = 2.6;
  const outer = 7.2;
  return {
    x1: cx + inner * Math.cos(angle),
    y1: cy + inner * Math.sin(angle),
    x2: cx + outer * Math.cos(angle),
    y2: cy + outer * Math.sin(angle),
  };
});

/** Navy mark with concentric rings + eight-point star */
export function AtlasLogo({
  size = 36,
  className,
  showGlow = true,
}: AtlasLogoProps) {
  return (
    <div
      className={cn(
        "relative flex shrink-0 items-center justify-center rounded-xl bg-[#1e3a5f]",
        showGlow && "shadow-glow-sm",
        "transition-transform duration-300 group-hover:scale-105",
        className
      )}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        viewBox="0 0 32 32"
        fill="none"
        className="h-[88%] w-[88%]"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="16"
          cy="16"
          r="13"
          stroke="white"
          strokeWidth="0.75"
          strokeOpacity="0.18"
        />
        <circle
          cx="16"
          cy="16"
          r="9.5"
          stroke="white"
          strokeWidth="0.75"
          strokeOpacity="0.32"
        />
        {RAYS.map((ray, i) => (
          <line
            key={i}
            x1={ray.x1}
            y1={ray.y1}
            x2={ray.x2}
            y2={ray.y2}
            stroke="white"
            strokeWidth="1.35"
            strokeLinecap="round"
          />
        ))}
        <circle cx="16" cy="16" r="1.6" fill="white" />
      </svg>
    </div>
  );
}
