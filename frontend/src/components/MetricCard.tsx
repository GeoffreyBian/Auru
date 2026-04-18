import clsx from "clsx";

interface Props {
  label: string;
  value: string | number;
  unit?: string;
  status?: "good" | "warn" | "bad" | "neutral";
  description?: string;
}

const STATUS_STYLES = {
  good: "border-emerald-700/50 bg-emerald-950/30",
  warn: "border-amber-700/50 bg-amber-950/20",
  bad: "border-red-700/50 bg-red-950/20",
  neutral: "border-zinc-700/50 bg-zinc-900",
};

const VALUE_STYLES = {
  good: "text-emerald-300",
  warn: "text-amber-300",
  bad: "text-red-300",
  neutral: "text-zinc-100",
};

export default function MetricCard({ label, value, unit, status = "neutral", description }: Props) {
  return (
    <div className={clsx("rounded-xl border p-5 flex flex-col gap-1", STATUS_STYLES[status])}>
      <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</p>
      <p className={clsx("text-3xl font-bold tabular-nums", VALUE_STYLES[status])}>
        {value}
        {unit && <span className="ml-1 text-base font-medium text-zinc-400">{unit}</span>}
      </p>
      {description && <p className="text-xs text-zinc-500 mt-1">{description}</p>}
    </div>
  );
}
