"use client";
import React, { useState, useEffect } from 'react';
import { TrendingUp, PlusCircle } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts';

// Bảng màu 10 sắc thái chuyên nghiệp cho các đường cổ phiếu
const COLORS = [
  '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4',
  '#f43f5e', '#ea580c', '#84cc16', '#a855f7', '#14b8a6'
];

export default function GrowthChart({
  chartData, chartRange, setChartRange, isDropdownOpen, setIsDropdownOpen,
  selectedComparisons, holdingTickers, toggleComparison
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  return (
    <div className="mb-6 bg-white rounded-2xl shadow-xl border border-slate-400 overflow-visible relative z-10">

      {/* --- HEADER BIỂU ĐỒ: TIÊU ĐỀ, CHU KỲ & SO SÁNH --- */}
      <div className="p-4 bg-slate-50/50 border-b border-slate-300 flex flex-col md:flex-row justify-between md:items-center gap-4">
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-600 uppercase tracking-tight">
          <TrendingUp size={20} className="text-slate-600" />
          Tăng trưởng (%)
        </h2>

        {/* Bộ chọn mốc thời gian: 12px, Bold, Giãn chữ chuẩn Zon */}
        <div className="flex bg-white border border-slate-400 p-1 rounded-lg shadow-sm">
          {['1m', '3m', '6m', '1y'].map((range) => (
            <button
              key={range}
              onClick={() => setChartRange(range)}
              className={`px-4 py-1.5 text-[12px] font-bold rounded-md uppercase transition-all tracking-wide ${chartRange === range ? 'bg-emerald-500 text-white shadow-sm' : 'text-slate-400 hover:bg-slate-50'
                }`}
            >
              {range}
            </button>
          ))}
        </div>

        {/* Nút Dropdown So sánh */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="bg-white border border-emerald-200 text-[12px] font-bold uppercase rounded-md px-4 py-2 flex items-center gap-2 text-slate-600 hover:bg-slate-50 transition shadow-sm tracking-wide"
          >
            <PlusCircle size={15} /> SO SÁNH ({selectedComparisons.length}/5)
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-2xl border border-slate-100 p-3 z-50 animate-in fade-in zoom-in duration-200">
              <p className="text-[10px] uppercase font-black text-slate-400 border-b border-slate-100 pb-2 mb-2">Đã chọn {selectedComparisons.length}/5</p>
              <div className="space-y-1 max-h-60 overflow-y-auto no-scrollbar">
                {['PORTFOLIO', 'VNINDEX', ...holdingTickers].map(t => {
                  const isSelected = selectedComparisons.includes(t);
                  const isDisabled = !isSelected && selectedComparisons.length >= 5;
                  return (
                    <label key={t} className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${isDisabled ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer hover:bg-slate-50'}`}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={isDisabled}
                        onChange={() => toggleComparison(t)}
                        className="accent-emerald-600 w-4 h-4 rounded border-slate-300"
                      />
                      <span className={`text-xs font-bold ${t === 'PORTFOLIO' ? 'text-blue-600' : 'text-slate-700'}`}>
                        {t === 'PORTFOLIO' ? 'Danh mục' : t === 'VNINDEX' ? 'VN-INDEX' : t}
                      </span>
                    </label>
                  )
                })}
              </div>
            </div>
          )}
          {isDropdownOpen && <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)}></div>}
        </div>
      </div>

      {/* --- THÂN BIỂU ĐỒ: ĐÃ FIX LỖI SIZING WARNING --- */}
      <div className="p-6 h-[350px] w-full min-h-[350px] relative block">
        {(!chartData || chartData.length <= 1) ? (
          /* Trạng thái khi chưa có data hoặc data rỗng */
          <div className="flex flex-col items-center justify-center h-full space-y-3">
            <div className="relative w-10 h-10">
              <div className="absolute inset-0 border-2 border-emerald-100 rounded-full"></div>
              <div className="absolute inset-0 border-2 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
            </div>
            <p className="text-slate-400 text-[11px] font-bold animate-pulse uppercase tracking-widest text-center">
              Đang đồng bộ dữ liệu thị trường...<br />
              <span className="text-[9px] font-medium lowercase italic opacity-60">(Lần đầu tải có thể mất vài giây)</span>
            </p>
          </div>
        ) : (
          /* Render Biểu đồ đường */
          mounted && (
            <ResponsiveContainer width="100%" height="100%" debounce={50} minWidth={0} minHeight={0}>
              <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#64748b', fontSize: 10, fontWeight: 700 }}
                  tickFormatter={(val) => `${val > 0 ? '+' : ''}${val}%`}
                />
                <Tooltip
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                  formatter={(value) => [`${value.toFixed(2)}%`]}
                  itemSorter={(item) => -item.value}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '20px', fontSize: '11px', fontWeight: 800 }}
                  iconType="circle"
                />

                {/* LOGIC VẼ ĐƯỜNG DỰA TRÊN CHỌN MÃ */}
                {selectedComparisons.map((ticker) => {
                  if (ticker === 'PORTFOLIO') {
                    return <Line key="PORTFOLIO" type="monotone" dataKey="PORTFOLIO" name="Danh mục" stroke="#2563eb" strokeWidth={3} dot={false} activeDot={{ r: 6, strokeWidth: 0, fill: '#2563eb' }} />;
                  }
                  if (ticker === 'VNINDEX') {
                    return <Line key="VNINDEX" type="monotone" dataKey="VNINDEX" name="VN-Index" stroke="#94a3b8" strokeWidth={2} dot={false} strokeDasharray="5 5" strokeOpacity={0.7} />;
                  }
                  const stockOnlyList = selectedComparisons.filter(t => t !== 'PORTFOLIO' && t !== 'VNINDEX');
                  const colorIdx = stockOnlyList.indexOf(ticker);
                  const color = COLORS[colorIdx % COLORS.length];
                  return <Line key={ticker} type="monotone" dataKey={ticker} name={ticker} stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 0 }} />;
                })}
              </LineChart>
            </ResponsiveContainer>
          )
        )}
      </div>
    </div>
  );
}