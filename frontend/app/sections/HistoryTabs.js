"use client";
import React, { useState, useEffect, useRef } from 'react';
import { Book, Calendar, Activity, List, Wallet, PieChart as PieChartIcon, ChevronDown } from 'lucide-react';
import PortfolioAllocation from '../components/history/PortfolioAllocation';
import RealizedProfit from '../components/history/RealizedProfit';
import OrderLog from '../components/history/OrderLog';
import CashFlowLog from '../components/history/CashFlowLog';

export default function HistoryTabs({
  activeHistoryTab, setActiveHistoryTab, startDate, setStartDate, endDate, setEndDate,
  handleCalculateProfit, data, PIE_COLORS, historicalProfit, navHistory, logs,
  setEditingNote, setShowNoteModal
}) {
  const [isHistoryExpanded, setIsHistoryExpanded] = useState(false);
  const collapseTimeoutRef = useRef(null);

  // Auto-collapse after 10 minutes
  useEffect(() => {
    if (isHistoryExpanded) {
      if (collapseTimeoutRef.current) {
        clearTimeout(collapseTimeoutRef.current);
      }
      collapseTimeoutRef.current = setTimeout(() => {
        setIsHistoryExpanded(false);
      }, 600000); // 10 minutes
    }
    return () => {
      if (collapseTimeoutRef.current) {
        clearTimeout(collapseTimeoutRef.current);
      }
    };
  }, [isHistoryExpanded]);

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-slate-400 overflow-hidden relative z-10 mb-6">

      {/* 1. HEADER & BỘ LỌC NGÀY */}
      <div
        onMouseEnter={() => setIsHistoryExpanded(true)}
        className="p-5 bg-white border-b border-slate-300 flex flex-col md:flex-row justify-between md:items-center gap-4 cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Book size={20} className="text-slate-600" />
            <h2 className="text-[17px] font-medium text-slate-600 uppercase tracking-tight">Nhật Ký Dữ Liệu</h2>
          </div>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold focus:ring-2 focus:ring-emerald-500 outline-none text-slate-700 shadow-sm cursor-pointer" />
          </div>
          <span className="text-slate-300 font-bold self-center">−</span>
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm font-bold focus:ring-2 focus:ring-emerald-500 outline-none text-slate-700 shadow-sm cursor-pointer" />
          </div>
          <button onClick={handleCalculateProfit} className="px-6 py-2 bg-purple-500 hover:bg-purple-600 text-white text-sm font-bold rounded-xl shadow-md active:scale-95 transition-all">Kiểm tra</button>
          {/* Toggle Button */}
          <button
            onClick={() => setIsHistoryExpanded(!isHistoryExpanded)}
            className="p-2.5 bg-emerald-500 hover:bg-emerald-600 rounded-xl transition-all shadow-md hover:shadow-lg"
            title={isHistoryExpanded ? 'Thu gọn' : 'Mở rộng'}
          >
            <ChevronDown
              size={22}
              className={`text-white transition-transform duration-300 ${isHistoryExpanded ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Collapsible Content with Curtain Animation */}
      <div
        className={`overflow-hidden transition-all duration-500 ease-in-out ${isHistoryExpanded ? 'max-h-[3000px] opacity-100' : 'max-h-0 opacity-0'}`}
      >
        {/* 2. THANH NAVIGATION TABS */}
        <div className="bg-white border-b border-slate-100 px-6 pt-4 flex gap-10 overflow-x-auto no-scrollbar">
          {[
            { id: 'allocation', label: 'Cơ cấu danh mục', icon: <PieChartIcon size={18} /> },
            { id: 'performance', label: 'Nhật ký Lãi/Lỗ', icon: <Activity size={18} /> },
            { id: 'orders', label: 'Nhật ký Khớp lệnh', icon: <List size={18} /> },
            { id: 'cashflow', label: 'Nhật ký Dòng tiền', icon: <Wallet size={18} /> }
          ].map((tab) => (
            <button key={tab.id} onClick={() => setActiveHistoryTab(tab.id)} className={`pb-3 px-3 py-2 text-base font-medium border-b-2 transition-all whitespace-nowrap flex items-center gap-2 hover:bg-emerald-50 rounded-t-lg ${activeHistoryTab === tab.id ? 'border-emerald-600 text-slate-900 bg-emerald-50/50' : 'border-transparent text-slate-600 hover:text-emerald-600'}`}>{tab.icon} {tab.label}</button>
          ))}
        </div>

        {/* 3. NỘI DUNG CHI TIẾT TỪNG TAB */}
        <div className="p-6 min-h-[450px] bg-slate-50/30">

          {/* TAB 1: CƠ CẤU DANH MỤC */}
          {activeHistoryTab === 'allocation' && (
            <PortfolioAllocation data={data} PIE_COLORS={PIE_COLORS} />
          )}

          {/* TAB 2: NHẬT KÝ LÃI/LỖ */}
          {activeHistoryTab === 'performance' && (
            <RealizedProfit historicalProfit={historicalProfit} navHistory={navHistory} />
          )}

          {/* TAB 3: NHẬT KÝ KHỚP LỆNH */}
          {activeHistoryTab === 'orders' && (
            <OrderLog logs={logs} setEditingNote={setEditingNote} setShowNoteModal={setShowNoteModal} />
          )}

          {/* TAB 4: NHẬT KÝ DÒNG TIỀN */}
          {activeHistoryTab === 'cashflow' && (
            <CashFlowLog logs={logs} />
          )}
        </div>
      </div>
    </div>
  );
}