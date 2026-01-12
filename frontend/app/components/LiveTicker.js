"use client";
import React, { useState, useEffect, useRef } from 'react';
import { getVpsLive } from '../../lib/api';
import { Edit3, Check, X } from 'lucide-react';

const DEFAULT_SYMBOLS = "FPT,HAG,VCI,MBB,STB,FUEVFVND,MBS,BAF,DXG,SHB";

export default function LiveTicker() {
    const [symbols, setSymbols] = useState(DEFAULT_SYMBOLS);
    const [prices, setPrices] = useState({});
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [editValue, setEditValue] = useState("");
    const intervalRef = useRef(null);

    // Initialize from localStorage
    useEffect(() => {
        const saved = localStorage.getItem('ticker_symbols');
        if (saved) {
            setSymbols(saved);
        }
    }, []);

    const fetchPrices = async (currentSymbols) => {
        try {
            const response = await getVpsLive(currentSymbols || symbols);
            if (response.data) {
                setPrices(response.data);
            }
        } catch (error) {
            console.error('Error fetching VPS live prices:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPrices(symbols);
        if (intervalRef.current) clearInterval(intervalRef.current);
        intervalRef.current = setInterval(() => fetchPrices(symbols), 15000);
        return () => clearInterval(intervalRef.current);
    }, [symbols]);

    const handleSave = () => {
        const sanitized = editValue.toUpperCase().replace(/\s/g, '');
        setSymbols(sanitized);
        localStorage.setItem('ticker_symbols', sanitized);
        setIsEditing(false);
    };

    if (loading && Object.keys(prices).length === 0) {
        return (
            <div className="h-10 bg-slate-50 border border-slate-200 flex items-center px-4 overflow-hidden rounded-xl shadow-sm">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest animate-pulse">
                    Đang kết nối VPS Live Board...
                </span>
            </div>
        );
    }

    const tickerItems = symbols.split(',').map(symbol => {
        const data = prices[symbol];
        if (!data) return null;

        const change = data.price - data.ref;
        const changePct = data.ref > 0 ? (change / data.ref) * 100 : 0;
        const isUp = change > 0;
        const isDown = change < 0;
        const isCeiling = data.price === data.ceiling && data.price > 0;
        const isFloor = data.price === data.floor && data.price > 0;

        let colorClass = "text-yellow-600";
        if (isCeiling) colorClass = "text-fuchsia-600";
        else if (isFloor) colorClass = "text-cyan-600";
        else if (isUp) colorClass = "text-emerald-600";
        else if (isDown) colorClass = "text-rose-600";

        return (
            <div key={symbol} className="flex items-center gap-2 px-6 border-r border-slate-100 whitespace-nowrap group hover:bg-slate-100/50 transition-colors h-full">
                <span className="text-[11px] font-black text-slate-800 group-hover:scale-110 transition-transform">{symbol}</span>
                <span className={`text-[11px] font-bold tabular-nums ${colorClass}`}>
                    {(data.price / 1000).toLocaleString('en-US', { minimumFractionDigits: 1 })}
                </span>
                <span className={`text-[10px] font-bold tabular-nums flex items-center gap-0.5 ${colorClass}`}>
                    {change > 0 ? '▲' : change < 0 ? '▼' : '■'} {Math.abs(changePct).toFixed(1)}%
                </span>
            </div>
        );
    });

    return (
        <div className="h-10 bg-slate-50 border border-slate-200 flex items-center overflow-hidden rounded-xl shadow-sm group relative">
            <div className="bg-emerald-500 text-white text-[9px] font-black px-2.5 h-full flex items-center z-10 shadow-md">LIVE</div>

            <div className="flex-1 overflow-hidden relative h-full flex items-center">
                {!isEditing ? (
                    <div className="flex animate-infinite-scroll group-hover:pause">
                        {tickerItems}
                        {tickerItems}
                    </div>
                ) : (
                    <div className="absolute inset-0 bg-white/95 z-20 flex items-center px-4 gap-2 animate-in fade-in slide-in-from-left-2 duration-200">
                        <input
                            autoFocus
                            className="flex-1 bg-slate-100 border border-slate-200 rounded-lg px-3 py-1 text-xs font-bold text-slate-800 outline-none focus:border-emerald-500 transition-colors"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                            placeholder="Nhập mã CP (VD: FPT,HAG,VCI...)"
                        />
                        <button onClick={handleSave} className="p-1.5 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors">
                            <Check size={14} strokeWidth={3} />
                        </button>
                        <button onClick={() => setIsEditing(false)} className="p-1.5 bg-slate-200 text-slate-600 rounded-lg hover:bg-slate-300 transition-colors">
                            <X size={14} strokeWidth={3} />
                        </button>
                    </div>
                )}
            </div>

            {/* Edit Button */}
            {!isEditing && (
                <button
                    onClick={() => {
                        setEditValue(symbols);
                        setIsEditing(true);
                    }}
                    className="absolute right-0 top-0 bottom-0 px-3 bg-slate-50/80 backdrop-blur-sm border-l border-slate-100 text-slate-400 hover:text-emerald-500 hover:bg-white transition-all z-10 opacity-0 group-hover:opacity-100"
                    title="Chỉnh sửa danh sách"
                >
                    <Edit3 size={14} />
                </button>
            )}

            <style jsx>{`
                @keyframes infinite-scroll {
                    from { transform: translateX(0); }
                    to { transform: translateX(-50%); }
                }
                .animate-infinite-scroll {
                    display: flex;
                    width: max-content;
                    animation: infinite-scroll 50s linear infinite;
                }
                .pause {
                    animation-play-state: paused;
                }
            `}</style>
        </div>
    );
}
