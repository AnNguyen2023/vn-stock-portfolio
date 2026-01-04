"use client";
import { Book, Calendar, Activity, List, Wallet, PieChart as PieChartIcon } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

export default function HistoryTabs({ 
  activeHistoryTab, setActiveHistoryTab, startDate, setStartDate, endDate, setEndDate, 
  handleCalculateProfit, data, PIE_COLORS, historicalProfit, navHistory, logs, 
  setEditingNote, setShowNoteModal 
}) {
  return (
    <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden relative z-10 mb-10">
      
      {/* 1. HEADER & BỘ LỌC NGÀY */}
      <div className="p-5 bg-white border-b border-slate-100 flex flex-col md:flex-row justify-between md:items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg"><Book size={22} /></div>
          <h2 className="text-slate-800 text-lg font-extrabold uppercase tracking-tight">Nhật Ký Dữ Liệu</h2>
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
          <button onClick={handleCalculateProfit} className="px-6 py-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-bold rounded-xl shadow-md active:scale-95 transition-all">Kiểm tra</button>
        </div>
      </div>

      {/* 2. THANH NAVIGATION TABS */}
      <div className="bg-white border-b border-slate-100 px-6 pt-4 flex gap-10 overflow-x-auto no-scrollbar">
        {[
          { id: 'allocation', label: 'Cơ cấu danh mục', icon: <PieChartIcon size={18}/> },
          { id: 'performance', label: 'Nhật ký Lãi/Lỗ', icon: <Activity size={18}/> },
          { id: 'orders', label: 'Nhật ký Khớp lệnh', icon: <List size={18}/> },
          { id: 'cashflow', label: 'Nhật ký Dòng tiền', icon: <Wallet size={18}/> }
        ].map((tab) => (
          <button key={tab.id} onClick={() => setActiveHistoryTab(tab.id)} className={`pb-3 text-sm font-bold border-b-2 transition-all whitespace-nowrap flex items-center gap-2 ${activeHistoryTab === tab.id ? 'border-emerald-600 text-slate-900' : 'border-transparent text-slate-400 hover:text-emerald-600'}`}>{tab.icon} {tab.label}</button>
        ))}
      </div>

      {/* 3. NỘI DUNG CHI TIẾT TỪNG TAB */}
      <div className="p-6 min-h-[450px] bg-slate-50/30">
        
        {/* TAB 1: CƠ CẤU DANH MỤC */}
        {activeHistoryTab === 'allocation' && (
          <div className="animate-in fade-in zoom-in duration-300 flex items-center justify-center relative h-[400px]">
            {(!data?.holdings || data.holdings.length === 0) ? <div className="text-slate-400 italic">Chưa có dữ liệu.</div> : (
              <div className="w-full h-full relative">
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-0">
                  <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mb-1">Giá trị cổ phiếu</p>
                  <p className="text-2xl font-black text-slate-800 tracking-tighter">{Math.floor(data?.total_stock_value || 0).toLocaleString('en-US')} <span className="text-xs font-bold text-slate-400 uppercase">vnd</span></p>
                </div>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart><Pie data={data.holdings} cx="50%" cy="50%" innerRadius={100} outerRadius={140} paddingAngle={3} dataKey="current_value" nameKey="ticker" label={({ name, percent }) => `${name} (${(percent * 100).toFixed(1)}%)`}>
                    {data.holdings.map((entry, index) => (<Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} stroke="#fff" strokeWidth={3} />))}
                  </Pie><Tooltip formatter={(val) => `${Math.floor(val).toLocaleString()} vnd`} /></PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: NHẬT KÝ LÃI/LỖ */}
        {activeHistoryTab === 'performance' && (
          <div className="animate-in fade-in zoom-in duration-500">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              <div className="lg:col-span-5 space-y-4">
                <h3 className="text-slate-700 text-[15px] font-bold uppercase tracking-wider border-l-4 border-emerald-500 pl-3">Lợi nhuận chốt sổ</h3>
                {!historicalProfit ? <div className="bg-white p-10 rounded-2xl border border-slate-100 flex flex-col items-center justify-center text-center shadow-sm min-h-[280px]"><Calendar size={32} className="text-slate-200 mb-4" /><p className="text-slate-500 text-sm">Chọn ngày và nhấn "Kiểm tra".</p></div> : (
                  <div className="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm min-h-[280px] flex flex-col justify-center">
                    <p className="text-[11px] text-emerald-600 font-bold uppercase mb-1 tracking-widest">Tổng lãi/lỗ ròng</p>
                    <p className={`text-3xl font-black tracking-tighter ${historicalProfit.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>{historicalProfit.total_profit >= 0 ? '+' : ''}{Math.floor(historicalProfit.total_profit).toLocaleString('en-US')} <span className="text-sm font-medium text-slate-400 ml-1.5">vnd</span></p>
                    <div className="mt-6 pt-4 border-t border-slate-50 flex justify-between items-center text-[12px]"><span className="text-slate-400 font-bold uppercase">Số lệnh đã chốt</span><span className="font-black text-slate-700">{historicalProfit.trade_count} lệnh</span></div>
                  </div>
                )}
              </div>
              <div className="lg:col-span-7 space-y-4">
                <h3 className="text-slate-700 text-[15px] font-bold uppercase tracking-wider border-l-4 border-blue-500 pl-3">NHẬT KÝ TÀI SẢN (NAV)</h3>
                <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden min-h-[280px]">
                  <div className="max-h-[280px] overflow-y-auto no-scrollbar">
                    {navHistory && navHistory.length > 0 ? (
                      <table className="w-full text-left">
                        <thead className="sticky top-0 bg-slate-50 text-slate-400 text-[10px] uppercase font-black border-b border-slate-100"><tr><th className="p-4 pl-6">Ngày</th><th className="p-4 text-right">Tổng tài sản</th><th className="p-4 text-right pr-6">Biến động</th></tr></thead>
                        <tbody className="divide-y divide-slate-50">{navHistory.map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/50 transition"><td className="p-4 pl-6 font-bold text-slate-600">{item.date}</td><td className="p-4 text-right font-black text-slate-800">{Math.floor(item.nav).toLocaleString()}</td><td className={`p-4 text-right pr-6 font-bold ${item.change >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>{item.change >= 0 ? '+' : ''}{item.pct.toFixed(2)}%</td></tr>
                        ))}</tbody>
                      </table>
                    ) : <div className="h-[280px] flex flex-col items-center justify-center gap-3"><Activity size={40} className="text-slate-100 animate-pulse" /><p className="text-slate-400 text-xs italic">Đang chờ dữ liệu Snapshot...</p></div>}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: NHẬT KÝ KHỚP LỆNH */}
        {activeHistoryTab === 'orders' && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-sm">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-slate-400 text-[10px] uppercase font-black border-b border-slate-100"><tr><th className="p-4 pl-6">Ngày</th><th className="p-4">Lệnh</th><th className="p-4">Chi tiết</th><th className="p-4 pr-6 text-right">Ghi chú</th></tr></thead>
                <tbody className="divide-y divide-slate-50">
                  {logs.filter(l => l.category === 'STOCK').map((log, i) => (
                    <tr key={i} className="text-sm hover:bg-slate-50 transition group">
                      <td className="p-4 pl-6 font-bold text-slate-500">{new Date(log.date).toLocaleDateString('vi-VN')}</td>
                      <td className={`p-4 font-black ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-500'}`}>{log.type}</td>
                      <td className="p-4 font-medium text-slate-700">{log.content}</td>
                      <td className="p-4 pr-6 text-right"><div className="flex items-center justify-end gap-2"><span className="text-[11px] text-slate-400 italic max-w-[150px] truncate">{log.note || "---"}</span>
                        <button onClick={() => { setEditingNote({id: log.id, content: log.note}); setShowNoteModal(true); }} className="p-1.5 text-slate-300 hover:text-blue-500 hover:bg-blue-50 rounded-lg transition-all"><Book size={14} /></button>
                      </div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: NHẬT KÝ DÒNG TIỀN */}
        {activeHistoryTab === 'cashflow' && (
          <div className="animate-in max-w-2xl mx-auto py-4 space-y-4">
            {logs.filter(l => l.category === 'CASH').map((log, idx) => {
              const isPos = ['DEPOSIT', 'INTEREST', 'DIVIDEND_CASH'].includes(log.type);
              return (
                <div key={idx} className="flex gap-5 items-start group">
                  <div className="min-w-[70px] text-right pt-2"><p className="text-xs font-black text-slate-400">{new Date(log.date).toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit'})}</p></div>
                  <div className="relative flex flex-col items-center self-stretch"><div className={`w-3.5 h-3.5 rounded-full mt-2.5 z-10 ring-4 ring-white ${isPos ? 'bg-emerald-500' : 'bg-purple-500'}`}></div><div className="w-0.5 bg-slate-100 flex-1 -mt-1"></div></div>
                  <div className={`flex-1 p-4 rounded-2xl border border-slate-100 shadow-sm transition ${isPos ? 'bg-emerald-50/30' : 'bg-purple-50/30'}`}><span className={`text-[10px] font-black px-2 py-0.5 rounded-md bg-white ${isPos ? 'text-emerald-600' : 'text-purple-600'}`}>{log.type}</span><p className="text-sm font-bold text-slate-700 mt-1">{log.content}</p></div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}