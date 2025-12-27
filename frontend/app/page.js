"use client";
import { useEffect, useState } from 'react';
import { 
  getPortfolio, depositMoney, withdrawMoney, 
  buyStock, sellStock, getAuditLog, 
  getHistorySummary, getPerformance 
} from '@/lib/api';
import { 
  Wallet, TrendingUp, PieChart, RefreshCw, PlusCircle, 
  ShoppingCart, MinusCircle, Book, History, Eye, 
  EyeOff, Calendar, ArrowRight, Activity
} from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Privacy States (Mặc định ẩn)
  const [showTimeline, setShowTimeline] = useState(false);
  const [showOrderHistory, setShowOrderHistory] = useState(false);

  // Historical Profit State
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [historicalProfit, setHistoricalProfit] = useState(null);

  // Modals Visibility
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [showBuy, setShowBuy] = useState(false);
  const [showSell, setShowSell] = useState(false);

  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [buyForm, setBuyForm] = useState({ ticker: '', volume: '', price: '', fee_rate: 0.0015 });
  const [sellForm, setSellForm] = useState({ ticker: '', volume: '', price: '', available: 0 });

  const fetchAllData = async () => {
    try {
      // Dùng từng await riêng lẻ để nếu 1 cái lỗi (như perf) thì 2 cái kia vẫn chạy
      const resP = await getPortfolio().catch(() => ({data: null}));
      const resL = await getAuditLog().catch(() => ({data: []}));
      const resEf = await getPerformance().catch(() => ({data: null}));
      
      if(resP.data) setData(resP.data);
      if(resL.data) setLogs(resL.data);
      if(resEf.data) setPerf(resEf.data);
    } catch (error) { console.error("Lỗi:", error); }
    setLoading(false);
  };

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCalculateProfit = async () => {
    if (!startDate || !endDate) return alert("Vui lòng chọn đủ ngày");
    const res = await getHistorySummary(startDate, endDate);
    setHistoricalProfit(res.data);
  };

  const closeModals = () => {
    setShowDeposit(false); setShowWithdraw(false); setShowBuy(false); setShowSell(false);
    setAmount(''); setDescription('');
    setBuyForm({ ticker: '', volume: '', price: '', fee_rate: 0.0015 });
  };

  if (loading && !data) return <div className="p-10 text-center font-sans text-purple-600 font-bold">VUI LÒNG ĐỢI...</div>;

  return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        
        {/* Header với màu nút Tím & Đỏ nhẹ */}
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-10">
          <h1 className="text-3xl font-black text-purple-900 italic">INVEST JOURNAL</h1>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => setShowDeposit(true)} className="bg-emerald-500 text-white px-6 py-2.5 rounded-2xl font-bold flex items-center gap-2 hover:bg-emerald-600 shadow-lg">
              <PlusCircle size={18}/> Nạp vốn
            </button>
            <button onClick={() => setShowWithdraw(true)} className="bg-purple-600 text-white px-6 py-2.5 rounded-2xl font-bold flex items-center gap-2 hover:bg-purple-700 shadow-lg shadow-purple-100">
              <MinusCircle size={18}/> Rút tiền
            </button>
            <button onClick={() => setShowBuy(true)} className="bg-rose-400 text-white px-6 py-2.5 rounded-2xl font-bold flex items-center gap-2 hover:bg-rose-500 shadow-lg">
              <PlusCircle size={18}/> Mua mới
            </button>
            <button onClick={fetchAllData} className="p-3 bg-white border border-purple-100 rounded-2xl text-purple-400 hover:text-purple-600 transition"><RefreshCw size={20}/></button>
          </div>
        </div>

        {/* Thẻ Tổng quan */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SummaryCard title="Vốn thực có (NAV)" value={Math.floor(data?.total_nav)} icon={<PieChart size={22}/>} color="text-purple-600" bg="bg-purple-50" />
          <SummaryCard title="Tiền mặt" value={Math.floor(data?.cash_balance)} icon={<Wallet size={22}/>} color="text-emerald-600" bg="bg-emerald-50" />
          <SummaryCard title="Giá trị cổ phiếu" value={Math.floor(data?.total_stock_value)} icon={<TrendingUp size={22}/>} color="text-fuchsia-600" bg="bg-fuchsia-50" />
        </div>

        {/* Bảng Hiệu suất (Giống hình bạn yêu cầu) */}
        <div className="mb-10 bg-[#222] rounded-[2rem] overflow-hidden shadow-2xl border border-slate-800">
         <div className="bg-[#333] p-4 text-center border-b border-white/10">
          <h2 className="text-slate-100 text-lg md:text-xl font-black tracking-tight flex items-center justify-center gap-2 uppercase">Hiệu suất đầu tư theo mốc thời gian 
            <span className="text-slate-400 text-sm italic">ⓘ</span>
          </h2>
        </div>
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-white/5">
            <PerfBox label="1 ngày" data={perf?.["1d"]} />
            <PerfBox label="1 tháng" data={perf?.["1m"]} />
            <PerfBox label="1 năm" data={perf?.["1y"]} />
            <PerfBox label="YTD" data={perf?.["ytd"]} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* CỘT TRÁI (1/4): TIMELINE (Privacy) */}
          <div className="lg:col-span-1 order-last lg:order-first">
            <div className="bg-white rounded-[2.5rem] shadow-xl border border-purple-100 overflow-hidden flex flex-col h-full min-h-[500px]">
              <div className="p-6 bg-purple-600 text-white flex justify-between items-center">
                <span className="font-black flex items-center gap-2"><Book size={18}/> Nhật ký Timeline</span>
                <button onClick={() => setShowTimeline(!showTimeline)} className="text-purple-200 hover:text-white transition">
                  {showTimeline ? <EyeOff size={20}/> : <Eye size={20}/>}
                </button>
              </div>
              <div className="p-6 space-y-6 overflow-y-auto bg-slate-50/50 flex-1">
                {showTimeline ? (
                  logs.map((log, idx) => (
                    <div key={idx} className="relative pl-6 border-l-2 border-purple-100 pb-2">
                      <div className={`absolute -left-[9px] top-1 w-4 h-4 rounded-full border-4 border-white ${log.category === 'CASH' ? 'bg-emerald-400' : 'bg-purple-400'}`}></div>
                      <p className="text-[10px] text-slate-400 font-bold mb-1">{new Date(log.date).toLocaleString('vi-VN')}</p>
                      <div className="bg-white p-3 rounded-2xl border border-slate-100 shadow-sm">
                        <p className="text-xs font-black text-slate-800 mb-1">{log.type}</p>
                        <p className="text-[10px] text-slate-500 leading-relaxed">{log.content}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center h-full opacity-30 text-slate-400 italic text-xs">
                    <EyeOff size={40} className="mb-2"/> Dữ liệu nhật ký đã ẩn
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* CỘT PHẢI (3/4): DANH MỤC & LỊCH SỬ KHỚP LỆNH */}
          <div className="lg:col-span-3 space-y-10">
            
            {/* 1. Danh mục hiện tại (Xanh lá hơn một chút) */}
            <div className="bg-white rounded-[2.5rem] shadow-xl border border-emerald-200 overflow-hidden">
              <div className="p-6 bg-emerald-100/60 border-b border-emerald-200 flex justify-between items-center">
                <h2 className="font-black text-emerald-900 flex items-center gap-3 text-lg"><TrendingUp size={20}/> Danh mục hiện tại</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-emerald-50/50 text-emerald-600 text-[10px] uppercase font-bold tracking-widest">
                    <tr>
                      <th className="p-5">Mã CK</th>
                      <th className="p-5 text-right">Khối lượng</th>
                      <th className="p-5 text-right">Giá vốn</th>
                      <th className="p-5 text-right">Thị giá</th>
                      <th className="p-5 text-right">Lãi / Lỗ</th>
                      <th className="p-5 text-right">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-emerald-100">
                    {data?.holdings.map((s) => (
                      <tr key={s.ticker} className="hover:bg-emerald-50/40 transition">
                        <td className="p-5 font-black text-purple-700">{s.ticker}</td>
                        <td className="p-5 text-right font-bold text-slate-600">{s.volume.toLocaleString()}</td>
                        <td className="p-5 text-right text-slate-400 font-mono text-sm">{s.avg_price.toLocaleString()}</td>
                        <td className="p-5 text-right font-bold text-slate-800 font-mono">{s.current_price.toLocaleString()}</td>
                        <td className={`p-5 text-right font-black ${s.profit_loss >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                          {s.profit_loss >= 0 ? '▲' : '▼'} {Math.abs(Math.floor(s.profit_loss)).toLocaleString()}
                        </td>
                        <td className="p-5 text-right flex justify-end gap-2">
                           <button onClick={() => {setBuyForm({...buyForm, ticker: s.ticker}); setShowBuy(true)}} className="p-2 bg-emerald-50 text-emerald-600 rounded-xl hover:bg-emerald-600 hover:text-white transition"><PlusCircle size={14}/></button>
                           <button onClick={() => {setSellForm({ticker: s.ticker, volume: s.available, price: '', available: s.available}); setShowSell(true)}} className="p-2 bg-rose-50 text-rose-500 rounded-xl hover:bg-rose-500 hover:text-white transition"><MinusCircle size={14}/></button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 2. Tra cứu lãi lỗ giai đoạn */}
            <div className="bg-white rounded-[2.5rem] p-8 shadow-xl border border-purple-100">
              <h2 className="font-black text-slate-700 mb-6 flex items-center gap-3"><Calendar size={20}/> Tra cứu hiệu suất lịch sử</h2>
              <div className="flex flex-wrap gap-4 items-end">
                <div className="flex-1 min-w-[150px]">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-2 block">Từ ngày</label>
                  <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-full p-3 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-purple-400 outline-none font-bold" />
                </div>
                <div className="flex-1 min-w-[150px]">
                  <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-2 block">Đến ngày</label>
                  <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-full p-3 bg-slate-50 border-none rounded-2xl focus:ring-2 focus:ring-purple-400 outline-none font-bold" />
                </div>
                <button onClick={handleCalculateProfit} className="bg-purple-600 text-white px-8 py-3 rounded-2xl font-black hover:bg-purple-700 transition">KIỂM TRA</button>
              </div>
              {historicalProfit && (
                <div className="mt-8 p-6 bg-purple-50 rounded-[2rem] border border-purple-100 flex justify-between items-center">
                  <div>
                    <p className="text-[10px] text-purple-400 font-black uppercase mb-2 tracking-widest">Lãi lỗ ròng thực nhận</p>
                    <p className={`text-3xl font-black ${historicalProfit.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {historicalProfit.total_profit >= 0 ? '+' : ''}{Math.floor(historicalProfit.total_profit).toLocaleString()} <span className="text-sm font-normal italic lowercase">vnd</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-purple-400 font-bold uppercase mb-1">Số thương vụ</p>
                    <p className="text-xl font-black text-purple-900">{historicalProfit.trade_count}</p>
                  </div>
                </div>
              )}
            </div>

            {/* 3. Lịch sử khớp lệnh (Xanh lá đậm hơn - Privacy) */}
            <div className="bg-white rounded-[2.5rem] shadow-xl border border-emerald-300/40 overflow-hidden">
              <div className="p-6 bg-emerald-200/50 border-b border-emerald-300 flex justify-between items-center">
                <h2 className="font-black text-emerald-900 flex items-center gap-3 text-lg"><History size={20}/> Lịch sử khớp lệnh</h2>
                <button onClick={() => setShowOrderHistory(!showOrderHistory)} className="text-emerald-700 hover:text-emerald-900 transition">
                  {showOrderHistory ? <EyeOff size={20}/> : <Eye size={20}/>}
                </button>
              </div>
              <div className="max-h-[400px] overflow-y-auto bg-emerald-50/20">
                {showOrderHistory ? (
                  <table className="w-full text-left">
                    <tbody className="divide-y divide-emerald-100">
                      {logs.filter(l => l.category === 'STOCK').map((log, i) => (
                        <tr key={i} className="text-xs hover:bg-white transition">
                          <td className="p-4 font-bold text-slate-400">{new Date(log.date).toLocaleDateString('vi-VN')}</td>
                          <td className={`p-4 font-black ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-500'}`}>{log.type}</td>
                          <td className="p-4 text-slate-600 font-medium italic">{log.content}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="p-20 text-center text-emerald-300 italic text-xs">Dữ liệu khớp lệnh đã ẩn</div>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>

      {/* --- CỬA SỔ (MODALS) --- */}
      
      {(showDeposit || showWithdraw) && (
        <div className="fixed inset-0 bg-purple-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-md">
          <div className="bg-white rounded-[3rem] p-10 w-full max-w-md shadow-2xl border border-purple-100">
            <h2 className={`text-2xl font-black mb-8 ${showDeposit ? 'text-emerald-600' : 'text-purple-600'} uppercase`}>
              {showDeposit ? 'Nạp vốn' : 'Rút vốn'}
            </h2>
            <form onSubmit={showDeposit ? handleDeposit : handleWithdraw} className="space-y-6">
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Số tiền</label>
                <input type="number" required autoFocus className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-purple-100 outline-none text-xl font-black" 
                  value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0" />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 ml-1">Ghi chú</label>
                <input type="text" className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-purple-100 outline-none text-sm font-bold" 
                  value={description} onChange={(e) => setDescription(e.target.value)} placeholder="..." />
              </div>
              <div className="flex gap-4 pt-4">
                <button type="button" onClick={closeModals} className="flex-1 py-4 text-slate-400 font-black">Hủy</button>
                <button type="submit" className={`flex-1 py-4 text-white font-black rounded-2xl shadow-xl ${showDeposit ? 'bg-emerald-500' : 'bg-purple-600'}`}>XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showBuy && (
        <div className="fixed inset-0 bg-purple-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-md">
          <div className="bg-white rounded-[3rem] p-10 w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-black mb-8 text-rose-400 uppercase tracking-tighter">MUA CỔ PHIẾU</h2>
            <form onSubmit={handleBuy} className="space-y-5">
              <div className="grid grid-cols-2 gap-5">
                <div className="col-span-2">
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-2 ml-1">Mã CK</label>
                  <input type="text" required className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-rose-100 outline-none font-black text-2xl text-rose-500 uppercase" 
                    value={buyForm.ticker} onChange={(e) => setBuyForm({...buyForm, ticker: e.target.value.toUpperCase()})} />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-2 ml-1">Khối lượng</label>
                  <input type="number" required className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-rose-100 outline-none font-black" 
                    value={buyForm.volume} onChange={(e) => setBuyForm({...buyForm, volume: e.target.value})} />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-2 ml-1">Giá Khớp</label>
                  <input type="number" step="0.01" required className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-rose-100 outline-none font-black" 
                    value={buyForm.price} onChange={(e) => setBuyForm({...buyForm, price: e.target.value})} />
                </div>
              </div>
              <div className="flex gap-4 pt-6">
                <button type="button" onClick={closeModals} className="flex-1 py-4 text-slate-400 font-black">Hủy</button>
                <button type="submit" className="flex-1 py-4 bg-rose-400 text-white font-black rounded-2xl">XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showSell && (
        <div className="fixed inset-0 bg-purple-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-md">
          <div className="bg-white rounded-[3rem] p-10 w-full max-w-md shadow-2xl border border-rose-100">
            <h2 className="text-2xl font-black mb-8 text-rose-600 uppercase tracking-tighter">BÁN CỔ PHIẾU</h2>
            <form onSubmit={handleSell} className="space-y-5">
              <div className="p-6 bg-rose-50 rounded-[2rem] border border-rose-100 flex justify-between items-center">
                <p className="text-3xl font-black text-rose-700 uppercase">{sellForm.ticker}</p>
                <p className="text-xl font-black text-rose-700 italic">Khả dụng: {sellForm.available}</p>
              </div>
              <div className="grid grid-cols-2 gap-5">
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-2 ml-1">Số lượng Bán</label>
                  <input type="number" required max={sellForm.available} className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-rose-100 outline-none font-black" 
                    value={sellForm.volume} onChange={(e) => setSellForm({...sellForm, volume: e.target.value})} />
                </div>
                <div>
                  <label className="block text-[10px] font-black text-slate-400 uppercase mb-2 ml-1">Giá Bán</label>
                  <input type="number" step="0.01" required className="w-full p-4 bg-slate-50 border-none rounded-2xl focus:ring-4 focus:ring-rose-100 outline-none font-black" 
                    value={sellForm.price} onChange={(e) => setSellForm({...sellForm, price: e.target.value})} />
                </div>
              </div>
              <div className="flex gap-4 pt-6">
                <button type="button" onClick={closeModals} className="flex-1 py-4 text-slate-400 font-black">Hủy</button>
                <button type="submit" className="flex-1 py-4 bg-rose-600 text-white font-black rounded-2xl">XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

function SummaryCard({ title, value, icon, color, bg }) {
  return (
    <div className="p-6 rounded-[2.5rem] border border-white bg-white/60 backdrop-blur-sm shadow-xl shadow-purple-900/5 flex items-center gap-6 transition hover:-translate-y-1 duration-300">
      <div className={`p-5 rounded-[1.5rem] ${bg} ${color} shadow-inner`}>{icon}</div>
      <div>
        <p className="text-slate-400 text-[10px] font-black uppercase tracking-[0.25em] mb-1">{title}</p>
        <h3 className="text-2xl font-black text-slate-800 tracking-tight">
          {value?.toLocaleString()} <span className="text-[10px] font-bold text-slate-300 ml-1 italic lowercase">vnd</span>
        </h3>
      </div>
    </div>
  );
}

function PerfBox({ label, data }) {
  const isProfit = (data?.val || 0) >= 0;
  // Làm màu chữ sáng rực hơn trên nền đen
  const colorClass = isProfit ? "text-emerald-400" : "text-rose-400";
  
  return (
    <div className="p-6 text-center bg-[#252525] hover:bg-[#2a2a2a] transition border-r border-white/5 last:border-r-0">
      <p className="text-slate-500 text-[11px] uppercase font-black mb-4 tracking-[0.2em]">{label}</p>
      {/* Tăng kích thước số tiền lên text-xl */}
      <p className={`text-xl md:text-2xl font-black tracking-tighter ${colorClass}`}>
        {isProfit ? '+' : ''}{Math.floor(data?.val || 0).toLocaleString()}
      </p>
      {/* Tăng kích thước phần trăm lên text-sm */}
      <p className={`text-sm font-bold ${colorClass} mt-2 opacity-90`}>
        ({isProfit ? '+' : ''}{data?.pct?.toFixed(2)}%)
      </p>
    </div>
  );
}