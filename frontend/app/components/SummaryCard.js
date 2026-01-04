// SummaryCard.js
"use client";

export default function SummaryCard({ title, value, icon, color, bg, isPrivate }) {
  // Định dạng số có dấu phẩy (2,000,000,000)
  const formatted = value ? Number(value).toLocaleString('en-US') : '0';

  return (
    <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 hover:shadow-md transition-all duration-300 group">
      <div className="flex justify-between items-start">
        <div>
           {/* Tiêu đề nhỏ bên trên */}
           <p className="text-sm font-bold text-slate-600 uppercase tracking-tight mb-2">{title}</p>
           {/* Con số tiền chính */}
           <h3 className={`text-2xl font-black tracking-tighter ${color} transition-all duration-500 ${isPrivate ? 'blur-md select-none opacity-20' : ''}`}>
             {isPrivate ? '888,888,888' : formatted} 
             <span className="text-[10px] font-bold text-slate-300 ml-1 uppercase">vnd</span>
           </h3>
        </div>
        {/* Icon bên phải */}
        <div className={`p-4 rounded-2xl ${bg} ${color} group-hover:scale-110 transition-all duration-300 shadow-sm`}>
          {icon}
        </div>
      </div>
    </div>
  );
}