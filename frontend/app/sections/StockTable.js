"use client";
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { List, PlusCircle, MinusCircle, TrendingUp, TrendingDown, Minus, ArrowUpDown, ChevronDown } from 'lucide-react';
import StatusBadge from '../components/StatusBadge';
import StockTrendingCell from '../components/StockTrendingCell';

export default function StockTable({ data, buyForm, setBuyForm, setSellForm, setShowBuy, setShowSell }) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [isExpanded, setIsExpanded] = useState(false);
  const collapseTimeoutRef = useRef(null);

  // Auto-collapse after 10 minutes (600000ms)
  useEffect(() => {
    if (isExpanded) {
      // Clear any existing timeout
      if (collapseTimeoutRef.current) {
        clearTimeout(collapseTimeoutRef.current);
      }
      // Set new timeout for 10 minutes
      collapseTimeoutRef.current = setTimeout(() => {
        setIsExpanded(false);
      }, 600000); // 10 minutes
    }
    return () => {
      if (collapseTimeoutRef.current) {
        clearTimeout(collapseTimeoutRef.current);
      }
    };
  }, [isExpanded]);

  const sortedItems = useMemo(() => {
    let items = [...(data?.holdings || [])];
    if (sortConfig.key !== null) {
      items.sort((a, b) => {
        let aValue = a[sortConfig.key];
        let bValue = b[sortConfig.key];

        // Special handling for nested trending object
        if (sortConfig.key === 'trending') {
          aValue = a.trending?.change_pct ?? -Infinity;
          bValue = b.trending?.change_pct ?? -Infinity;
        }

        // Handle undefined/null
        if (aValue === undefined || aValue === null) aValue = -Infinity;
        if (bValue === undefined || bValue === null) bValue = -Infinity;

        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }
    return items;
  }, [data?.holdings, sortConfig]);

  const requestSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const SortIcon = ({ columnKey }) => {
    const isActive = sortConfig.key === columnKey;
    return (
      <ArrowUpDown
        size={14}
        className={`inline-block ml-1 transition-colors ${isActive ? 'text-emerald-500' : 'text-slate-500'}`}
      />
    );
  };
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-400 overflow-hidden mb-6">
      <div
        onMouseEnter={() => setIsExpanded(true)}
        className="p-5 border-b border-slate-300 flex justify-between items-center bg-white cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <List size={20} className="text-slate-600" />
            <h2 className="text-xl font-bold text-slate-600 uppercase tracking-tight">Danh mục cổ phiếu</h2>
          </div>
          <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-bold rounded-full">{data?.holdings?.length || 0} mã</span>
        </div>
        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowBuy(true)}
            className="px-4 py-2 bg-rose-500 text-white text-sm font-bold rounded-xl hover:bg-rose-600 transition-all shadow-sm active:scale-95"
          >
            Mua
          </button>
          <button
            onClick={() => setShowSell(true)}
            className="px-4 py-2 bg-purple-500 text-white text-sm font-bold rounded-xl hover:bg-purple-600 transition-all shadow-sm active:scale-95"
          >
            Bán
          </button>

          {/* Toggle Button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2.5 bg-emerald-500 hover:bg-emerald-600 rounded-xl transition-all shadow-md hover:shadow-lg"
            title={isExpanded ? 'Thu gọn' : 'Mở rộng'}
          >
            <ChevronDown
              size={22}
              className={`text-white transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Collapsible Content with Curtain Animation */}
      <div
        className={`overflow-hidden transition-all duration-500 ease-in-out ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
          }`}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50/50 text-slate-500 text-[13px] uppercase font-bold tracking-[0.12em] border-b border-slate-200">
              <tr>
                <th className="p-4 pl-6 cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('ticker')}>Mã CK <SortIcon columnKey="ticker" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('volume')}>SL <SortIcon columnKey="volume" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('avg_price')}>Giá TB <SortIcon columnKey="avg_price" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('current_price')}>Giá TT <SortIcon columnKey="current_price" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('current_value')}>Giá trị <SortIcon columnKey="current_value" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('profit_loss')}>Lãi/Lỗ <SortIcon columnKey="profit_loss" /></th>
                <th className="p-4 text-center w-32 cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('weight')}>Tỷ trọng <SortIcon columnKey="weight" /></th>
                <th className="p-4 text-center border-r border-slate-200 whitespace-nowrap cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('trending')}>
                  <div>Xu hướng <SortIcon columnKey="trending" /></div>
                  <div className="text-[10px] text-slate-800 font-normal">(5 phiên)</div>
                </th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('today_change_percent')}>Hôm nay <SortIcon columnKey="today_change_percent" /></th>
                <th className="p-4 text-center whitespace-nowrap">Thao tác</th>
              </tr>
            </thead>
            <tbody className="">
              {sortedItems.map((s) => {
                const isProfit = s.profit_loss >= 0;
                const allocation = data.total_stock_value > 0 ? (s.current_value / data.total_stock_value) * 100 : 0;

                // Unified 5-color theme logic
                const getTheme = () => {
                  const p = s.current_price;
                  const ref = s.ref_price;
                  const ceil = s.ceiling_price;
                  const floor = s.floor_price;

                  if (p >= ceil && ceil > 0) return {
                    text: "text-purple-500",
                    bg: "bg-purple-500",
                    badge: "text-purple-600 bg-purple-50"
                  };
                  if (p <= floor && floor > 0) return {
                    text: "text-cyan-400",
                    bg: "bg-cyan-400",
                    badge: "text-cyan-600 bg-cyan-50"
                  };
                  if (p > ref && ref > 0) return {
                    text: "text-emerald-500",
                    bg: "bg-emerald-500",
                    badge: "text-emerald-600 bg-emerald-50"
                  };
                  if (p < ref && ref > 0) return {
                    text: "text-rose-500",
                    bg: "bg-rose-500",
                    badge: "text-rose-600 bg-rose-50"
                  };
                  return {
                    text: "text-amber-500",
                    bg: "bg-amber-500",
                    badge: "text-amber-600 bg-amber-50"
                  };
                };

                const theme = getTheme();

                return (
                  <tr key={s.ticker} className="hover:bg-emerald-50 transition-colors group">
                    <td className="p-4 pl-6 relative border-r border-slate-200 last:border-r-0">
                      <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${theme.bg}`}></div>
                      <div>
                        <div className={`font-bold text-[15px] ${theme.text}`}>{s.ticker}</div>
                        <div className="text-[10px] text-slate-400 font-medium truncate max-w-[120px]">Công ty cổ phần {s.ticker}</div>
                      </div>
                    </td>
                    <td className="p-4 text-right font-bold text-slate-700 text-sm border-r border-slate-200 last:border-r-0">{s.volume.toLocaleString('en-US')}</td>
                    <td className="p-4 text-right text-sm font-medium text-slate-500 border-r border-slate-200 last:border-r-0">
                      <span className="tabular-nums">{(s.avg_price * 1000).toLocaleString('en-US')}</span>
                    </td>
                    <td className="p-4 text-right text-sm border-r border-slate-200 last:border-r-0">
                      <div className={`font-bold tabular-nums ${theme.text}`}>{(s.current_price * 1000).toLocaleString('en-US')}</div>
                    </td>
                    <td className="p-4 text-right text-sm font-bold text-slate-700 border-r border-slate-200 last:border-r-0">
                      {Math.floor(s.current_value).toLocaleString('en-US')}
                    </td>

                    <td className="p-4 text-center border-r border-slate-200 last:border-r-0">
                      <span className={`text-base font-medium ${isProfit ? 'text-emerald-600' : 'text-rose-500'}`}>
                        {Math.abs(Math.floor(s.profit_loss)).toLocaleString('en-US')}
                      </span>
                      <div className="flex items-center justify-center gap-2">
                        <StatusBadge value={s.profit_percent.toFixed(2)} showIcon={false} />
                      </div>
                    </td>
                    <td className="p-4 text-center border-r border-slate-200 last:border-r-0">
                      <div className="bg-slate-100 w-16 h-1.5 rounded-full mx-auto overflow-hidden"><div className="bg-orange-500 h-full transition-all duration-500" style={{ width: `${allocation}%` }}></div></div>
                      <span className="text-[15px] font-medium text-slate-600">{allocation.toFixed(1)}%</span>
                    </td>
                    <td className="p-4 text-center border-r border-slate-200 last:border-r-0">
                      <StockTrendingCell ticker={s.ticker} trending={s.trending} />
                    </td>
                    <td className="p-4 text-right border-r border-slate-200 last:border-r-0">
                      <div className={`inline-flex items-center gap-1 font-bold text-sm tabular-nums ${theme.badge} px-2.5 py-1 rounded-lg`}>
                        {s.today_change_percent > 0 ? <TrendingUp size={14} /> : s.today_change_percent < 0 ? <TrendingDown size={14} /> : <Minus size={14} />}
                        {s.today_change_percent > 0 ? "+" : ""}{s.today_change_percent.toFixed(2)}%
                      </div>
                    </td>

                    <td className="p-4">
                      <div className="flex justify-center gap-2">
                        <button onClick={() => { setBuyForm({ ...buyForm, ticker: s.ticker }); setShowBuy(true) }} className="p-2 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-all shadow-sm"><PlusCircle size={21} /></button>
                        <button onClick={() => { setSellForm({ ticker: s.ticker, volume: s.volume, price: '', available: s.available }); setShowSell(true) }} className="p-2 bg-rose-50 text-rose-500 rounded-lg hover:bg-rose-500 hover:text-white transition-all shadow-sm"><MinusCircle size={21} /></button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-white border-t border-slate-300">
              <tr>
                <td colSpan={5} className="p-5 pl-6 text-slate-700 text-[20px] font-medium tracking-wide">Tổng giá trị danh mục</td>
                <td colSpan={4} className="p-5 pr-6 text-right">
                  <div className="flex items-baseline justify-end gap-3">
                    <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full whitespace-nowrap">
                      Hiệu suất đầu tư: {data?.total_nav > 0 ? ((data.total_stock_value / data.total_nav) * 100).toFixed(2) : 0}%
                    </span>
                    <span className="text-xl font-bold text-slate-900 tracking-tight">{Math.floor(data?.total_stock_value || 0).toLocaleString('en-US')}</span>
                    <span className="text-base font-semibold text-slate-500 lowercase">vnd</span>
                  </div>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}