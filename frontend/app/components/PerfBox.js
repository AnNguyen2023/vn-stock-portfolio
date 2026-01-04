
// PerfBox.js
"use client";

export default function PerfBox({ label, data, isPrivate }) {
  const val = data?.val || 0;
  const pct = data?.pct || 0;
  const isPos = val >= 0;
  const color = isPos ? "text-emerald-600" : "text-rose-500";
  
  return (
    <div className="p-6 text-center hover:bg-slate-50/50 transition-colors cursor-default">
      {/* Mốc thời gian (1D, 1M...) */}
      <p className="text-slate-400 text-[10px] uppercase font-black tracking-[0.2em] mb-3">
        {label}
      </p>
      {/* Con số tiền lãi lỗ */}
      <p className={`text-xl font-black tracking-tighter transition-all duration-500 ${color} ${isPrivate ? 'blur-lg select-none opacity-20' : ''}`}>
        {isPos ? '+' : ''}{Math.floor(val).toLocaleString()}
      </p>
      {/* Phần trăm % */}
      <p className={`text-[10px] font-black mt-1 ${color} ${isPrivate ? 'blur-sm opacity-20' : ''}`}>
        ({isPos ? '+' : ''}{pct.toFixed(2)}%)
      </p>
    </div>
  );
}