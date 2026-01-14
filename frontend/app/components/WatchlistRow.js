"use client";
import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import TrendingIcon from "./TrendingIcon";

export default function WatchlistRow({ item, onRemove, isSelected, onToggle }) {
    const [priceFlash, setPriceFlash] = useState(false);
    const [changeFlash, setChangeFlash] = useState(false);
    const [prevPrice, setPrevPrice] = useState(item.price);
    const [prevChange, setPrevChange] = useState(item.change_pct);

    // Trigger flash animation when values change
    useEffect(() => {
        if (item.price !== prevPrice) {
            setPriceFlash(true);
            setPrevPrice(item.price);
            setTimeout(() => setPriceFlash(false), 600);
        }
        if (item.change_pct !== prevChange) {
            setChangeFlash(true);
            setPrevChange(item.change_pct);
            setTimeout(() => setChangeFlash(false), 600);
        }
    }, [item.price, item.change_pct, prevPrice, prevChange]);

    // Priority: use item.trending from batch API, fallback to sideways default
    const trending = item.trending || { trend: "sideways", change_pct: 0 };

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

        if (p >= ceil && ceil > 0) {
            return {
                text: "text-purple-500",
                bg: "bg-purple-500",
                priceColor: "text-purple-600",
                badgeClass: "bg-purple-100 text-purple-700",
                icon: <TrendingUp size={14} />
            };
        }
        if (p <= floor && floor > 0) {
            return {
                text: "text-cyan-400",
                bg: "bg-cyan-400",
                priceColor: "text-cyan-600",
                badgeClass: "bg-cyan-100 text-cyan-700",
                icon: <TrendingDown size={14} />
            };
        }
        if (p > ref && ref > 0) {
            return {
                text: "text-emerald-500",
                bg: "bg-emerald-500",
                priceColor: "text-emerald-600",
                badgeClass: "bg-emerald-100 text-emerald-700",
                icon: <TrendingUp size={14} />
            };
        }
        if (p < ref && ref > 0) {
            return {
                text: "text-rose-500",
                bg: "bg-rose-500",
                priceColor: "text-rose-600",
                badgeClass: "bg-rose-100 text-rose-700",
                icon: <TrendingDown size={14} />
            };
        }
        return {
            text: "text-amber-500",
            bg: "bg-amber-500",
            priceColor: "text-amber-600",
            badgeClass: "bg-amber-100 text-amber-700",
            icon: <Minus size={14} />
        };
    };


    const theme = getTheme();

    return (
        <tr className={`border-b border-slate-50 hover:bg-emerald-50 transition-all duration-500 ease-in-out group ${isSelected ? 'bg-orange-50/30' : ''}`}>
            <td className="p-3 pl-5 text-center">
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
            <td className="p-3 relative">
                <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${theme.bg}`}></div>
                <div>
                    <div className={`font-medium text-[13px] ${theme.text}`}>{item.ticker}</div>
                    <div className="text-[10px] text-slate-400 font-medium truncate max-w-[100px]">{item.organ_name}</div>
                </div>
            </td>

            <td className="p-3 text-right">
                <span className={`text-[13px] font-medium tabular-nums ${theme.priceColor} transition-all duration-300 ${priceFlash ? 'bg-emerald-100 scale-105 px-1 rounded' : ''}`}>
                    {item.price?.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </span>
            </td>

            <td className="p-3 text-right">
                <div className={`inline-flex items-center gap-1 px-2 py-1 rounded-md font-medium text-[13px] tabular-nums ${theme.badgeClass} transition-all duration-300 ${changeFlash ? 'ring-2 ring-emerald-400 scale-105' : ''}`}>
                    {theme.icon}
                    {item.change_pct >= 0 ? '+' : ''}{item.change_pct?.toFixed(2)}%
                </div>
            </td>

            <td className="p-3 text-center bg-amber-100/40 w-20">
                <TrendingIcon trend={trending.trend} changePct={trending.change_pct} size={22} />
            </td>

            <td className="p-3 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.pb ? item.pb.toFixed(2) : "-"}
            </td>

            <td className="p-3 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.roe ? item.roe.toFixed(3) + "%" : "-"}
            </td>

            <td className="p-3 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.roa ? item.roa.toFixed(3) + "%" : "-"}
            </td>

            <td className="p-3 text-right font-medium text-slate-600 text-sm tabular-nums">
                {item.pe ? item.pe.toFixed(2) : "-"}
            </td>

            <td className="p-3 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                    onClick={() => onRemove(item.ticker, item.watchlist_ticker_id)}
                    className="p-2 text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
                    title="Xóa khỏi danh sách"
                >
                    <Minus size={16} />
                </button>
            </td>
        </tr>
    );
}
