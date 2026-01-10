"use client";
import React from 'react';

export default function CashFlowLog({ logs }) {
    return (
        <div className="animate-in max-w-2xl mx-auto py-4 space-y-4">
            {logs.filter(l => l.category === 'CASH').map((log, idx) => {
                const isPos = ['DEPOSIT', 'INTEREST', 'DIVIDEND_CASH'].includes(log.type);
                return (
                    <div key={idx} className="flex gap-5 items-start group">
                        <div className="min-w-[70px] text-right pt-2"><p className="text-xs font-black text-slate-400">{new Date(log.date).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })}</p></div>
                        <div className="relative flex flex-col items-center self-stretch"><div className={`w-3.5 h-3.5 rounded-full mt-2.5 z-10 ring-4 ring-white ${isPos ? 'bg-emerald-500' : 'bg-purple-500'}`}></div><div className="w-0.5 bg-slate-100 flex-1 -mt-1"></div></div>
                        <div className={`flex-1 p-4 rounded-2xl border border-slate-100 shadow-sm transition ${isPos ? 'bg-emerald-50/30' : 'bg-purple-50/30'}`}><span className={`text-[11px] font-normal px-2 py-0.5 rounded-md bg-white ${isPos ? 'text-emerald-600' : 'text-purple-600'}`}>{log.type}</span><p className="text-[15px] font-normal text-slate-700 mt-1">{log.content}</p></div>
                    </div>
                );
            })}
        </div>
    );
}
