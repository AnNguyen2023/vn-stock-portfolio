"use client";
import { useEffect, useState } from 'react';
import { 
  getPortfolio, depositMoney, withdrawMoney, 
  buyStock, sellStock, getAuditLog, 
  getHistorySummary, getPerformance 
} from '@/lib/api';
import { 
  Wallet, TrendingUp, PieChart, RefreshCw, PlusCircle, 
  MinusCircle, Book, History, Eye, 
  EyeOff, Calendar, Activity, List
} from 'lucide-react';

import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';

// Dữ liệu giả lập: Tỷ suất lợi nhuận (%) so với mốc ban đầu (0%)
const CHART_DATA = [
  { date: '01/12', portfolio: 0, vnindex: 0, ssi: 0 },
  { date: '05/12', portfolio: 2.5, vnindex: 1.2, ssi: -1.5 }, // SSI giảm
  { date: '10/12', portfolio: 4.8, vnindex: 3.5, ssi: 2.0 },  // SSI hồi phục
  { date: '15/12', portfolio: 3.2, vnindex: 0.5, ssi: 4.5 },  // SSI tăng mạnh
  { date: '20/12', portfolio: 5.5, vnindex: 2.1, ssi: 8.0 },  // SSI vượt trội
  { date: '25/12', portfolio: 7.2, vnindex: 4.0, ssi: 6.5 },
  { date: '28/12', portfolio: 8.5, vnindex: 3.8, ssi: 5.0 },
];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Privacy States
  const [showTimeline, setShowTimeline] = useState(false);

  // History Tab State
  const [activeHistoryTab, setActiveHistoryTab] = useState('performance'); // 'performance' | 'orders' | 'cashflow'
  
  // Date Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [historicalProfit, setHistoricalProfit] = useState(null);

  // Modals Visibility
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [showBuy, setShowBuy] = useState(false);
  const [showSell, setShowSell] = useState(false);

  // Forms
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [buyForm, setBuyForm] = useState({ ticker: '', volume: '', price: '', fee_rate: 0.0015 });
  const [sellForm, setSellForm] = useState({ ticker: '', volume: '', price: '', available: 0 });

  const fetchAllData = async () => {
    try {
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

  // Tự động điền ghi chú tùy theo là Nạp hay Rút
  useEffect(() => {
    const today = new Date().toLocaleDateString('vi-VN'); // Ngày hiện tại

    if (showDeposit) {
      setDescription(`Nạp tiền tk ${today} `); // Nếu là Nạp
    } else if (showWithdraw) {
      setDescription(`Rút tiền tk ${today} `); // Nếu là Rút <--- THÊM DÒNG NÀY
    } else {
      // Khi đóng modal thì reset trắng
      setDescription('');
      setAmount(''); 
    }
  }, [showDeposit, showWithdraw]);

  // 2. Hàm nhập tiền: Tự thêm dấu phẩy (100,000)
  const handleAmountChange = (e) => {
    const rawValue = e.target.value.replace(/[^0-9]/g, ''); // Xóa chữ, chỉ lấy số
    if (!rawValue) {
      setAmount('');
      return;
    }
    // Format kiểu Mỹ để có dấu phẩy: 100,000
    const formatted = new Intl.NumberFormat('en-US').format(rawValue);
    setAmount(formatted);
  };
  // ---------------------

  const handleCalculateProfit = async () => {
    if (!startDate || !endDate) return alert("Vui lòng chọn đủ ngày");
    const res = await getHistorySummary(startDate, endDate);
    setHistoricalProfit(res.data);
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    if (!amount) return;
    // SỬA DÒNG DƯỚI: Xóa dấu phẩy trước khi gửi
    const realAmount = parseFloat(amount.replace(/,/g, '')); 
    await depositMoney({ amount: realAmount, description });
    closeModals(); fetchAllData();
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    if (!amount) return;
    
    // QUAN TRỌNG: Xóa dấu phẩy (100,000 -> 100000) trước khi gửi
    const realAmount = parseFloat(amount.replace(/,/g, ''));
    
    await withdrawMoney({ amount: realAmount, description });
    closeModals(); 
    fetchAllData();
  };

  const handleBuy = async (e) => {
    e.preventDefault();
    await buyStock({ ...buyForm, volume: parseInt(buyForm.volume), price: parseFloat(buyForm.price) });
    closeModals(); fetchAllData();
  };

  const handleSell = async (e) => {
    e.preventDefault();
    await sellStock({ ...sellForm, volume: parseInt(sellForm.volume), price: parseFloat(sellForm.price) });
    closeModals(); fetchAllData();
  };

  const closeModals = () => {
    setShowDeposit(false); setShowWithdraw(false); setShowBuy(false); setShowSell(false);
    setAmount(''); setDescription('');
    setBuyForm({ ticker: '', volume: '', price: '', fee_rate: 0.0015 });
  };

  if (loading && !data) return <div className="p-10 text-center font-sans text-emerald-600 font-medium">ĐANG TẢI DỮ LIỆU...</div>;

  return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-10">
          <h1 className="text-3xl font-black text-emerald-900 italic">INVEST JOURNAL</h1>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => setShowDeposit(true)} className="bg-emerald-500 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-emerald-600 shadow-md active:scale-95 transition">
              <PlusCircle size={18}/> Nạp vốn
            </button>
            <button onClick={() => setShowWithdraw(true)} className="bg-purple-600 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-purple-700 shadow-md shadow-purple-100 active:scale-95 transition">
              <MinusCircle size={18}/> Rút tiền
            </button>
            <button onClick={() => setShowBuy(true)} className="bg-rose-400 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-rose-500 shadow-md active:scale-95 transition">
              <PlusCircle size={18}/> Mua mới
            </button>
            <button onClick={fetchAllData} className="p-2.5 bg-white border border-emerald-100 rounded-lg text-emerald-500 hover:text-emerald-700 transition shadow-sm"><RefreshCw size={20}/></button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SummaryCard title="Vốn thực có (NAV)" value={Math.floor(data?.total_nav)} icon={<PieChart size={22}/>} color="text-purple-600" bg="bg-purple-50" />
          <SummaryCard title="Tiền mặt" value={Math.floor(data?.cash_balance)} icon={<Wallet size={22}/>} color="text-emerald-600" bg="bg-emerald-50" />
          <SummaryCard title="Giá trị cổ phiếu" value={Math.floor(data?.total_stock_value)} icon={<TrendingUp size={22}/>} color="text-fuchsia-600" bg="bg-fuchsia-50" />
        </div>

        {/* Bảng Hiệu suất Realtime - Style Emerald & Font Medium */}
        <div className="mb-10 bg-white rounded-xl overflow-hidden shadow-xl border border-emerald-100">
         <div className="p-4 bg-emerald-50/50 border-b border-emerald-100 flex justify-between items-center text-center">
          <h2 className="w-full text-emerald-900 text-lg font-medium tracking-tight flex items-center justify-center gap-2 uppercase">
            Hiệu suất đầu tư theo mốc thời gian 
            <span className="text-emerald-400 text-sm italic lowercase font-normal">ⓘ</span>
          </h2>
        </div>
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-emerald-50">
            <PerfBox label="1 ngày" data={perf?.["1d"]} />
            <PerfBox label="1 tháng" data={perf?.["1m"]} />
            <PerfBox label="1 năm" data={perf?.["1y"]} />
            <PerfBox label="YTD" data={perf?.["ytd"]} />
          </div>
        </div>

        <div className="space-y-10">
        
        {/* --- BIỂU ĐỒ SO SÁNH 3 CHỈ SỐ --- */}
        <div className="mb-10 bg-white rounded-xl shadow-xl border border-emerald-100 overflow-hidden">
          <div className="p-4 bg-emerald-50/50 border-b border-emerald-100 flex flex-col md:flex-row justify-between md:items-center gap-3">
             <h2 className="text-emerald-900 text-lg font-medium tracking-tight flex items-center gap-2 uppercase">
                <TrendingUp size={20} className="text-emerald-600"/> So sánh Tăng trưởng (%)
             </h2>
             
             {/* Bộ lọc so sánh */}
             <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase">So sánh với:</span>
                <select className="bg-white border border-emerald-200 text-xs rounded-md px-3 py-1.5 outline-none text-slate-700 font-bold shadow-sm">
                   <option value="VNINDEX">VN-Index (Thị trường)</option>
                </select>
                <span className="text-slate-300 font-bold">+</span>
                <select className="bg-white border border-orange-200 text-xs rounded-md px-3 py-1.5 outline-none text-orange-600 font-bold shadow-sm">
                   <option value="SSI">SSI</option>
                   <option value="FPT">FPT</option>
                   <option value="HPG">HPG</option>
                </select>
             </div>
          </div>

          <div className="p-6 h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={CHART_DATA} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                
                <XAxis 
                  dataKey="date" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#64748b', fontSize: 11, fontWeight: 500}} 
                  dy={10}
                />
                
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: '#64748b', fontSize: 11}} 
                  tickFormatter={(val) => `${val}%`} 
                />
                
                <Tooltip 
                  contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'}}
                  itemStyle={{paddingBottom: 4, fontWeight: 600}}
                  formatter={(value) => [`${value}%`]}
                />
                
                <Legend wrapperStyle={{paddingTop: '20px', fontSize: '12px', fontWeight: 600}} iconType="circle" />

                {/* 1. VN-INDEX (Màu Xám - Benchmark) */}
                <Line 
                  type="monotone" 
                  dataKey="vnindex" 
                  name="VN-Index" 
                  stroke="#94a3b8" 
                  strokeWidth={2} 
                  dot={false} 
                  activeDot={{r: 6}}
                  strokeDasharray="5 5" // Nét đứt để biểu thị đây là mốc tham chiếu
                />

                {/* 2. CỔ PHIẾU RIÊNG (Màu Cam - SSI) */}
                <Line 
                  type="monotone" 
                  dataKey="ssi" 
                  name="SSI" 
                  stroke="#f97316" // Màu cam đậm
                  strokeWidth={2} 
                  dot={{r: 4, fill: '#f97316', strokeWidth: 0}} 
                  activeDot={{r: 6}} 
                />

                {/* 3. DANH MỤC CỦA TÔI (Màu Xanh Emerald - Quan trọng nhất) */}
                <Line 
                  type="monotone" 
                  dataKey="portfolio" 
                  name="Danh mục của tôi" 
                  stroke="#10b981" 
                  strokeWidth={4} // Dày nhất để nổi bật
                  dot={{r: 5, stroke: '#fff', strokeWidth: 2, fill: '#10b981'}} 
                  activeDot={{r: 8, stroke: '#d1fae5', strokeWidth: 4}} 
                />
              
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
          
          {/* 1. Danh mục hiện tại */}
          <div className="bg-white rounded-xl shadow-xl border border-emerald-100 overflow-hidden">
            <div className="p-4 bg-emerald-50/50 border-b border-emerald-100 flex justify-between items-center">
              <h2 className="text-emerald-900 text-lg font-medium tracking-tight flex items-center gap-2 uppercase">
                <TrendingUp size={20} className="text-emerald-600"/> Danh mục hiện tại
              </h2>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-white text-slate-400 text-[11px] uppercase font-semibold tracking-widest whitespace-nowrap border-b border-emerald-50">
                  <tr>
                    <th className="p-4 text-emerald-600">Mã CK</th>
                    <th className="p-4 text-right">Khối lượng</th>
                    <th className="p-4 text-right">Giá vốn</th>
                    <th className="p-4 text-right">Giá TT</th>
                    <th className="p-4 text-right">Tổng Vốn</th>
                    <th className="p-4 text-right">Giá trị TT</th>
                    <th className="p-4 text-right">Lãi / Lỗ</th>
                    <th className="p-4 text-right">% Lãi/Lỗ</th>
                    <th className="p-4 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {data?.holdings.map((s) => {
                    const totalCost = s.current_value - s.profit_loss;
                    const numClass = "p-4 text-right font-medium text-slate-700 text-sm"; // Class chuẩn hóa
                    return (
                      <tr key={s.ticker} className="hover:bg-emerald-50/30 transition">
                        <td className="p-4 font-bold text-slate-700 text-sm">{s.ticker}</td>
                        <td className={numClass}>{s.volume.toLocaleString()}</td>
                        <td className={numClass}>{s.avg_price.toLocaleString()}</td>
                        <td className={numClass}>{s.current_price.toLocaleString()}</td>
                        <td className={numClass}>{Math.floor(totalCost).toLocaleString()}</td>
                        <td className={numClass}>{Math.floor(s.current_value).toLocaleString()}</td>

                        <td className={`p-4 text-right font-medium text-sm ${s.profit_loss >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                          {s.profit_loss >= 0 ? '+' : ''}{Math.floor(s.profit_loss).toLocaleString()}
                        </td>
                        <td className={`p-4 text-right font-medium text-sm ${s.profit_percent >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                           {s.profit_percent > 0 ? '+' : ''}{s.profit_percent.toFixed(2)}%
                        </td>

                        <td className="p-4 text-right flex justify-end gap-2">
                            <button onClick={() => {setBuyForm({...buyForm, ticker: s.ticker}); setShowBuy(true)}} className="p-1.5 bg-emerald-50 text-emerald-600 rounded-md hover:bg-emerald-600 hover:text-white transition"><PlusCircle size={16}/></button>
                            <button onClick={() => {setSellForm({ticker: s.ticker, volume: s.volume, price: '', available: s.volume}); setShowSell(true)}} className="p-1.5 bg-rose-50 text-rose-500 rounded-md hover:bg-rose-500 hover:text-white transition"><MinusCircle size={16}/></button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 2. Trung tâm Dữ liệu (History Tabs) */}
          <div className="bg-white rounded-xl shadow-xl border border-emerald-100 overflow-hidden">
              
              <div className="p-4 bg-emerald-50/50 border-b border-emerald-100 flex flex-col md:flex-row justify-between md:items-center gap-4">
                  <h2 className="text-emerald-900 text-lg font-medium tracking-tight flex items-center gap-2 uppercase">
                      <History size={20} className="text-emerald-600"/> Trung tâm Dữ liệu
                  </h2>
                  
                  <div className="flex flex-wrap gap-2 items-center">
                        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} 
                          className="bg-white border border-emerald-100 rounded-md p-1.5 text-xs font-medium text-slate-700 focus:ring-2 focus:ring-emerald-200 outline-none uppercase" />
                        <span className="text-slate-300 font-bold">-</span>
                        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} 
                          className="bg-white border border-emerald-100 rounded-md p-1.5 text-xs font-medium text-slate-700 focus:ring-2 focus:ring-emerald-200 outline-none uppercase" />
                        
                        <button onClick={handleCalculateProfit} className="bg-emerald-600 text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-emerald-700 transition shadow-sm">
                          KIỂM TRA
                        </button>
                  </div>
              </div>

              <div className="bg-white border-b border-emerald-50 px-4 pt-4">
                  <div className="flex gap-8 overflow-x-auto">
                      <button onClick={() => setActiveHistoryTab('performance')} 
                          className={`pb-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${activeHistoryTab === 'performance' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-400 hover:text-slate-600'}`}>
                          <span className="flex items-center gap-2"><Activity size={16}/> Hiệu suất Lãi/Lỗ</span>
                      </button>
                      <button onClick={() => setActiveHistoryTab('orders')} 
                          className={`pb-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${activeHistoryTab === 'orders' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-400 hover:text-slate-600'}`}>
                          <span className="flex items-center gap-2"><List size={16}/> Nhật ký Khớp lệnh</span>
                      </button>
                      <button onClick={() => setActiveHistoryTab('cashflow')} 
                          className={`pb-3 text-sm font-medium border-b-2 transition whitespace-nowrap ${activeHistoryTab === 'cashflow' ? 'border-emerald-600 text-emerald-700' : 'border-transparent text-slate-400 hover:text-slate-600'}`}>
                          <span className="flex items-center gap-2"><Wallet size={16}/> Nhật ký Dòng tiền</span>
                      </button>
                  </div>
              </div>

              <div className="p-6 min-h-[400px] bg-slate-50/30">
                  
                  {/* TAB 1: HIỆU SUẤT */}
                  {activeHistoryTab === 'performance' && (
                      <div className="animate-in fade-in zoom-in duration-300">
                            {!historicalProfit ? (
                              <div className="text-center text-slate-400 italic mt-10">Vui lòng chọn ngày và bấm "Kiểm tra".</div>
                            ) : (
                              <div className="bg-gradient-to-br from-white to-emerald-50 p-8 rounded-xl border border-emerald-100 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
                                  <div>
                                      <p className="text-[10px] text-emerald-600 font-semibold uppercase mb-2 tracking-widest">Tổng Lãi/Lỗ Ròng</p>
                                      <p className={`text-4xl font-bold tracking-tighter ${historicalProfit.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                      {historicalProfit.total_profit >= 0 ? '+' : ''}{Math.floor(historicalProfit.total_profit).toLocaleString()} <span className="text-lg font-bold text-slate-400">₫</span>
                                      </p>
                                  </div>
                                  <div className="bg-white p-4 rounded-lg border border-emerald-100 text-center min-w-[120px]">
                                      <p className="text-[10px] text-slate-400 font-semibold uppercase mb-1">Số lệnh</p>
                                      <p className="text-2xl font-bold text-emerald-900">{historicalProfit.trade_count}</p>
                                  </div>
                              </div>
                            )}
                      </div>
                  )}

                  {/* TAB 2: KHỚP LỆNH */}
                  {activeHistoryTab === 'orders' && (
                      <div className="animate-in fade-in zoom-in duration-300">
                          <div className="overflow-hidden rounded-xl border border-emerald-100 shadow-sm bg-white">
                              <table className="w-full text-left">
                                  <thead className="bg-emerald-50/50 text-[10px] uppercase text-slate-500 font-semibold">
                                      <tr>
                                          <th className="p-4">Ngày</th>
                                          <th className="p-4">Lệnh</th>
                                          <th className="p-4">Chi tiết</th>
                                      </tr>
                                  </thead>
                                  <tbody className="divide-y divide-emerald-50">
                                      {logs.filter(l => l.category === 'STOCK').map((log, i) => (
                                          <tr key={i} className="text-xs hover:bg-emerald-50/20 transition">
                                              <td className="p-4 font-bold text-slate-500">{new Date(log.date).toLocaleDateString('vi-VN')}</td>
                                              <td className={`p-4 font-bold ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-500'}`}>{log.type}</td>
                                              <td className="p-4 text-slate-700 font-medium">{log.content}</td>
                                          </tr>
                                      ))}
                                  </tbody>
                              </table>
                          </div>
                      </div>
                  )}

                  {/* TAB 3: NHẬT KÝ DÒNG TIỀN */}
                  {activeHistoryTab === 'cashflow' && (
                      <div className="animate-in fade-in zoom-in duration-300 max-w-3xl mx-auto">
                        <div className="mb-6 p-4 bg-emerald-50 rounded-xl border border-emerald-100 flex items-center justify-between shadow-sm">
                          <div>
                             <p className="text-[10px] text-emerald-600 font-bold uppercase mb-1 tracking-widest">Tiền mặt thực có</p>
                             <h3 className="text-2xl font-bold text-slate-800 tracking-tight">
                               {Math.floor(data?.cash_balance || 0).toLocaleString()} <span className="text-sm font-medium text-slate-400">vnd</span>
                             </h3>
                          </div>
                          <div className="p-3 bg-white rounded-lg text-emerald-500 shadow-sm">
                             <Wallet size={24} />
                          </div>
                        </div>

                        <div className="space-y-4">
                            {logs.filter(l => l.category === 'CASH').length > 0 ? (
                              logs.filter(l => l.category === 'CASH').map((log, idx) => {
                                const isPositive = ['DEPOSIT', 'INTEREST', 'DIVIDEND_CASH'].includes(log.type);
                                const colorClass = isPositive ? 'bg-emerald-500' : 'bg-purple-500';
                                const textClass = isPositive ? 'text-emerald-700' : 'text-purple-700';
                                const bgClass = isPositive ? 'bg-emerald-50' : 'bg-purple-50';

                                return (
                                  <div key={idx} className="flex gap-4 items-start group">
                                    <div className="min-w-[60px] text-right pt-2">
                                      <p className="text-xs font-bold text-slate-500">{new Date(log.date).toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit'})}</p>
                                    </div>
                                    <div className="relative flex flex-col items-center self-stretch">
                                       <div className={`w-3 h-3 rounded-full mt-2 ${colorClass} z-10 ring-4 ring-white`}></div>
                                       <div className="w-0.5 bg-slate-100 flex-1 -mt-1 group-last:hidden"></div>
                                    </div>
                                    <div className={`flex-1 p-3 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition ${bgClass}`}>
                                       <div className="flex justify-between items-start mb-1">
                                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/80 ${textClass}`}>
                                            {log.type}
                                          </span>
                                       </div>
                                       <p className="text-xs font-medium text-slate-700">{log.content}</p>
                                    </div>
                                  </div>
                                );
                              })
                            ) : (
                              <div className="text-center p-10 text-slate-400 italic">Chưa có giao dịch tiền mặt.</div>
                            )}
                        </div>
                      </div>
                  )}
              </div>
          </div>
        </div>
      </div>

      {/* MODALS */}
      {(showDeposit || showWithdraw) && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl border border-emerald-100">
            <h2 className={`text-xl font-bold mb-6 ${showDeposit ? 'text-emerald-600' : 'text-purple-600'} uppercase`}>
              {showDeposit ? 'Nạp vốn' : 'Rút vốn'}
            </h2>
            {/* THAY THẾ FORM CŨ BẰNG FORM NÀY */}
            <form onSubmit={showDeposit ? handleDeposit : handleWithdraw} className="space-y-6">
              
              {/* Ô NHẬP SỐ TIỀN */}
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">
                  Số tiền muốn {showDeposit ? 'nạp' : 'rút'}
                </label>
                <div className="relative flex items-center">
                  <input 
                    type="text" // Đổi thành text để hiện dấu phẩy
                    required 
                    autoFocus 
                    className="w-full pl-4 pr-16 py-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-3xl font-medium text-slate-700 transition-all placeholder:text-slate-200"
                    value={amount} 
                    onChange={handleAmountChange} // Dùng hàm mới
                    placeholder="0" 
                  />
                  <span className="absolute right-4 text-slate-400 font-bold text-sm pointer-events-none">VNĐ</span>
                </div>
              </div>

              {/* Ô NHẬP GHI CHÚ */}
              <div>
                <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">
                  Ghi chú giao dịch
                </label>
                <input 
                  type="text" 
                  className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-base font-medium text-slate-600 transition-all" 
                  value={description} 
                  onChange={(e) => setDescription(e.target.value)} 
                  placeholder="..." 
                />
              </div>

              {/* NÚT BẤM */}
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeModals} className="flex-1 py-3.5 text-slate-400 font-bold hover:bg-slate-50 rounded-xl transition">Hủy</button>
                <button type="submit" className={`flex-1 py-3.5 text-white font-bold rounded-xl shadow-lg shadow-emerald-100 active:scale-95 transition ${showDeposit ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-purple-600 hover:bg-purple-700'}`}>
                  XÁC NHẬN
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showBuy && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold mb-6 text-rose-500 uppercase">MUA CỔ PHIẾU</h2>
            <form onSubmit={handleBuy} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2 ml-1">Mã CK</label>
                  <input type="text" required className="w-full p-3 bg-slate-50 border-none rounded-lg focus:ring-2 focus:ring-rose-200 outline-none font-bold text-xl text-rose-500 uppercase" 
                    value={buyForm.ticker} onChange={(e) => setBuyForm({...buyForm, ticker: e.target.value.toUpperCase()})} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2 ml-1">Khối lượng</label>
                  <input type="number" required className="w-full p-3 bg-slate-50 border-none rounded-lg focus:ring-2 focus:ring-rose-200 outline-none font-bold" 
                    value={buyForm.volume} onChange={(e) => setBuyForm({...buyForm, volume: e.target.value})} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2 ml-1">Giá Khớp</label>
                  <input type="number" step="0.01" required className="w-full p-3 bg-slate-50 border-none rounded-lg focus:ring-2 focus:ring-rose-200 outline-none font-bold" 
                    value={buyForm.price} onChange={(e) => setBuyForm({...buyForm, price: e.target.value})} />
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={closeModals} className="flex-1 py-3 text-slate-400 font-bold hover:bg-slate-50 rounded-lg transition">Hủy</button>
                <button type="submit" className="flex-1 py-3 bg-rose-500 hover:bg-rose-600 text-white font-bold rounded-lg shadow-lg">XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showSell && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl border border-rose-100">
            <h2 className="text-xl font-bold mb-6 text-rose-600 uppercase">BÁN CỔ PHIẾU</h2>
            <form onSubmit={handleSell} className="space-y-4">
              <div className="p-4 bg-rose-50 rounded-lg border border-rose-100 flex justify-between items-center">
                <p className="text-2xl font-bold text-rose-700 uppercase">{sellForm.ticker}</p>
                <p className="text-sm font-medium text-rose-700">Có: {sellForm.available}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2 ml-1">Số lượng</label>
                  <input type="number" required max={sellForm.available} className="w-full p-3 bg-slate-50 border-none rounded-lg focus:ring-2 focus:ring-rose-200 outline-none font-bold" 
                    value={sellForm.volume} onChange={(e) => setSellForm({...sellForm, volume: e.target.value})} />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2 ml-1">Giá Bán</label>
                  <input type="number" step="0.01" required className="w-full p-3 bg-slate-50 border-none rounded-lg focus:ring-2 focus:ring-rose-200 outline-none font-bold" 
                    value={sellForm.price} onChange={(e) => setSellForm({...sellForm, price: e.target.value})} />
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={closeModals} className="flex-1 py-3 text-slate-400 font-bold hover:bg-slate-50 rounded-lg transition">Hủy</button>
                <button type="submit" className="flex-1 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg shadow-lg">XÁC NHẬN</button>
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
    <div className="p-6 rounded-xl border border-white bg-white/60 backdrop-blur-sm shadow-xl shadow-purple-900/5 flex items-center gap-6 transition hover:-translate-y-1 duration-300">
      <div className={`p-4 rounded-lg ${bg} ${color} shadow-sm`}>{icon}</div>
      <div>
        <p className="text-slate-400 text-[10px] font-medium uppercase tracking-widest mb-1">{title}</p>
        <h3 className="text-2xl font-bold text-slate-800 tracking-tight">
          {value?.toLocaleString()} <span className="text-[10px] font-medium text-slate-300 ml-1 italic lowercase">vnd</span>
        </h3>
      </div>
    </div>
  );
}

function PerfBox({ label, data }) {
  const isProfit = (data?.val || 0) >= 0;
  const colorClass = isProfit ? "text-emerald-600" : "text-rose-500";
  
  return (
    <div className="p-6 text-center hover:bg-emerald-50/30 transition">
      <p className="text-slate-400 text-[11px] uppercase font-medium mb-3 tracking-[0.2em]">{label}</p>
      <p className={`text-2xl font-bold tracking-tighter ${colorClass}`}>
        {isProfit ? '+' : ''}{Math.floor(data?.val || 0).toLocaleString()}
      </p>
      <p className={`text-xs font-medium ${colorClass} mt-1 opacity-80`}>
        ({isProfit ? '+' : ''}{data?.pct?.toFixed(2)}%)
      </p>
    </div>
  );
}