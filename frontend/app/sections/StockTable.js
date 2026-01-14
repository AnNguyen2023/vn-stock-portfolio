"use client";
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { List, TrendingUp, TrendingDown, Minus, PlusCircle, MinusCircle, ChevronDown, ArrowUpDown } from 'lucide-react';
import StatusBadge from '../components/StatusBadge';
import StockTrendingCell from '../components/StockTrendingCell';
import StockTableRow from '../components/StockTableRow';

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
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowBuy(true)}
            className="bg-rose-400 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 hover:bg-rose-500 shadow-md shadow-rose-100 active:scale-95 transition-all text-sm"
          >
            <PlusCircle size={16} /> Mua
          </button>
          <button
            onClick={() => setShowSell(true)}
            className="bg-purple-500 text-white px-4 py-2 rounded-xl font-bold flex items-center gap-2 hover:bg-purple-600 shadow-md shadow-purple-100 active:scale-95 transition-all text-sm"
          >
            <MinusCircle size={16} /> Bán
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
                <th className="p-4 pl-6 cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('ticker')}>
                  <div className="flex items-center justify-center gap-1">
                    Mã CK <SortIcon columnKey="ticker" />
                  </div>
                </th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('volume')}>SL <SortIcon columnKey="volume" /></th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('avg_price')}>Giá TB <SortIcon columnKey="avg_price" /></th>
                <th className="p-4 text-center cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('current_price')}>
                  <div className="flex items-center justify-center gap-1">
                    Giá TT <SortIcon columnKey="current_price" />
                  </div>
                </th>
                <th className="p-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('current_value')}>Giá trị <SortIcon columnKey="current_value" /></th>
                <th className="py-4 pl-0 pr-2 w-[8%] text-center cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('profit_loss')}>
                  <div className="flex items-center justify-center gap-1">
                    Lãi/Lỗ <SortIcon columnKey="profit_loss" />
                  </div>
                </th>
                <th className="p-4 text-center w-32 cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('weight')}>Tỷ trọng <SortIcon columnKey="weight" /></th>
                <th className="p-4 text-center border-r border-slate-200 whitespace-nowrap cursor-pointer bg-amber-100/60 hover:bg-amber-100/80 transition-colors" onClick={() => requestSort('trending')}>
                  <div className="flex items-center justify-center gap-1 text-[13px] font-bold">
                    XU HƯỚNG (5 PHIÊN) <SortIcon columnKey="trending" />
                  </div>
                </th>
                <th className="p-4 text-center cursor-pointer hover:bg-emerald-100 transition-colors border-r border-slate-200 whitespace-nowrap" onClick={() => requestSort('today_change_percent')}>
                  <div className="flex items-center justify-center gap-1">
                    Hôm nay <SortIcon columnKey="today_change_percent" />
                  </div>
                </th>
                <th className="p-4 text-center whitespace-nowrap">Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((s) => (
                <StockTableRow
                  key={s.ticker}
                  stock={s}
                  totalStockValue={data?.total_stock_value || 1}
                  setBuyForm={setBuyForm}
                  setShowBuy={setShowBuy}
                  setSellForm={setSellForm}
                  setShowSell={setShowSell}
                />
              ))}
            </tbody>
            <tfoot className="bg-white border-t border-slate-300">
              <tr>
                <td colSpan={5} className="p-5 pl-6 text-slate-700 text-[20px] font-medium tracking-wide">Tổng giá trị danh mục</td>
                <td className="p-5 text-right">
                  <span className="text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full whitespace-nowrap">
                    ({data?.total_nav > 0 ? ((data.total_stock_value / data.total_nav) * 100).toFixed(2) : 0}% NAV)
                  </span>
                </td>
                <td colSpan={3} className="p-5 pr-6 text-right">
                  <div className="flex items-baseline justify-end gap-1.5">
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