"use client";
import React from 'react';
import { Calendar, Activity } from 'lucide-react';

export default function RealizedProfit({ historicalProfit, navHistory }) {
    return (
        <div className="animate-in fade-in zoom-in duration-500">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* CỘT TRÁI: LỢI NHUẬN CHỐT SỔ */}
                <div className="lg:col-span-5 space-y-4">
                    <h3 className="text-slate-700 text-[15px] font-bold uppercase tracking-wider border-l-4 border-emerald-500 pl-3">Lợi nhuận chốt sổ</h3>
                    {!historicalProfit ? (
                        <div className="bg-white p-10 rounded-2xl border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm min-h-[280px]">
                            <Calendar size={32} className="text-slate-200 mb-4" />
                            <p className="text-slate-500 text-sm">Chọn ngày và nhấn "Kiểm tra".</p>
                        </div>
                    ) : (
                        <div className="bg-white p-5 rounded-[24px] border border-slate-400 shadow-[0_8px_30px_rgb(0,0,0,0.04)] min-h-[280px] flex flex-col justify-center">
                            <p className="text-[15px] text-slate-700 font-normal uppercase mb-2 tracking-[0.1em]">Tổng lãi/lỗ ròng</p>
                            <p className={`text-[26px] font-normal tracking-tight ${historicalProfit.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                {historicalProfit.total_profit >= 0 ? '+' : ''}{Math.floor(historicalProfit.total_profit).toLocaleString('en-US')}
                                <span className="text-[11px] font-normal text-slate-400 ml-1.5 uppercase tracking-wider">VND</span>
                            </p>
                            <div className="mt-6 pt-4 border-t border-slate-100 flex justify-between items-center">
                                <span className="text-[15px] text-slate-700 font-normal uppercase tracking-wider">Số lệnh đã chốt</span>
                                <span className="font-normal text-slate-700">{historicalProfit.trade_count} lệnh</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* CỘT PHẢI: NHẬT KÝ TÀI SẢN (NAV) */}
                <div className="lg:col-span-7 space-y-4">
                    <h3 className="text-slate-700 text-[15px] font-bold uppercase tracking-wider border-l-4 border-blue-500 pl-3">NHẬT KÝ TÀI SẢN (NAV)</h3>
                    <div className="bg-white rounded-[24px] border border-slate-400 shadow-[0_8px_30px_rgb(0,0,0,0.04)] overflow-hidden min-h-[280px]">

                        {/* PHẦN TỔNG HỢP HIỆU SUẤT TỔNG THEO SSI */}
                        {navHistory?.summary && (
                            <div className="p-5 bg-slate-50/50 border-b border-slate-400 grid grid-cols-2 lg:grid-cols-3 gap-6">
                                <div className="space-y-1">
                                    <p className="text-[12px] text-slate-500 font-medium uppercase tracking-wider">Hiệu suất đầu tư</p>
                                    <p className={`text-[22px] font-semibold ${navHistory.summary.total_performance_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                        {navHistory.summary.total_performance_pct >= 0 ? '+' : ''}{navHistory.summary.total_performance_pct.toFixed(2)}%
                                    </p>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[12px] text-slate-500 font-medium uppercase tracking-wider">Lợi nhuận tổng</p>
                                    <p className={`text-[22px] font-semibold ${navHistory.summary.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                        {navHistory.summary.total_profit >= 0 ? '+' : ''}{Math.floor(navHistory.summary.total_profit).toLocaleString()} <span className="text-[11px] font-normal text-slate-400 italic">VND</span>
                                    </p>
                                </div>
                                <div className="space-y-1 text-right lg:text-left">
                                    <p className="text-[12px] text-slate-500 font-medium uppercase tracking-wider">Net nộp rút cá nhân</p>
                                    <p className="text-[22px] font-semibold text-slate-700">
                                        {navHistory.summary.net_flow >= 0 ? '+' : ''}{Math.floor(navHistory.summary.net_flow).toLocaleString('en-US')} <span className="text-[11px] font-extrabold text-slate-400 uppercase tracking-wider">VND</span>
                                    </p>
                                </div>
                            </div>
                        )}

                        <div className="max-h-[280px] overflow-y-auto no-scrollbar">
                            {(() => {
                                const list = Array.isArray(navHistory) ? navHistory : (navHistory?.history || []);
                                if (list.length > 0) {
                                    return (
                                        <table className="w-full text-left">
                                            <thead className="sticky top-0 bg-slate-50 text-slate-600 text-[13px] uppercase font-black border-b border-slate-400"><tr><th className="p-4 pl-6">Ngày</th><th className="p-4 text-right">Tổng tài sản</th><th className="p-4 text-right pr-6">Biến động</th></tr></thead>
                                            <tbody className="divide-y divide-slate-50">{list.map((item, idx) => (
                                                <tr key={idx} className="hover:bg-slate-200 transition text-[15px]">
                                                    <td className="p-4 pl-6 font-normal text-slate-700">{item.date}</td>
                                                    <td className="p-4 text-right font-normal text-slate-900">{Math.floor(item.nav).toLocaleString()}</td>
                                                    <td className={`p-4 text-right pr-6 font-normal ${item.change >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{item.change >= 0 ? '+' : ''}{item.pct.toFixed(2)}%</td>
                                                </tr>
                                            ))}</tbody>
                                        </table>
                                    );
                                }
                                return <div className="h-[280px] flex flex-col items-center justify-center gap-3"><Activity size={40} className="text-slate-100 animate-pulse" /><p className="text-slate-400 text-xs italic">Đang chờ dữ liệu Snapshot...</p></div>;
                            })()}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
