"use client";
import React, { useState } from 'react';
import { Book, Eye, X } from 'lucide-react';

export default function OrderLog({ logs, setEditingNote, setShowNoteModal }) {
    const [showNoteSummary, setShowNoteSummary] = useState(false);

    // Filter logs that have notes
    const logsWithNotes = logs.filter(l => l.category === 'STOCK' && l.note && l.note.trim() !== '');

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 text-slate-600 text-[13px] uppercase font-black border-b border-slate-100">
                        <tr>
                            <th className="p-4 pl-6">Ngày</th>
                            <th className="p-4">Lệnh</th>
                            <th className="p-4">Chi tiết</th>
                            <th className="p-4 pr-6 text-right">
                                <span>Ghi chú</span>
                                <button
                                    onClick={() => setShowNoteSummary(true)}
                                    className="ml-2 px-2 py-1 text-[11px] font-bold text-emerald-600 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-all inline-flex items-center gap-1"
                                >
                                    <Eye size={12} />
                                    Xem
                                </button>
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                        {logs.filter(l => l.category === 'STOCK').map((log, i) => (
                            <tr key={i} className="text-[15px] hover:bg-slate-200 transition group">
                                <td className="p-4 pl-6 font-normal text-slate-700">{new Date(log.date).toLocaleDateString('vi-VN')}</td>
                                <td className={`p-4 font-normal ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-600'}`}>{log.type}</td>
                                <td className="p-4 font-normal text-slate-700">{log.content}</td>
                                <td className="p-4 pr-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <div className="relative group/note">
                                            <span className="text-[15px] text-slate-700 font-normal italic max-w-[150px] truncate cursor-help block">
                                                {log.note || "---"}
                                            </span>
                                            {log.note && (
                                                <div className="absolute top-1/2 right-full -translate-y-1/2 mr-3 w-64 p-5 bg-white rounded-[24px] shadow-2xl border border-slate-100 opacity-0 invisible group-hover/note:opacity-100 group-hover/note:visible transition-all duration-300 z-50 text-left pointer-events-none transform translate-x-2 group-hover/note:translate-x-0">
                                                    <div className="flex items-start gap-4">
                                                        <div className="mt-1 p-2 bg-blue-50 text-blue-600 rounded-xl">
                                                            <Book size={18} />
                                                        </div>
                                                        <div className="flex-1">
                                                            <h4 className="text-[13px] font-bold text-slate-800 uppercase tracking-tight mb-1">Ghi chú đầu tư</h4>
                                                            <p className="text-[14px] text-slate-600 font-medium leading-relaxed whitespace-pre-wrap">{log.note}</p>
                                                        </div>
                                                    </div>
                                                    {/* Arrow pointing right */}
                                                    <div className="absolute top-1/2 left-full -translate-y-1/2 border-8 border-transparent border-l-white"></div>
                                                </div>
                                            )}
                                        </div>
                                        <button onClick={() => { setEditingNote({ id: log.id, content: log.note }); setShowNoteModal(true); }} className="p-1.5 text-slate-500 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-all"><Book size={18} /></button>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* MODAL: Tổng hợp Ghi chú Đầu tư */}
            {showNoteSummary && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
                    <div className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden animate-in zoom-in-95 duration-300">
                        {/* Header */}
                        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 bg-emerald-50 rounded-xl">
                                    <Book size={20} className="text-emerald-600" />
                                </div>
                                <h3 className="text-lg font-bold text-slate-800 uppercase tracking-tight">Tổng hợp Ghi chú Đầu tư</h3>
                            </div>
                            <button
                                onClick={() => setShowNoteSummary(false)}
                                className="p-2 hover:bg-slate-100 rounded-xl transition-colors"
                            >
                                <X size={20} className="text-slate-400" />
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-6 overflow-y-auto max-h-[60vh]">
                            {logsWithNotes.length > 0 ? (
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 text-slate-500 text-[12px] uppercase font-bold border-b border-slate-100">
                                        <tr>
                                            <th className="p-3 pl-4 rounded-tl-xl">Ngày</th>
                                            <th className="p-3">Lệnh</th>
                                            <th className="p-3 pr-4 rounded-tr-xl">Ghi chú</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-50">
                                        {logsWithNotes.map((log, i) => (
                                            <tr key={i} className="hover:bg-slate-50 transition">
                                                <td className="p-3 pl-4 text-slate-700 text-[14px] whitespace-nowrap">
                                                    {new Date(log.date).toLocaleDateString('vi-VN')}
                                                </td>
                                                <td className={`p-3 text-[14px] whitespace-nowrap ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-600'}`}>
                                                    {log.type} {log.content.split(' ')[0]}
                                                </td>
                                                <td className="p-3 pr-4 text-slate-700 text-[14px] leading-relaxed">
                                                    {log.note}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="text-center py-12">
                                    <Book size={40} className="text-slate-200 mx-auto mb-4" />
                                    <p className="text-slate-400 text-sm">Chưa có ghi chú nào được lưu.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
