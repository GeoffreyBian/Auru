import { Lightbulb } from "lucide-react";

interface Props {
  insights: string[];
}

export default function InsightCard({ insights }: Props) {
  if (insights.length === 0) return null;
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="h-4 w-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-zinc-200">Coaching Insights</h3>
      </div>
      <ul className="space-y-3">
        {insights.map((insight, i) => (
          <li key={i} className="flex gap-3 text-sm text-zinc-300 leading-relaxed">
            <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-amber-900/50 text-amber-400 text-xs flex items-center justify-center font-bold">
              {i + 1}
            </span>
            {insight}
          </li>
        ))}
      </ul>
    </div>
  );
}
