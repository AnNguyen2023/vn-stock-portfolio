"use client";
import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

export default function PortfolioAllocation({ data, PIE_COLORS }) {
    const [mounted, setMounted] = useState(false);
    useEffect(() => { setMounted(true); }, []);

    if (!data?.holdings || data.holdings.length === 0) {
        return (
            <div className="animate-in fade-in zoom-in duration-300 relative w-full h-[400px] flex items-center justify-center">
                <div className="text-slate-400 italic font-medium">Chưa có dữ liệu phân bổ cổ phiếu.</div>
            </div>
        );
    }

    return (
        <div className="animate-in fade-in zoom-in duration-300 relative w-full h-[400px] flex items-center justify-center">
            {/* KHUNG CHỨA BIỂU ĐỒ */}
            <div className="relative w-full h-full block">

                {/* PHẦN CHỮ HIỂN THỊ GIỮA VÒNG TRÒN */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
                    <p className="text-[13px] text-slate-600 font-bold uppercase tracking-[0.2em] mb-1">
                        Giá trị cổ phiếu
                    </p>
                    <p className="text-2xl font-black text-slate-800 tracking-tighter">
                        {Math.floor(data?.total_stock_value || 0).toLocaleString('en-US')}
                        <span className="text-xs font-bold text-slate-400 uppercase ml-1">vnd</span>
                    </p>
                </div>

                {/* BIỂU ĐỒ TRÒN */}
                {mounted && (
                    <ResponsiveContainer width="100%" height="100%" debounce={50} minWidth={0} minHeight={0}>
                        <PieChart>
                            <Pie
                                data={data.holdings}
                                cx="50%"
                                cy="50%"
                                innerRadius={100}
                                outerRadius={140}
                                paddingAngle={3}
                                dataKey="current_value"
                                nameKey="ticker"
                                stroke="none"
                                labelLine={false}
                                /* Label hiển thị bên ngoài cho thoáng */
                                label={({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) => {
                                    const RADIAN = Math.PI / 180;
                                    const radius = outerRadius + 20;
                                    const x = cx + radius * Math.cos(-midAngle * RADIAN);
                                    const y = cy + radius * Math.sin(-midAngle * RADIAN);
                                    return (
                                        <text x={x} y={y} fill="#475569" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" className="text-[15px] font-bold">
                                            {`${name} (${(percent * 100).toFixed(1)}%)`}
                                        </text>
                                    );
                                }}
                            >
                                {data.holdings.map((entry, index) => (
                                    <Cell
                                        key={`cell-${index}`}
                                        fill={PIE_COLORS[index % PIE_COLORS.length]}
                                        className="hover:opacity-80 transition-opacity outline-none"
                                    />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                                formatter={(val) => [`${Math.floor(val).toLocaleString()} vnd`, 'Giá trị']}
                            />
                        </PieChart>
                    </ResponsiveContainer>
                )}
            </div>
        </div>
    );
}
