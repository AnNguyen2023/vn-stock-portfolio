"use client";
import { TrendingUp, TrendingDown, Minus, PlusCircle, MinusCircle } from 'lucide-react';
import StockTrendingCell from './StockTrendingCell';
import StatusBadge from './StatusBadge';
import { useFlashAnimation } from '../hooks/useFlashAnimation';
import { getStockTheme } from '../utils/stockTheme';

export default function StockTableRow({ stock, totalStockValue, setBuyForm, setShowBuy, setSellForm, setShowSell }) {
    const priceFlash = useFlashAnimation(stock.current_price);
    const changeFlash = useFlashAnimation(stock.today_change_percent);


    const theme = getStockTheme(stock.current_price, stock.ref_price, stock.ceiling_price, stock.floor_price);
    const allocation = totalStockValue > 0 ? ((stock.current_value / totalStockValue) * 100) : 0;

    return (
        <tr key={stock.ticker} className="hover:bg-emerald-50 transition-all duration-500 ease-in-out group">
            <td className="p-3 pl-5 relative border-r border-slate-200 last:border-r-0">
                <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${theme.bg}`}></div>
                <div className="flex flex-col items-center">
                    <div className={`font-medium text-[15px] ${theme.text}`}>{stock.ticker}</div>
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
            <td className="py-3 pl-0 pr-2 text-right border-r border-slate-200 last:border-r-0">
                <div className={`text-sm font-bold ${stock.profit_loss >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {stock.profit_loss >= 0 ? '+' : ''}{Math.floor(stock.profit_loss).toLocaleString('en-US')}
                </div>
                <div className={`text-[12px] font-bold ${stock.profit_percent >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                    ({stock.profit_percent >= 0 ? '+' : ''}{stock.profit_percent.toFixed(2)}%)
                </div>
            </td>
            <td className="p-3 text-center border-r border-slate-200 last:border-r-0">
                <div className="bg-slate-100 w-16 h-1.5 rounded-full mx-auto overflow-hidden"><div className="bg-orange-500 h-full transition-all duration-500" style={{ width: `${allocation}%` }}></div></div>
                <span className="text-[15px] font-medium text-slate-600">{allocation.toFixed(1)}%</span>
            </td>
            <td className="p-3 text-center border-r border-slate-200 last:border-r-0 bg-amber-100/40 w-20">
                <StockTrendingCell ticker={stock.ticker} trending={stock.trending} />
            </td>
            <td className={`p-3 text-center border-r border-slate-200 last:border-r-0 ${stock.current_price >= stock.ceiling_price && stock.ceiling_price > 0 ? 'bg-purple-100' : ''}`}>
                <div className={`inline-flex items-center gap-1 transition-all duration-300 ${changeFlash ? 'ring-2 ring-emerald-400 scale-105' : ''}`}>
                    <span className={theme.priceColor}>{theme.icon}</span>
                    <span className={`font-bold tabular-nums ${theme.priceColor} ${stock.current_price >= stock.ceiling_price && stock.ceiling_price > 0 ? 'text-base' : 'text-sm'}`}>
                        {stock.today_change_percent >= 0 ? '+' : ''}{stock.today_change_percent.toFixed(2)}%
                    </span>
                </div>
            </td>
            <td className="p-3 text-center">
                <div className="flex justify-center gap-2">
                    <button
                        onClick={() => {
                            setBuyForm({ ...setBuyForm, ticker: stock.ticker });
                            setShowBuy(true);
                        }}
                        className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-all shadow-sm"
                    >
                        <PlusCircle size={18} />
                    </button>
                    <button
                        onClick={() => {
                            setSellForm({ ticker: stock.ticker, volume: stock.volume });
                            setShowSell(true);
                        }}
                        className="p-1.5 bg-rose-50 text-rose-500 rounded-lg hover:bg-rose-500 hover:text-white transition-all shadow-sm"
                    >
                        <MinusCircle size={18} />
                    </button>
                </div>
            </td>
        </tr>
    );
}
