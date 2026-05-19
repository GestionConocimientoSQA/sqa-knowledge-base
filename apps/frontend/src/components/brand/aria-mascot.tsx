"use client";

import { cn } from "@/lib/utils";

interface AriaMascotProps {
  size?: number;
  status?: "idle" | "speaking" | "thinking";
  className?: string;
}

/**
 * Burbuja mascota Aria. Hexágono SQA con halo animado cuando "habla".
 */
export function AriaMascot({
  size = 36,
  status = "idle",
  className,
}: AriaMascotProps) {
  const animate = status === "speaking";
  return (
    <div
      className={cn("relative flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <div
        className="absolute inset-0 hex-clip-flat bg-sqa-naranja"
        style={
          animate
            ? { animation: "pulse-halo 1.6s ease-out infinite" }
            : undefined
        }
      />
      <div className="absolute inset-[6%] hex-clip-flat bg-sqa-ink" />
      <span
        className="relative font-display font-black text-sqa-naranja"
        style={{ fontSize: size * 0.42 }}
      >
        A
      </span>
    </div>
  );
}
