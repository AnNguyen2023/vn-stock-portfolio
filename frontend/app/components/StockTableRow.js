"use client";
import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, PlusCircle, MinusCircle } from 'lucide-react';
import StockTrendingCell from './StockTrendingCell';
import StatusBadge from './StatusBadge';

export default function StockTableRow({ stock, totalStockValue, setBuyForm, setShowBuy, setSellForm, setShowSell }) {
    const [priceFlash, setPriceFlash] = useState(false);
    const [changeFlash, setChangeFlash] = useState(false);
    const [prevPrice, setPrevPrice] = useState(stock.current_price);
    const [prevChange, setPrevChange] = useState(stock.today_change_percent);

    // Trigger flash animation when values change
    useEffect(() => {
        if (stock.current_price !== prevPrice) {
            setPriceFlash(true);
            setPrevPrice(stock.current_price);
            setTimeout(() => setPriceFlash(false), 600);
        }
        if (stock.today_change_percent !== prevChange) {
            setChangeFlash(true);
            setPrevChange(stock.today_change_percent);
            setTimeout(() => setChangeFlash(false), 600);
        }
    }, [stock.current_price, stock.today_change_percent, prevPrice, prevChange]);

    const getTheme = () => {
        const price = stock.current_price;
        const ref = stock.ref_price;
        const ceiling = stock.ceiling_price;
        const floor = stock.floor_price;

        // 5-color theme logic matching WatchlistRow
        if (price >= ceiling && ceiling > 0) {
            return {
                text: "text-purple-500",
                bg: "bg-purple-500",
                priceColor: "text-purple-600",
                badgeClass: "bg-purple-100 text-purple-700",
                icon: <TrendingUp size={14} />
            };
        }
        if (price <= floor && floor > 0) {
            return {
                text: "text-cyan-400",
                bg: "bg-cyan-400",
                priceColor: "text-cyan-600",
                badgeClass: "bg-cyan-100 text-cyan-700",
                icon: <TrendingDown size={14} />
            };
        }
        if (price > ref && ref > 0) {
            return {
                text: "text-emerald-500",
                bg: "bg-emerald-500",
                priceColor: "text-emerald-600",
                badgeClass: "bg-emerald-100 text-emerald-700",
                icon: <TrendingUp size={14} />
            };
        }
        if (price < ref && ref > 0) {
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
    const allocation = totalStockValue > 0 ? ((stock.current_value / totalStockValue) * 100) : 0;

    return (
        <tr key={stock.ticker} className="hover:bg-emerald-50 transition-all duration-500 ease-in-out group">
            <td className="p-3 pl-5 relative border-r border-slate-200 last:border-r-0">
                <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${theme.bg}`}></div>
                <div>
                    <div className={`font-medium text-[13px] ${theme.text}`}>{stock.ticker}</div>
                    <div className="text-[10px] text-slate-400 font-medium truncate max-w-[120px]">Công ty cổ phần {stock.ticker}</div>
                </div>
            </td>
            <td className="p-3 text-right font-medium text-slate-700 text-sm border-r border-slate-200 last:border-r-0">{stock.volume.toLocaleString('en-US')}</td>
            <td className="p-3 text-right text-sm font-medium text-slate-500 border-r border-slate-200 last:border-r-0">
                <span className="tabular-nums">{stock.avg_price.toLocaleString('en-US')}</span>
            </td>
            <td className="p-3 text-center text-sm border-r border-slate-200 last:border-r-0">
                <div className={`font-medium tabular-nums ${theme.priceColor} transition-all duration-300 ${priceFlash ? 'bg-emerald-100 scale-105 px-1 rounded' : ''}`}>{stock.current_price.toLocaleString('en-US')}</div>
            </td>
            <td className="p-3 text-right text-sm font-medium text-slate-700 border-r border-slate-200 last:border-r-0">
                {Math.floor(stock.current_value).toLocaleString('en-US')}
            </td>
            <td className="p-3 text-right text-sm font-medium text-slate-700 border-r border-slate-200 last:border-r-0">
                {Math.floor(stock.profit_loss).toLocaleString('en-US')}
            </td>
            <td className="p-3 text-center border-r border-slate-200 last:border-r-0">
                <div className="bg-slate-100 w-16 h-1.5 rounded-full mx-auto overflow-hidden"><div className="bg-orange-500 h-full transition-all duration-500" style={{ width: `${allocation}%` }}></div></div>
                <span className="text-[15px] font-medium text-slate-600">{allocation.toFixed(1)}%</span>
            </td>
            <td className="p-3 text-center border-r border-slate-200 last:border-r-0 bg-amber-100/40 w-20">
                <StockTrendingCell ticker={stock.ticker} trending={stock.trending} />
            </td>
            <td className="p-3 text-right border-r border-slate-200 last:border-r-0">
                <div className={`transition-all duration-300 ${changeFlash ? 'ring-2 ring-emerald-400 scale-105' : ''}`}>
                    <StatusBadge value={stock.today_change_percent} />
                </div>
            </td>
            <td className="p-3 text-center">
                <div className="flex justify-center gap-2">
                    <button
                        onClick={() => {
                            setBuyForm({ ...setBuyForm, ticker: stock.ticker });
                            setShowBuy(true);
                        }}
                        className="p-2 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-all shadow-sm"
                    >
                        <PlusCircle size={21} />
                    </button>
                    <button
                        onClick={() => {
                            setSellForm({ ticker: stock.ticker, volume: stock.volume });
                            setShowSell(true);
                        }}
                        className="p-2 bg-rose-50 text-rose-500 rounded-lg hover:bg-rose-500 hover:text-white transition-all shadow-sm"
                    >
                        <MinusCircle size={21} />
                    </button>
                </div>
            </td>
        </tr>
    );
}
