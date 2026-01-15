"use client";
import { TrendingUp, TrendingDown } from "lucide-react";

export default function StatusBadge({ value, showIcon = true }) {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  const isPositive = numValue >= 0;
  const icon = isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />;

  // Enhanced color scheme with more vibrant colors
  const colorClass = isPositive
    ? 'bg-emerald-100 text-emerald-700'
    : 'bg-rose-100 text-rose-700';

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-md font-medium text-[13px] tabular-nums ${colorClass}`}>
      {showIcon && icon}
      {isPositive ? '+' : ''}{numValue.toFixed(2)}%
    </div>
  );
}