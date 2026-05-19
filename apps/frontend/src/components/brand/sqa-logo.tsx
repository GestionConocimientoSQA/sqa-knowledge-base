import { cn } from "@/lib/utils";

interface SqaLogoProps {
  className?: string;
  mode?: "light" | "dark";
}

/**
 * Logo SQA inline (SVG ligero). Reemplazable por <Image src="/logos/sqa.svg" />
 * cuando se agregue el asset oficial.
 */
export function SqaLogo({ className, mode = "dark" }: SqaLogoProps) {
  const fg = mode === "light" ? "#ffffff" : "hsl(var(--sqa-azul-corp))";
  return (
    <svg
      viewBox="0 0 96 28"
      role="img"
      aria-label="SQA"
      className={cn("h-6 w-auto", className)}
    >
      <text
        x="0"
        y="22"
        fontFamily="var(--font-display)"
        fontWeight={900}
        fontSize="22"
        fill={fg}
        letterSpacing="-0.04em"
      >
        SQA
      </text>
      <rect
        x="0"
        y="24"
        width="48"
        height="3"
        rx="1.5"
        fill="hsl(var(--sqa-naranja))"
      />
    </svg>
  );
}
