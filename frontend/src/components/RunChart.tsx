"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface DataPoint {
  time_sec: number;
  value: number;
}

interface Props {
  title: string;
  data: DataPoint[];
  color?: string;
  unit?: string;
  referenceLines?: { x: number; label: string; color: string }[];
  invertY?: boolean;
  yDomain?: [number | "auto", number | "auto"];
  formatValue?: (v: number) => string;
}

const defaultFormat = (v: number) => v.toFixed(1);

export default function RunChart({
  title,
  data,
  color = "#10b981",
  unit = "",
  referenceLines = [],
  invertY = false,
  yDomain,
  formatValue = defaultFormat,
}: Props) {
  if (data.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <p className="text-sm font-semibold text-zinc-300 mb-4">{title}</p>
        <div className="flex h-36 items-center justify-center text-sm text-zinc-600">
          No data available
        </div>
      </div>
    );
  }

  const domain: [number | "auto", number | "auto"] = yDomain ?? ["auto", "auto"];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
      <p className="text-sm font-semibold text-zinc-300 mb-4">{title}</p>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad-${title}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
          <XAxis
            dataKey="time_sec"
            tickFormatter={(v) => `${Math.floor(v / 60)}:${String(Math.floor(v % 60)).padStart(2, "0")}`}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            reversed={invertY}
            domain={domain}
            tickFormatter={(v) => `${formatValue(v)}${unit}`}
            tick={{ fill: "#71717a", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip
            contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
            labelStyle={{ color: "#a1a1aa", fontSize: 11 }}
            itemStyle={{ color: color }}
            labelFormatter={(v) => {
              const mins = Math.floor(Number(v) / 60);
              const secs = Math.floor(Number(v) % 60);
              return `${mins}:${String(secs).padStart(2, "0")}`;
            }}
            formatter={(v) => [`${formatValue(Number(v))}${unit}`, title]}
          />
          {referenceLines.map((rl) => (
            <ReferenceLine
              key={rl.x}
              x={rl.x}
              stroke={rl.color}
              strokeDasharray="4 3"
              label={{ value: rl.label, fill: rl.color, fontSize: 10, position: "insideTopRight" }}
            />
          ))}
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            fill={`url(#grad-${title})`}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
