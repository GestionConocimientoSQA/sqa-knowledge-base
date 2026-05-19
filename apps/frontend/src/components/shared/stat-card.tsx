import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

type Tone = "pass" | "fail" | "warn" | "neutral";

interface StatCardProps {
  label: string;
  value: string | number;
  delta?: string;
  tone?: Tone;
  hint?: string;
}

const TONE_CLASSES: Record<Tone, string> = {
  pass: "text-success",
  fail: "text-destructive",
  warn: "text-warning",
  neutral: "text-muted-foreground",
};

/**
 * Tarjeta de KPI. SRP: solo render. La data viene resuelta por el caller.
 */
export function StatCard({
  label,
  value,
  delta,
  tone = "neutral",
  hint,
}: StatCardProps) {
  return (
    <Card className="p-5">
      <div className="eyebrow">{label}</div>
      <div className="mt-2 font-display text-3xl font-extrabold tracking-tight tabular-nums">
        {value}
      </div>
      {delta && (
        <div className={cn("mt-1 text-xs font-semibold", TONE_CLASSES[tone])}>
          {delta}
        </div>
      )}
      {hint && (
        <div className="mt-3 text-xs text-muted-foreground">{hint}</div>
      )}
    </Card>
  );
}
