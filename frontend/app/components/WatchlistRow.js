"use client";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { useState, useEffect } from "react";
import TrendingIcon from "./TrendingIcon";

export default function WatchlistRow({ item, onRemove, isSelected, onToggle }) {
    const [trending, setTrending] = useState({ trend: "sideways", change_pct: 0 });

    useEffect(() => {
        // Fetch trending data
        fetch(`http://localhost:8000/trending/${item.ticker}`)
            .then(res => res.json())
            .then(data => setTrending(data))
            .catch(() => setTrending({ trend: "sideways", change_pct: 0 }));
    }, [item.ticker]);

    const isPositive = item.change_pct > 0;
    const isNegative = item.change_pct < 0;

    // Format numbers
    const formatPrice = (p) => new Intl.NumberFormat("vi-VN").format(p);
    const formatCompact = (val) => {
        if (!val || isNaN(val)) return "0";
        // Ưu tiên hiển thị cực gọn: Nghìn tỷ (T) nếu số quá lớn
        if (val >= 1e12) return (val / 1e12).toFixed(1) + "T";
        if (val >= 1e9) return (val / 1e9).toFixed(1) + "T";
        if (val >= 1e6) return (val / 1e6).toFixed(1) + "M";
        return val.toLocaleString();
    };

    // Unified 5-color theme logic
    const getTheme = () => {
        const p = item.price;
        const ref = item.ref_price;
        const ceil = item.ceiling_price;
        const floor = item.floor_price;

        if (p >= ceil && ceil > 0) return {
            text: "text-purple-500",
            bg: "bg-purple-500",
            badge: "text-purple-600 bg-purple-50",
            sparkline: "#a855f7"
        };
        if (p <= floor && floor > 0) return {
            text: "text-cyan-400",
            bg: "bg-cyan-400",
            badge: "text-cyan-600 bg-cyan-50",
            sparkline: "#22d3ee"
        };
        if (p > ref && ref > 0) return {
            text: "text-emerald-500",
            bg: "bg-emerald-500",
            badge: "text-emerald-600 bg-emerald-50",
            sparkline: "#10b981"
        };
        if (p < ref && ref > 0) return {
            text: "text-rose-500",
            bg: "bg-rose-500",
            badge: "text-rose-600 bg-rose-50",
            sparkline: "#f43f5e"
        };
        return {
            text: "text-amber-500",
            bg: "bg-amber-500",
            badge: "text-amber-600 bg-amber-50",
            sparkline: "#f59e0b"
        };
    };

    const theme = getTheme();

    return (
        <tr className={`border-b border-slate-50 hover:bg-emerald-50 transition-colors group ${isSelected ? 'bg-orange-50/30' : ''}`}>
            <td className="p-4 pl-6 text-center">
                <div
                    onClick={onToggle}
                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center cursor-pointer transition-all ${isSelected
                        ? "bg-orange-500 border-orange-500"
                        : "bg-white border-slate-200"
                        }`}
                >
                    {isSelected && (
                        <div className="w-2 h-2 bg-white rounded-full" />
                    )}
                </div>
            </td>
            <td className="p-4 relative">
                <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${theme.bg}`}></div>
                <div>
                    <div className={`font-bold text-[15px] ${theme.text}`}>{item.ticker}</div>
                    <div className="text-[10px] text-slate-400 font-medium truncate max-w-[100px]">{item.organ_name}</div>
                </div>
            </td>

            <td className="p-4 text-right">
                <span className={`text-sm font-bold tabular-nums ${theme.text}`}>
                    {formatPrice(item.price)}
                </span>
            </td>

            <td className="p-4 text-right">
                <div className={`inline-flex items-center gap-1 font-bold text-sm tabular-nums ${theme.badge} px-2.5 py-1 rounded-lg`}>
                    {item.price > item.ref_price ? <TrendingUp size={14} /> : item.price < item.ref_price ? <TrendingDown size={14} /> : <Minus size={14} />}
                    {item.change_pct > 0 ? "+" : ""}{item.change_pct.toFixed(2)}%
                </div>
            </td>

            <td className="p-4 text-center">
                <TrendingIcon trend={trending.trend} changePct={trending.change_pct} size={26} />
            </td>

            <td className="p-4 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.pb ? item.pb.toFixed(2) : "-"}
            </td>

            <td className="p-4 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.roe ? item.roe.toFixed(3) + "%" : "-"}
            </td>

            <td className="p-4 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.roa ? item.roa.toFixed(3) + "%" : "-"}
            </td>

            <td className="p-4 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.pe ? item.pe.toFixed(2) : "-"}
            </td>

            <td className="p-4 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                    onClick={() => onRemove(item.ticker)}
                    className="p-2 text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                    title="Xóa khỏi danh sách"
                >
                    <Minus size={16} />
                </button>
            </td>
        </tr>
    );
}
