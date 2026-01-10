// SummaryCard.js
"use client";

export default function SummaryCard({ title, value, icon, color, bg, isPrivate }) {
  // Định dạng số có dấu phẩy (2,000,000,000)
  const formatted = value ? Number(value).toLocaleString('en-US') : '0';

  return (
    <div className="bg-white p-5 rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-400 hover:shadow-[0_20px_40px_rgba(0,0,0,0.08)] hover:scale-[1.02] transition-all duration-500 group relative overflow-hidden">
      {/* Subtle background glow on hover */}
      <div className={`absolute -right-4 -top-4 w-24 h-24 rounded-full ${bg} opacity-0 group-hover:opacity-20 transition-opacity duration-700 blur-3xl`}></div>

      <div className="flex justify-between items-start relative z-10">
        <div>
          {/* Tiêu đề nhỏ bên trên - đậm và rõ nét hơn */}
          <p className="text-base font-medium text-slate-600 uppercase tracking-tight mb-2">{title}</p>
          {/* Con số tiền chính - Bold mãnh (extrabold) và sắc nét */}
          <h3 className={`text-[26px] font-bold tracking-tight ${color} transition-all duration-500 ${isPrivate ? 'blur-md select-none opacity-20' : ''}`}>
            {isPrivate ? '8,888,888,888' : formatted}
            <span className="text-[10px] font-bold text-slate-400 ml-1.5 uppercase tracking-wider italic">vnd</span>
          </h3>
        </div>
        {/* Icon bên phải - Có chiều sâu */}
        <div className={`p-4 rounded-2xl ${bg} ${color} group-hover:scale-110 transition-all duration-500 shadow-[0_4px_12px_rgba(0,0,0,0.05)] border border-white/50`}>
          {icon}
        </div>
      </div>
    </div>
  );
}