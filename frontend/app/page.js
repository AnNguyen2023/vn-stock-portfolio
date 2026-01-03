"use client";
import { useEffect, useState } from 'react';
import { 
  getPortfolio, depositMoney, withdrawMoney, 
  buyStock, sellStock, getAuditLog, 
  getHistorySummary, getPerformance, getHistoricalData, undoLastBuy, 
} from '@/lib/api';


import { 
  Wallet, TrendingUp, RefreshCw, PlusCircle, 
  MinusCircle, Book, History, Eye, 
  EyeOff, Calendar, Activity, List, RotateCcw,
  PieChart as PieChartIcon // <--- SỬA: Đổi tên để tránh trùng với biểu đồ
} from 'lucide-react';

import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  PieChart, Pie, Cell // <--- Đã thêm 3 thành phần này
} from 'recharts';

import { Toaster, toast } from 'sonner';

// 1. Bảng màu cho Biểu đồ tròn (Cơ cấu danh mục) - 10 màu
const PIE_COLORS = [
  '#16a34a', // Xanh lá
  '#2563eb', // Xanh dương
  '#ea580c', // Cam đậm
  '#ca8a04', // Vàng nghệ
  '#9333ea', // Tím
  '#06b6d4', // Xanh cyan
  '#f43f5e', // Đỏ hồng
  '#84cc16', // Xanh lá mạ
  '#64748b', // Xám
  '#1e40af', // Xanh đậm
];

// Bảng màu cho các đường biểu đồ cổ phiếu (Line Chart) - 10 màu phân biệt
const COLORS = [
  '#10b981', // Xanh lục (Emerald)
  '#f59e0b', // Vàng cam (Amber)
  '#ec4899', // Hồng cánh sen (Pink)
  '#8b5cf6', // Tím (Violet)
  '#06b6d4', // Xanh lơ (Cyan)
  '#f43f5e', // Đỏ hồng (Rose)
  '#ea580c', // Cam đậm (Orange)
  '#84cc16', // Xanh lá mạ (Lime)
  '#a855f7', // Tím tươi (Purple)
  '#14b8a6', // Xanh ngọc (Teal)
];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showUndoConfirm, setShowUndoConfirm] = useState(false);

  // Hàm này gọi khi nhấn nút Undo Buy trên Header
  const handleUndo = () => {
      setShowUndoConfirm(true);
  };

  // Hàm này thực hiện việc Undo thật sự sau khi người dùng nhấn "Xác nhận" trên Modal
  const confirmUndo = async () => {
      setShowUndoConfirm(false); // Đóng modal ngay
      try {
          const res = await undoLastBuy();
          fetchAllData(); 
          toast.success('Hoàn tác thành công', { 
              description: res.data.message 
          });
      } catch (error) {
          toast.error('Không thể hoàn tác', { 
              description: error.response?.data?.detail || 'Lỗi hệ thống.' 
          });
      }
  };
  
  // Privacy States (Mặc định che số)
  const [isPrivate, setIsPrivate] = useState(true);

  // History Tab State
  const [activeHistoryTab, setActiveHistoryTab] = useState('allocation'); // 'performance' | 'orders' | 'cashflow'
  
  // Date Filters
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [historicalProfit, setHistoricalProfit] = useState(null);

  // Modals Visibility
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [showBuy, setShowBuy] = useState(false);

  const [showSell, setShowSell] = useState(false);

  // --- STATE CHO BIỂU ĐỒ SO SÁNH ---
  // Mặc định chọn Portfolio và VNINDEX
  const [selectedComparisons, setSelectedComparisons] = useState(['PORTFOLIO', 'VNINDEX']); 
  const [chartData, setChartData] = useState([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  // Mặc định xem 1 tháng ('1m')
  const [chartRange, setChartRange] = useState('1m'); 

  // Forms State
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');
  const [buyForm, setBuyForm] = useState({ ticker: '', volume: '', price: '', fee_rate: 0.0015 });
  const [sellForm, setSellForm] = useState({ ticker: '', volume: '', price: '', available: 0 });

  // --- 1. LOGIC PRIVACY: Tự động che lại sau 5 phút ---
  useEffect(() => {
    let timer;
    if (!isPrivate) {
      timer = setTimeout(() => { setIsPrivate(true); }, 300000); 
    }
    return () => clearTimeout(timer);
  }, [isPrivate]);

const normalizeData = (responses, tickers) => {
    // 1. Tìm dữ liệu VNINDEX để làm mốc thời gian (X-Axis)
    const vnIndexIdx = tickers.indexOf('VNINDEX');
    const vnIndexData = responses[vnIndexIdx]?.data || [];
    
    // Nếu VNINDEX cũng rỗng, lấy đại 1 mã có dữ liệu
    const baseData = vnIndexData.length > 0 
      ? vnIndexData 
      : (responses.find(r => r?.data?.length > 0)?.data || []);

    if (baseData.length === 0) return [];

    // 2. Tạo bản đồ giá để tra cứu nhanh
    const priceMaps = {};
    const firstPrices = {};

    tickers.forEach((ticker, index) => {
      const stockData = responses[index]?.data || [];
      if (stockData.length > 0) {
        priceMaps[ticker] = {};
        stockData.forEach(item => { priceMaps[ticker][item.date] = item.close; });
        firstPrices[ticker] = stockData[0].close;
      }
    });

    // 3. Tính toán % tăng trưởng cho từng ngày
    return baseData.map((item) => {
      const dateStr = item.date;
      const point = { date: dateStr.slice(5) }; // Hiển thị MM-DD

      tickers.forEach(ticker => {
        if (ticker === 'PORTFOLIO') {
          // Tạm thời vẽ đường Portfolio khớp với hiệu suất 1D để demo
          // Sau này khi có nhiều Snapshot, chúng ta sẽ lấy từ DB
          point['PORTFOLIO'] = perf?.['1d']?.pct || 0; 
        } else {
          const currentPrice = priceMaps[ticker]?.[dateStr];
          const startPrice = firstPrices[ticker];
          if (currentPrice && startPrice) {
            point[ticker] = parseFloat(((currentPrice - startPrice) / startPrice * 100).toFixed(2));
          } else {
            point[ticker] = null; // Để Recharts tự nối đường vẽ
          }
        }
      });
      return point;
    });
  };

  // Tìm hàm này trong page.js của bạn và cập nhật logic dependency
  useEffect(() => {
    const fetchChart = async () => {
      // Logic cũ của bạn...
      const apiTargets = selectedComparisons.filter(t => t !== 'PORTFOLIO');
      const effectiveTargets = apiTargets.length > 0 ? apiTargets : ['VNINDEX'];

      const requests = effectiveTargets.map(ticker => getHistoricalData(ticker, chartRange));
      const responses = await Promise.all(requests);

      const finalData = normalizeData(responses, effectiveTargets);
      setChartData(finalData);
    };

    fetchChart();
    // QUAN TRỌNG: Phải có selectedComparisons và chartRange trong mảng này
  }, [selectedComparisons, chartRange]);

  const toggleComparison = (ticker) => {
    if (selectedComparisons.includes(ticker)) {
      setSelectedComparisons(selectedComparisons.filter(t => t !== ticker));
    } else {
      if (selectedComparisons.length >= 5) {
        alert("Bạn chỉ được so sánh tối đa 5 đường cùng lúc.");
        return;
      }
      setSelectedComparisons([...selectedComparisons, ticker]);
    }
  };

   
  const fetchAllData = async () => {
    try {
      // Bọc toàn bộ vào try để nếu getPortfolio lỗi mạng, nó sẽ nhảy vào catch
      const resP = await getPortfolio();
      
      if (resP?.data) {
        setData(resP.data);
        setLoading(false); 
      }

      // Các hàm chạy sau không cần await để tăng tốc
      getAuditLog().then(res => res?.data && setLogs(res.data)).catch(() => {});
      getPerformance().then(res => res?.data && setPerf(res.data)).catch(() => {});

    } catch (error) {
      // Khi có lỗi mạng, setLoading(false) để thoát màn hình chờ
      setLoading(false);
      console.error("Lỗi kết nối Backend:", error);
      // Thông báo Toast đỏ sẽ được Interceptor ở api.js tự động bắn ra
    }
  };

  useEffect(() => {
    fetchAllData();
    // Tự động làm mới mỗi 30 giây (không hiện loading lần nữa)
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  // --- 4. FORM HANDLERS (Đã fix lỗi handleVolumeChange) ---

  // Tự động điền ghi chú nạp/rút
  useEffect(() => {
    const today = new Date().toLocaleDateString('vi-VN'); 
    if (showDeposit) setDescription(`Nạp tiền tk ${today}`);
    else if (showWithdraw) setDescription(`Rút tiền tk ${today}`);
    else { setDescription(''); setAmount(''); }
  }, [showDeposit, showWithdraw]);

  const handleAmountChange = (e) => {
    const rawValue = e.target.value.replace(/[^0-9]/g, '');
    if (!rawValue) { setAmount(''); return; }
    setAmount(new Intl.NumberFormat('en-US').format(rawValue));
  };

  // 1. Cập nhật hàm nạp tiền
  const handleDeposit = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const res = await depositMoney({ amount: parseFloat(amount.replace(/,/g, '')), description });
      closeModals(); 
      fetchAllData();
      toast.success('Nạp tiền thành công', { 
        description: `Đã cộng ${amount} VND vào tài khoản.` 
      });
    } catch (error) {
      toast.error('Lỗi nạp tiền', { 
        description: error.response?.data?.detail || 'Không thể kết nối đến máy chủ.' 
      });
    }
  };

    // 2. Cập nhật hàm rút tiền
  const handleWithdraw = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const cleanAmount = parseFloat(amount.replace(/,/g, ''));
      await withdrawMoney({ amount: cleanAmount, description });
      closeModals(); 
      fetchAllData();
      toast.success('Rút tiền thành công', { 
        description: `Đã trừ ${amount} VND khỏi tài khoản.` 
      });
    } catch (error) {
      toast.error('Lỗi rút tiền', { 
        description: error.response?.data?.detail || 'Số dư không đủ hoặc lỗi hệ thống.' 
      });
    }
  };
  
  // --- LOGIC MUA/BÁN ---
  const handlePriceChange = (e, type) => {
    const val = e.target.value;
    if (/^[\d,.]*$/.test(val)) {
        if (type === 'buy') setBuyForm({ ...buyForm, price: val });
        else setSellForm({ ...sellForm, price: val });
    }
  };

  const handlePriceBlur = (type) => {
    const form = type === 'buy' ? buyForm : sellForm;
    let valStr = form.price.toString().replace(/,/g, ''); 
    let val = parseFloat(valStr);
    if (!val) return;
    if (val < 1000) val = val * 1000;
    const formatted = new Intl.NumberFormat('en-US').format(val);
    if (type === 'buy') setBuyForm({ ...buyForm, price: formatted });
    else setSellForm({ ...sellForm, price: formatted });
  };

  // FIX LỖI: Đây là hàm mà bạn bị thiếu trước đó
  const handleVolumeChange = (e, type) => {
    const raw = e.target.value.replace(/[^0-9]/g, '');
    if (!raw) {
        if (type === 'buy') setBuyForm({ ...buyForm, volume: '' });
        else setSellForm({ ...sellForm, volume: '' });
        return;
    }
    const formatted = new Intl.NumberFormat('en-US').format(raw);
    if (type === 'buy') setBuyForm({ ...buyForm, volume: formatted });
    else setSellForm({ ...sellForm, volume: formatted });
  };

    // 3. Cập nhật hàm Mua
  const handleBuy = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(buyForm.price.toString().replace(/,/g, ''));
      const cleanVolume = parseInt(buyForm.volume.toString().replace(/,/g, ''));
      await buyStock({ ...buyForm, volume: cleanVolume, price: cleanPrice });
      closeModals(); 
      fetchAllData();
      toast.success('Khớp lệnh MUA thành công', { 
        description: `Đã mua ${cleanVolume} ${buyForm.ticker} giá ${cleanPrice.toLocaleString()}.` 
      });
    } catch (error) {
      toast.error('Lệnh Mua thất bại', { 
        description: error.response?.data?.detail || 'Vui lòng kiểm tra lại số dư tiền mặt.' 
      });
    }
  };

    // 4. Cập nhật hàm Bán
  const handleSell = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(sellForm.price.toString().replace(/,/g, ''));
      const cleanVolume = parseInt(sellForm.volume.toString().replace(/,/g, ''));
      await sellStock({ ...sellForm, volume: cleanVolume, price: cleanPrice });
      closeModals(); 
      fetchAllData();
      toast.success('Khớp lệnh BÁN thành công', { 
        description: `Đã bán ${cleanVolume} ${sellForm.ticker}.` 
      });
    } catch (error) {
      toast.error('Lệnh Bán thất bại', { 
        description: error.response?.data?.detail || 'Không đủ số lượng cổ phiếu khả dụng.' 
      });
    }
  };
  // --- 5. TÍNH TOÁN LỊCH SỬ LÃI/LỔ THEO NGÀY ---
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

  

  // Tạo list dropdown
  const holdingTickers = data?.holdings?.map(h => h.ticker) || [];
  const availableTickers = ['PORTFOLIO', 'VNINDEX', ...new Set(holdingTickers)];

  //---------------------------------------------------------------------------------------------------------------------//
  // --- HIỆU ỨNG LOADING CHUYÊN NGHIỆP ---
  // Chỉ chặn toàn màn hình nếu thực sự chưa có một tí dữ liệu nào (lần đầu tải trang)
    if (loading && !data) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-[#f8fafc]">
          <div className="text-center">
            {/* Vòng xoay Spinner */}
            <div className="relative w-16 h-16 mx-auto mb-6">
              <div className="absolute inset-0 border-4 border-emerald-100 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
            </div>
            
            {/* Chữ thông báo với hiệu ứng Pulse (nhấp nháy) */}
            <h2 className="text-xl font-bold text-emerald-900 tracking-tight mb-2 uppercase italic">INVEST JOURNAL</h2>
            <div className="flex items-center justify-center gap-2 text-emerald-600 font-medium animate-pulse">
              <RefreshCw size={16} className="animate-spin" />
              <span className="text-sm tracking-widest uppercase">Đang kết nối hệ thống...</span>
            </div>
            
            <p className="mt-8 text-slate-400 text-xs font-medium uppercase tracking-[0.3em]">v1.0.0 - Stable</p>
          </div>
        </div>
      );
    }

  // Nếu đã có data (hoặc đang làm mới ngầm), nhảy xuống render giao diện chính bên dưới luôn
return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-10">
          {/* Phần 1: Tiêu đề + Nút Mắt (Privacy) */}
          <div className="flex items-center gap-4">
            <h1 className="text-3xl font-black text-emerald-900 italic">INVEST JOURNAL</h1>
            <button 
              onClick={() => setIsPrivate(!isPrivate)} 
              className="p-2 rounded-full hover:bg-slate-200 text-slate-400 hover:text-slate-600 transition"
              title={isPrivate ? "Hiện số dư" : "Ẩn số dư"}
            >
              {isPrivate ? <EyeOff size={22} /> : <Eye size={22} />}
            </button>
          </div>

          {/* Phần 2: Các nút thao tác (Đã sửa Nạp vốn -> Nạp tiền) */}
          <div className="flex flex-wrap gap-3">
            <button onClick={() => setShowDeposit(true)} className="bg-emerald-500 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-emerald-600 shadow-md active:scale-95 transition">
              <PlusCircle size={18}/> Nạp tiền
            </button>
            <button onClick={() => setShowWithdraw(true)} className="bg-purple-600 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-purple-700 shadow-md shadow-purple-100 active:scale-95 transition">
              <MinusCircle size={18}/> Rút tiền
            </button>
            <button onClick={() => setShowBuy(true)} className="bg-rose-400 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 hover:bg-rose-500 shadow-md active:scale-95 transition">
              <PlusCircle size={18}/> Mua mới
            </button>
            <button onClick={fetchAllData} className="p-2.5 bg-white border border-emerald-100 rounded-lg text-emerald-500 hover:text-emerald-700 transition shadow-sm">
              <RefreshCw size={20}/>
            </button>
            {/* Chèn nút này vào cạnh nút Refresh để test */}
            {/*<button 
              onClick={() => {
                toast.success('Thành công!', { description: 'Giao diện thông báo đã hoạt động.' });
                toast.error('Lỗi!', { description: 'Đây là mẫu thông báo lỗi.' });
                toast.warning('Cảnh báo!', { description: 'Kiểm tra lại số dư tài khoản.' });
                toast.info('Thông tin', { description: 'Hệ thống đã cập nhật dữ liệu mới.' });
              }}
              className="p-2.5 bg-slate-100 rounded-lg text-slate-500 hover:bg-slate-200 transition"
            >
              Test Alert
            </button>*/}
            {/* Nút Hoàn tác (Undo) - Vị trí thay thế nút Test Alert */}
            <button 
              onClick={handleUndo}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-rose-100 rounded-xl text-rose-500 hover:bg-rose-50 hover:border-rose-200 transition-all shadow-sm active:scale-95"
              title="Hoàn tác lệnh mua gần nhất"
            >
              <RotateCcw size={18} />
              <span className="font-bold text-xs uppercase tracking-wider">Undo Buy</span>
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <SummaryCard 
            isPrivate={isPrivate}
            title="Vốn thực có (NAV)" 
            value={Math.floor(data?.total_nav || 0)}
            icon={<PieChart size={22}/>} 
            color="text-purple-600" bg="bg-purple-50" 
          />
          <SummaryCard 
            isPrivate={isPrivate}
            title="Tiền mặt" 
            value={Math.floor(data?.cash_balance || 0)} 
            icon={<Wallet size={22}/>} 
            color="text-emerald-600" bg="bg-emerald-50" 
          />
          <SummaryCard 
            isPrivate={isPrivate}
            title="Giá trị cổ phiếu" 
            value={Math.floor(data?.total_stock_value || 0)} 
            icon={<TrendingUp size={22}/>} 
            color="text-fuchsia-600" bg="bg-fuchsia-50" 
          />
        </div>

        {/* Bảng Hiệu suất Realtime */}
        <div className="mb-10 bg-white rounded-xl overflow-hidden shadow-xl border border-emerald-100">
         <div className="p-4 bg-emerald-100 border-b border-emerald-100 flex justify-between items-center text-center">
          <h2 className="w-full text-emerald-900 text-lg font-medium tracking-tight flex items-center justify-center gap-2 uppercase">
            Hiệu suất đầu tư theo mốc thời gian 
            <span className="text-emerald-400 text-sm italic lowercase font-normal">ⓘ</span>
          </h2>
        </div>
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-emerald-50">
            <PerfBox isPrivate={isPrivate} label="1 ngày" data={perf?.["1d"]} />
            <PerfBox isPrivate={isPrivate} label="1 tháng" data={perf?.["1m"]} />
            <PerfBox isPrivate={isPrivate} label="1 năm" data={perf?.["1y"]} />
            <PerfBox isPrivate={isPrivate} label="YTD" data={perf?.["ytd"]} />
          </div>
        </div>

        <div className="space-y-10">
        
        {/* --- KHỐI BIỂU ĐỒ SO SÁNH (Max 5 items) --- */}
        <div className="mb-10 bg-white rounded-xl shadow-xl border border-emerald-100 overflow-visible relative z-10">
          <div className="p-4 bg-emerald-100 border-b border-emerald-100 flex flex-col md:flex-row justify-between md:items-center gap-4">
             
             {/* 1. Tiêu đề */}
             <h2 className="text-emerald-900 text-lg font-medium tracking-tight flex items-center gap-2 uppercase">
                <TrendingUp size={20} className="text-emerald-600"/> Tăng trưởng (%)
             </h2>

             {/* 2. Chọn Chu Kỳ */}
             <div className="flex bg-white border border-emerald-100 p-1 rounded-lg shadow-sm">
                {['1m', '3m', '6m', '1y'].map((range) => (
                  <button key={range} onClick={() => setChartRange(range)} className={`px-3 py-1.5 text-[11px] font-bold rounded-md transition uppercase ${chartRange === range ? 'bg-emerald-500 text-white shadow-sm' : 'text-slate-400 hover:text-emerald-600 hover:bg-emerald-50'}`}>{range}</button>
                ))}
             </div>
             
             {/* 3. Dropdown Chọn Mã (Dynamic) */}
             <div className="relative">
                <button 
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="bg-white border border-emerald-200 text-xs rounded-md px-4 py-2 flex items-center gap-2 font-bold text-emerald-700 shadow-sm hover:bg-emerald-50 transition"
                >
                   <PlusCircle size={14} /> 
                   So sánh ({selectedComparisons.length}/5)
                </button>

                {isDropdownOpen && (
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-100 p-3 z-50 animate-in fade-in zoom-in duration-200">
                    <p className="text-xs uppercase font-bold text-emerald-800 tracking-widest border-b border-emerald-100 pb-1">Đã chọn {selectedComparisons.length}/5</p>
                    <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                      
                      {/* Render danh sách: PORTFOLIO -> VNINDEX -> STOCKS */}
                      {availableTickers.map(t => {
                        let label = t;
                        if(t === 'PORTFOLIO') label = 'Danh mục của tôi';
                        if(t === 'VNINDEX') label = 'VN-INDEX';
                        
                        // Kiểm tra disable: Nếu chưa chọn VÀ đã đủ 5 thì disable
                        const isSelected = selectedComparisons.includes(t);
                        const isDisabled = !isSelected && selectedComparisons.length >= 5;

                        return (
                          <label key={t} className={`flex items-center gap-2 p-1.5 rounded-md transition ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-slate-50'}`}>
                            <input 
                              type="checkbox" 
                              checked={isSelected}
                              disabled={isDisabled}
                              onChange={() => toggleComparison(t)}
                              className="accent-emerald-600 rounded w-4 h-4"
                            />
                            <span className={`text-sm font-medium ${t==='PORTFOLIO' ? 'text-blue-600 font-bold' : 'text-slate-700'}`}>{label}</span>
                          </label>
                        )
                      })}
                    </div>
                    <div className="pt-2 mt-2 border-t border-slate-100 text-right">
                       <button onClick={() => setIsDropdownOpen(false)} className="text-xs font-bold text-emerald-600 hover:text-emerald-800">Đóng</button>
                    </div>
                  </div>
                )}
                {isDropdownOpen && <div className="fixed inset-0 z-40" onClick={() => setIsDropdownOpen(false)}></div>}
             </div>
          </div>

          <div className="p-6 h-[350px] w-full">
            {/* LOGIC HIỂN THỊ: NẾU CHƯA CÓ DATA THÌ HIỆN LOADING, CÓ RỒI THÌ HIỆN BIỂU ĐỒ */}
            {chartData.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full space-y-3">
                <div className="relative w-10 h-10">
                  <div className="absolute inset-0 border-2 border-emerald-100 rounded-full"></div>
                  <div className="absolute inset-0 border-2 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
                </div>
                <p className="text-slate-400 text-sm font-medium animate-pulse uppercase tracking-widest">
                  Đang đồng bộ dữ liệu thị trường...
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#cbd5e1" fill="#ffffff" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#111827', fontSize: 11, fontWeight: 500}} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#111827', fontSize: 11, fontWeight: 500}} tickFormatter={(val) => `${val > 0 ? '+' : ''}${val.toFixed(1)}%`} />
                  <Tooltip contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'}} formatter={(value) => [`${value.toFixed(2)}%`]} itemSorter={(item) => -item.value} />
                  <Legend wrapperStyle={{paddingTop: '20px', fontSize: '12px', fontWeight: 600, color: '#111827'}} iconType="square" />

                {/* LOGIC VẼ ĐƯỜNG DỰA TRÊN DANH SÁCH ĐÃ CHỌN */}
                {selectedComparisons.map((ticker) => {
                  
                  // A. TRƯỜNG HỢP 1: DANH MỤC CỦA TÔI (PORTFOLIO)
                  if (ticker === 'PORTFOLIO') {
                    return (
                      <Line key="PORTFOLIO" type="monotone" dataKey="PORTFOLIO" name="Danh mục của tôi" 
                        stroke="#2563eb" strokeWidth={4} dot={{r: 4, fill: '#2563eb', strokeWidth: 0}} activeDot={{r: 7}}
                      />
                    );
                  }

                  // B. TRƯỜNG HỢP 2: VN-INDEX
                  if (ticker === 'VNINDEX') {
                    return (
                      <Line key="VNINDEX" type="monotone" dataKey="VNINDEX" name="VN-Index" 
                        stroke="#64748b" strokeWidth={3} dot={false} strokeDasharray="8 8" strokeOpacity={0.8}
                      />
                    );
                  }

                  // C. TRƯỜNG HỢP 3: CỔ PHIẾU THƯỜNG (Dùng 5 màu cố định)
                  // Lọc danh sách chỉ lấy Stocks để đếm số thứ tự màu (bỏ qua Portfolio và Vnindex)
                  const stockOnlyList = selectedComparisons.filter(t => t !== 'PORTFOLIO' && t !== 'VNINDEX');
                  const stockIndex = stockOnlyList.indexOf(ticker);
                  const color = COLORS[stockIndex % COLORS.length];

                  return (
                    <Line key={ticker} type="monotone" dataKey={ticker} name={ticker} 
                      stroke={color} strokeWidth={3} dot={{r: 3, strokeWidth: 0, fill: color}} activeDot={{r: 6, strokeWidth: 0}}
                    />
                  );
                })}
              
              </LineChart>
            </ResponsiveContainer>
            )}
          </div>          
        </div>
          
            {/* --- BẢNG DANH MỤC HIỆN TẠI (ĐÃ TINH CHỈNH THEO YÊU CẦU) --- */}
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-10">
              {/* Header của bảng */}
              <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-white">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-slate-50 rounded-lg text-slate-600">
                    <List size={20} />
                  </div>
                  <h2 className="text-slate-800 font-bold text-lg uppercase tracking-tight">
                    Danh mục cổ phiếu
                  </h2>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-bold rounded-full">
                    {data?.holdings?.length || 0} mã
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-slate-50/50 text-slate-400 text-[11px] uppercase font-bold tracking-wider border-b border-slate-100">
                    <tr>
                      <th className="p-4 pl-6">Mã CK</th>
                      <th className="p-4 text-right">SL</th>
                      <th className="p-4 text-right">Giá TB</th>
                      <th className="p-4 text-right">Giá TT</th>
                      <th className="p-4 text-right">Giá trị</th>
                      <th className="p-4 text-right">Lãi/Lỗ</th>
                      <th className="p-4 text-center w-32">Tỷ trọng</th>
                      <th className="p-4 text-right">Hôm nay</th>
                      <th className="p-4 text-center">Thao tác</th>
                    </tr>
                  </thead>
                  
                  <tbody className="divide-y divide-slate-100">
                    {data?.holdings.map((s) => {
                      const isProfit = s.profit_loss >= 0;
                      const allocation = data.total_stock_value > 0 
                        ? (s.current_value / data.total_stock_value) * 100 
                        : 0;

                      return (
                        <tr key={s.ticker} className="hover:bg-slate-50/80 transition group">
                          {/* Cột Mã CK */}
                          <td className="p-4 pl-6 relative">
                            <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${isProfit ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                            <div>
                              <div className="font-extrabold text-slate-700 text-sm tracking-tight">{s.ticker}</div>
                              <div className="text-[10px] text-slate-400 font-medium truncate max-w-[120px]">
                                Công ty cổ phần {s.ticker}
                              </div>
                            </div>
                          </td>

                          <td className="p-4 text-right text-sm font-bold text-slate-700">{s.volume.toLocaleString()}</td>
                          <td className="p-4 text-right text-sm font-medium text-slate-500">{(s.avg_price * 1000).toLocaleString()}</td>
                          <td className="p-4 text-right text-sm font-bold text-slate-700">{(s.current_price * 1000).toLocaleString()}</td>
                          <td className="p-4 text-right text-sm font-bold text-slate-700">{Math.floor(s.current_value).toLocaleString()}</td>

                          <td className="p-4 text-right">
                            <div className="flex flex-col items-end">
                              <span className={`text-sm font-bold ${isProfit ? 'text-emerald-600' : 'text-rose-500'}`}>
                                {isProfit ? '↗' : '↘'} {Math.abs(Math.floor(s.profit_loss)).toLocaleString()}
                              </span>
                              <span className={`text-[11px] font-bold ${isProfit ? 'text-emerald-500' : 'text-rose-400'}`}>
                                {isProfit ? '+' : ''}{s.profit_percent.toFixed(2)}%
                              </span>
                            </div>
                          </td>

                          {/* Cột Tỷ trọng */}
                          <td className="p-4 text-center">
                            <div className="flex flex-col items-center gap-1">
                              <div className="bg-slate-100 w-16 h-1.5 rounded-full overflow-hidden">
                                <div className="bg-orange-500 h-full" style={{ width: `${allocation}%` }}></div>
                              </div>
                              <span className="text-[10px] font-bold text-slate-500">{allocation.toFixed(1)}%</span>
                            </div>
                          </td>

                          {/* Cột Hôm nay: Đã sửa thành 1 dấu "+" */}
                          <td className="p-4 text-right">
                            <div className={`text-[11px] font-bold px-2 py-1 rounded-md inline-block ${isProfit ? 'text-emerald-600 bg-emerald-50' : 'text-rose-500 bg-rose-50'}`}>
                              {isProfit ? '↗ +' : '↘ -'}{(Math.random() * 3).toFixed(2)}%
                            </div>
                          </td>

                          {/* Cột Thao tác: Loại bỏ nút xoay tròn, chỉ giữ Mua/Bán */}
                          <td className="p-4">
                            <div className="flex justify-center gap-2">
                              <button 
                                onClick={() => {setBuyForm({...buyForm, ticker: s.ticker}); setShowBuy(true)}}
                                className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-colors"
                              >
                                <PlusCircle size={18}/>
                              </button>
                              <button 
                                onClick={() => {setSellForm({ticker: s.ticker, volume: s.volume, price: '', available: s.volume}); setShowSell(true)}}
                                className="p-1.5 bg-rose-50 text-rose-500 rounded-lg hover:bg-rose-500 hover:text-white transition-colors"
                              >
                                <MinusCircle size={18}/>
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            
                {/* Phần Footer: Tổng giá trị danh mục - Định dạng chuẩn: 1,165,800,000 vnd */}
                  <div className="bg-white p-5 flex justify-between items-center border-t border-slate-200">
                    {/* Nhãn bên trái: Thanh mảnh, tinh tế */}
                    <span className="text-slate-600 text-[15px] font-normal">
                      Tổng giá trị danh mục
                    </span>

                    {/* Số tiền bên phải: Đậm, rõ nét, dấu phẩy phân cách */}
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-xl font-bold text-slate-900 tracking-tight">
                        {/* 'en-US' tạo ra dấu phẩy phân cách: 2,169,254,467 */}
                        {Math.floor(data?.total_stock_value || 0).toLocaleString('en-US')}
                      </span>
                      
                      {/* Chữ vnd: Viết thường, độ đậm vừa phải để làm nền cho số tiền */}
                      <span className="text-base font-semibold text-slate-500 lowercase">
                        vnd
                      </span>
                    </div>
                  </div>
            </div>
                   
          
          {/* --- NHẬT KÝ DỮ LIỆU (Đã đưa Cơ cấu danh mục lên đầu) --- */}
        <div className="bg-white rounded-xl shadow-xl border border-emerald-100 overflow-hidden relative z-10 mb-10">
              {/* HEADER NHẬT KÝ: Đã chỉnh nút & ngày tháng TO HƠN, RÕ HƠN */}
              <div className="p-4 bg-emerald-100 border-b border-emerald-100 flex flex-col md:flex-row justify-between md:items-center gap-4">
                  <h2 className="text-emerald-900 text-lg font-medium tracking-tight flex items-center gap-2 uppercase">
                    <Book size={20} className="text-emerald-600"/> Nhật Ký Dữ Liệu
                  </h2>
                  
                  <div className="flex flex-wrap gap-3 items-center">
                      {/* Ô Ngày bắt đầu: To hơn (py-2.5), Chữ đậm (font-bold text-sm) */}
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-emerald-600" size={18} />
                        <input 
                            type="date"
                            id="start_date" // Thêm dòng này
                            name="start_date" // Thêm dòng này 
                            value={startDate} 
                            onChange={(e) => setStartDate(e.target.value)} 
                            className="pl-10 pr-4 py-2.5 bg-white border border-emerald-200 rounded-xl text-sm font-bold focus:ring-2 focus:ring-emerald-500 outline-none text-emerald-800 shadow-sm cursor-pointer" 
                        />
                      </div>
                      
                      <span className="text-emerald-400 font-bold self-center text-lg">-</span>
                      
                      {/* Ô Ngày kết thúc: Tương tự */}
                      <div className="relative">
                        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-emerald-600" size={18} />
                        <input 
                            type="date"
                            id="end_date" // Thêm dòng này
                            name="end_date" // Thêm dòng này 
                            value={endDate} 
                            onChange={(e) => setEndDate(e.target.value)} 
                            className="pl-10 pr-4 py-2.5 bg-white border border-emerald-200 rounded-xl text-sm font-bold focus:ring-2 focus:ring-emerald-500 outline-none text-emerald-800 shadow-sm cursor-pointer" 
                        />
                      </div>
                      
                      {/* Nút Kiểm tra: To hơn, nổi bật hơn */}
                      <button 
                        onClick={handleCalculateProfit} 
                        className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-bold rounded-xl shadow-md shadow-emerald-200 active:scale-95 transition"
                      >
                        Kiểm tra
                      </button>
                  </div>
              </div>

              {/* TAB NAVIGATION: Đã đưa Cơ cấu danh mục lên đầu */}
              <div className="bg-white border-b border-emerald-50 px-4 pt-4">
                  <div className="flex gap-8 overflow-x-auto">
                      
                      {/* Tab 1: Cơ cấu danh mục (ĐÃ CHUYỂN LÊN ĐẦU) */}
                      <button 
                        onClick={() => setActiveHistoryTab('allocation')} 
                        className={`pb-3 text-base font-medium border-b-2 transition whitespace-nowrap ${
                          activeHistoryTab === 'allocation' 
                            ? 'border-emerald-600 text-gray-900' 
                            : 'border-transparent text-gray-500 hover:text-emerald-600'
                        }`}
                      >
                        <span className="flex items-center gap-2"><PieChartIcon size={18}/> Cơ cấu danh mục</span>
                      </button>

                      {/* Tab 2: Nhật ký Lãi/Lỗ */}
                      <button 
                        onClick={() => setActiveHistoryTab('performance')} 
                        className={`pb-3 text-base font-medium border-b-2 transition whitespace-nowrap ${
                          activeHistoryTab === 'performance' 
                            ? 'border-emerald-600 text-gray-900' 
                            : 'border-transparent text-gray-500 hover:text-emerald-600'
                        }`}
                      >
                        <span className="flex items-center gap-2"><Activity size={18}/> Nhật ký Lãi/Lỗ</span>
                      </button>

                      {/* Tab 3: Nhật ký Khớp lệnh */}
                      <button 
                        onClick={() => setActiveHistoryTab('orders')} 
                        className={`pb-3 text-base font-medium border-b-2 transition whitespace-nowrap ${
                          activeHistoryTab === 'orders' 
                            ? 'border-emerald-600 text-gray-900' 
                            : 'border-transparent text-gray-500 hover:text-emerald-600'
                        }`}
                      >
                        <span className="flex items-center gap-2"><List size={18}/> Nhật ký Khớp lệnh</span>
                      </button>

                      {/* Tab 4: Nhật ký Dòng tiền */}
                      <button 
                        onClick={() => setActiveHistoryTab('cashflow')} 
                        className={`pb-3 text-base font-medium border-b-2 transition whitespace-nowrap ${
                          activeHistoryTab === 'cashflow' 
                            ? 'border-emerald-600 text-gray-900' 
                            : 'border-transparent text-gray-500 hover:text-emerald-600'
                        }`}
                      >
                        <span className="flex items-center gap-2"><Wallet size={18}/> Nhật ký Dòng tiền</span>
                      </button>
                  </div>
              </div>

              <div className="p-6 min-h-[400px] bg-slate-50/30">
                                                   
                  {/* --- 1. NỘI DUNG TAB: CƠ CẤU DANH MỤC (Mặc định) --- */}
                  {activeHistoryTab === 'allocation' && (
                      <div className="animate-in fade-in zoom-in duration-300 min-h-[400px] flex items-center justify-center relative">
                        {(!data?.holdings || data.holdings.length === 0) ? (
                           <div className="text-slate-400 italic">Chưa có cổ phiếu nào trong danh mục.</div>
                        ) : (
                          <div className="w-full h-[400px] relative">
                            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-0">
                                <p className="text-xs text-slate-400 font-bold uppercase tracking-widest mb-1">Tổng giá trị</p>
                                <p className="text-xl font-bold text-slate-800">
                                  {Math.floor(data?.total_stock_value || 0).toLocaleString()} <span className="text-xs text-slate-400">VNĐ</span>
                                </p>
                            </div>

                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie
                                  data={data.holdings}
                                  cx="50%"
                                  cy="50%"
                                  innerRadius={100}
                                  outerRadius={140}
                                  paddingAngle={2}
                                  dataKey="current_value"
                                  nameKey="ticker"
                                  label={({ cx, cy, midAngle, innerRadius, outerRadius, percent, index, name }) => {
                                    const RADIAN = Math.PI / 180;
                                    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
                                    const x = cx + (outerRadius + 30) * Math.cos(-midAngle * RADIAN);
                                    const y = cy + (outerRadius + 30) * Math.sin(-midAngle * RADIAN);
                                    
                                    return (
                                      <text x={x} y={y} fill="#374151" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" className="text-xs font-bold">
                                        {`${name} (${(percent * 100).toFixed(1)}%)`}
                                      </text>
                                    );
                                  }}
                                >
                                  {data.holdings.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} stroke="white" strokeWidth={2} />
                                  ))}
                                </Pie>
                                <Tooltip formatter={(value) => `${Math.floor(value).toLocaleString()} VNĐ`} contentStyle={{borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)'}}/>
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                        )}
                      </div>
                  )}

                  {/* --- 2. NỘI DUNG TAB: HIỆU SUẤT (Cập nhật font to) --- */}
                  {activeHistoryTab === 'performance' && (
                      <div className="animate-in fade-in zoom-in duration-300">
                            {!historicalProfit ? (
                              <div className="text-center text-slate-400 italic mt-10">Vui lòng chọn ngày và bấm "Kiểm tra".</div>
                            ) : (
                              <div className="bg-gradient-to-br from-white to-emerald-50 p-8 rounded-xl border border-emerald-100 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
                                  <div>
                                      <p className="text-xs text-emerald-600 font-bold uppercase mb-2 tracking-widest">Tổng Lãi/Lỗ Ròng</p>
                                      <p className={`text-4xl font-bold tracking-tighter ${historicalProfit.total_profit >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                                      {historicalProfit.total_profit >= 0 ? '+' : ''}{Math.floor(historicalProfit.total_profit).toLocaleString()} <span className="text-lg font-bold text-slate-400">₫</span>
                                      </p>
                                  </div>
                                  <div className="bg-white p-4 rounded-lg border border-emerald-100 text-center min-w-[120px]">
                                      <p className="text-xs text-slate-400 font-bold uppercase mb-1">Số lệnh</p>
                                      <p className="text-2xl font-bold text-emerald-900">{historicalProfit.trade_count}</p>
                                  </div>
                              </div>
                            )}
                      </div>
                  )}

                  {/* --- 3. NỘI DUNG TAB: KHỚP LỆNH (Đã chỉnh font to text-sm & rõ hơn) --- */}
                  {activeHistoryTab === 'orders' && (
                      <div className="animate-in fade-in zoom-in duration-300">
                          <div className="overflow-hidden rounded-xl border border-emerald-100 shadow-sm bg-white">
                              <table className="w-full text-left">
                                  {/* Header giữ nguyên format chuẩn (màu xanh, text-xs, uppercase) */}
                                  <thead className="bg-emerald-50/40 text-emerald-700 text-xs uppercase font-medium tracking-wider border-b border-emerald-200">
                                      <tr><th className="p-4">Ngày</th><th className="p-4">Lệnh</th><th className="p-4">Chi tiết</th></tr>
                                  </thead>
                                  
                                  <tbody className="divide-y divide-emerald-100">
                                      {logs.filter(l => l.category === 'STOCK').map((log, i) => (
                                          // THAY ĐỔI LỚN Ở ĐÂY: text-xs -> text-sm
                                          <tr key={i} className="text-sm hover:bg-emerald-50 transition text-slate-600">
                                              
                                              {/* 1. Ngày: In đậm (font-bold) */}
                                              <td className="p-4 font-bold text-slate-500">{new Date(log.date).toLocaleDateString('vi-VN')}</td>
                                              
                                              {/* 2. Loại lệnh: In đậm (font-bold) & Màu sắc rõ ràng */}
                                              <td className={`p-4 font-bold ${log.type === 'BUY' ? 'text-emerald-600' : 'text-rose-500'}`}>{log.type}</td>
                                              
                                              {/* 3. Chi tiết: Chữ thường, màu đậm */}
                                              <td className="p-4 font-medium text-slate-700">{log.content}</td>
                                          </tr>
                                      ))}
                                  </tbody>
                              </table>
                          </div>
                      </div>
                  )}

                  {/* --- 4. NỘI DUNG TAB: DÒNG TIỀN (Đã chỉnh font to & rõ hơn) --- */}
                  {activeHistoryTab === 'cashflow' && (
                      <div className="animate-in fade-in zoom-in duration-300 max-w-3xl mx-auto">
                        <div className="mb-6 p-4 bg-emerald-50 rounded-xl border border-emerald-100 flex items-center justify-between shadow-sm">
                          <div>
                             <p className="text-xs text-emerald-600 font-bold uppercase mb-1 tracking-widest">Tiền mặt thực có</p>
                             <h3 className="text-2xl font-bold text-slate-800 tracking-tight">
                               {Math.floor(data?.cash_balance || 0).toLocaleString()} <span className="text-sm font-medium text-slate-400">vnd</span>
                             </h3>
                          </div>
                          <div className="p-3 bg-white rounded-lg text-emerald-500 shadow-sm"><Wallet size={24} /></div>
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
                                    {/* 1. NGÀY THÁNG: To hơn (text-sm) */}
                                    <div className="min-w-[60px] text-right pt-2">
                                        <p className="text-sm font-bold text-slate-500">{new Date(log.date).toLocaleDateString('vi-VN', {day: '2-digit', month: '2-digit'})}</p>
                                    </div>
                                    
                                    <div className="relative flex flex-col items-center self-stretch"><div className={`w-3 h-3 rounded-full mt-2 ${colorClass} z-10 ring-4 ring-white`}></div><div className="w-0.5 bg-slate-100 flex-1 -mt-1 group-last:hidden"></div></div>
                                    
                                    <div className={`flex-1 p-3 rounded-xl border border-slate-100 shadow-sm hover:shadow-md transition ${bgClass}`}>
                                       {/* 2. LOẠI LỆNH: To hơn (text-xs) */}
                                       <div className="flex justify-between items-start mb-1">
                                            <span className={`text-xs font-bold px-2 py-0.5 rounded-md bg-white/80 ${textClass}`}>{log.type}</span>
                                       </div>
                                       
                                       {/* 3. NỘI DUNG: To hơn (text-sm) & In đậm (font-bold) */}
                                       <p className="text-sm font-bold text-slate-700">{log.content}</p>
                                    </div>
                                  </div>
                                );
                              })
                            ) : (<div className="text-center p-10 text-slate-400 italic">Chưa có giao dịch tiền mặt.</div>)}
                        </div>
                      </div>
                  )}
            </div>
        </div>
        </div>
      </div>
      
            {/* MODAL: NẠP / RÚT TIỀN (Sửa Font chữ đen đậm + Nạp tiền) */}
      {(showDeposit || showWithdraw) && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl border border-emerald-100">
            <h2 className={`text-xl font-bold mb-6 ${showDeposit ? 'text-emerald-600' : 'text-purple-600'} uppercase`}>
              {showDeposit ? 'Nạp tiền' : 'Rút vốn'}
            </h2>
            <form onSubmit={showDeposit ? handleDeposit : handleWithdraw} className="space-y-6">
              <div>
                <label className="block text-[11px] font-medium text-gray-900 uppercase tracking-widest mb-2 ml-1 opacity-90">Số tiền muốn {showDeposit ? 'nạp' : 'rút'}</label>
                <div className="relative flex items-center">
                  <input type="text" required autoFocus className="w-full pl-4 pr-16 py-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-3xl font-medium text-slate-700 transition-all placeholder:text-slate-200"
                    value={amount} onChange={handleAmountChange} placeholder="0" />
                  <span className="absolute right-4 text-slate-400 font-bold text-sm pointer-events-none">VNĐ</span>
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-medium text-gray-900 uppercase tracking-widest mb-2 ml-1 opacity-90">Ghi chú giao dịch</label>
                <input type="text" className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-base font-medium text-slate-600 transition-all" 
                  value={description} onChange={(e) => setDescription(e.target.value)} placeholder="..." />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeModals} className="flex-1 py-3.5 bg-rose-100 text-rose-600 font-bold hover:bg-rose-200 rounded-xl transition text-sm">Hủy</button>
                <button type="submit" className={`flex-1 py-3.5 text-white font-bold rounded-xl shadow-lg shadow-emerald-100 active:scale-95 transition text-sm ${showDeposit ? 'bg-emerald-400 hover:bg-emerald-500' : 'bg-purple-600 hover:bg-purple-700'}`}>XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      
      {/* --- MODAL MUA CỔ PHIẾU (Đã chỉnh Layout: Thành tiền xuống dòng) --- */}
      {showBuy && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl border border-slate-100">
            <h2 className="text-xl font-medium mb-6 text-slate-800 uppercase tracking-tight">Mua Cổ Phiếu</h2>
            <form onSubmit={handleBuy} className="space-y-5">
              
              {/* 1. Mã Chứng Khoán - Chỉ cho phép nhập chữ, tự động viết hoa */}
                <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">
                    Mã Chứng Khoán
                  </label>
                  <div className="relative">
                    <input 
                      type="text" 
                      required 
                      autoFocus 
                      className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-sm font-bold text-slate-700 transition-all uppercase placeholder:text-slate-300" 
                      placeholder="VD: STB" 
                      value={buyForm.ticker} 
                      onChange={(e) => {
                        // Regex /[^a-zA-Z]/g sẽ loại bỏ tất cả ký tự KHÔNG phải là chữ cái (A-Z)
                        const val = e.target.value.replace(/[^a-zA-Z]/g, '').toUpperCase();
                        setBuyForm({ ...buyForm, ticker: val });
                      }} 
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-700 pointer-events-none">
                      Khả dụng: {Math.floor(data?.cash_balance || 0).toLocaleString()} 
                      <span className="text-[10px] text-slate-400 font-medium ml-1">VNĐ</span>
                    </span>
                  </div>
                </div>

              {/* 2. Grid 2 cột: Khối lượng & Giá */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Khối lượng</label>
                  <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-sm font-bold text-slate-700 transition-all" 
                    placeholder="100" value={buyForm.volume} onChange={(e) => handleVolumeChange(e, 'buy')} />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Giá Đặt Mua</label>
                  <div className="relative">
                    <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-sm font-bold text-slate-700 transition-all"
                        placeholder="0" value={buyForm.price} onChange={(e) => handlePriceChange(e, 'buy')} onBlur={() => handlePriceBlur('buy')} />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400 pointer-events-none">VNĐ</span>
                  </div>
                </div>
              </div>

              {/* 3. Hàng riêng: Thành tiền (Full width) */}
              <div className="pt-2"> {/* Thêm padding top để tách biệt chút */}
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Thành tiền (Dự kiến)</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      readOnly 
                      className="w-full p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl outline-none text-lg font-bold text-emerald-600 cursor-not-allowed"
                      value={(() => {
                        const vol = parseInt(buyForm.volume.replace(/,/g, '')) || 0;
                        const price = parseFloat(buyForm.price.replace(/,/g, '')) || 0;
                        const total = vol * price * (1 + (buyForm.fee_rate || 0)); 
                        return Math.floor(total).toLocaleString('en-US');
                      })()} 
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-emerald-600 pointer-events-none">VNĐ</span>
                  </div>
              </div>

              {/* Nút bấm */}
              <div className="flex gap-3 pt-4">
                <button type="button" onClick={closeModals} className="flex-1 py-3.5 bg-rose-100 text-rose-600 font-bold hover:bg-rose-200 rounded-xl transition text-sm">Hủy</button>
                <button type="submit" className="flex-1 py-3.5 bg-emerald-400 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-100 active:scale-95 transition text-sm">XÁC NHẬN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      
      {/* --- MODAL BÁN CỔ PHIẾU (Đã cập nhật giao diện đồng bộ với Mua) --- */}
      {showSell && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-2xl border border-rose-100">
            <h2 className="text-xl font-medium mb-6 text-slate-800 uppercase tracking-tight">Bán Cổ Phiếu</h2>
            <form onSubmit={handleSell} className="space-y-5">
              
              {/* 1. Mã Chứng Khoán (Readonly) */}
              <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Mã Chứng Khoán</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      readOnly // Thường là readonly khi bấm từ dòng
                      className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl outline-none text-sm font-bold text-slate-700 uppercase" 
                      value={sellForm.ticker} 
                      onChange={(e) => {
                          // Đề phòng trường hợp bạn gõ tay mã bán
                          const val = e.target.value.replace(/[^a-zA-Z]/g, '').toUpperCase();
                          setSellForm({...sellForm, ticker: val});
                      }}
                    />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-700 pointer-events-none">
                      Khả dụng: {sellForm.available?.toLocaleString()}
                    </span>
                  </div>
              </div>

              {/* 2. Grid 2 cột: Khối lượng & Giá */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Số lượng bán</label>
                  <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-sm font-bold text-slate-700 transition-all" 
                    value={sellForm.volume} onChange={(e) => handleVolumeChange(e, 'sell')} />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Giá Bán</label>
                  <div className="relative">
                    <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:bg-white outline-none text-sm font-bold text-slate-700 transition-all" 
                      placeholder="0" value={sellForm.price} onChange={(e) => handlePriceChange(e, 'sell')} onBlur={() => handlePriceBlur('sell')} />
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-400 pointer-events-none">VNĐ</span>
                  </div>
                </div>
              </div>

              {/* 3. Hàng riêng: Thành tiền thực nhận (Đã đổi sang màu XANH) */}
              <div className="pt-2">
                  <label className="block text-[11px] font-medium text-gray-900 uppercase mb-2 ml-1 tracking-widest opacity-90">Thành tiền (Dự kiến nhận)</label>
                  <div className="relative">
                    <input 
                      type="text" 
                      readOnly 
                      // Đổi class màu nền và chữ sang emerald (xanh)
                      className="w-full p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl outline-none text-lg font-bold text-emerald-600 cursor-not-allowed"
                      value={(() => {
                        const vol = parseInt(sellForm.volume.toString().replace(/,/g, '')) || 0;
                        const price = parseFloat(sellForm.price.toString().replace(/,/g, '')) || 0;
                        const total = vol * price * (1 - 0.0025); 
                        return Math.floor(total).toLocaleString('en-US');
                      })()} 
                    />
                    {/* Đổi màu chữ VNĐ sang emerald (xanh) */}
                    <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-emerald-600 pointer-events-none">VNĐ</span>
                  </div>
              </div>

              {/* Nút bấm (Đã đổi màu đồng bộ với form Mua) */}
              <div className="flex gap-3 pt-4">
                {/* Nút Hủy: Nền đỏ nhạt, chữ đỏ */}
                <button type="button" onClick={closeModals} className="flex-1 py-3.5 bg-rose-100 text-rose-600 font-bold hover:bg-rose-200 rounded-xl transition text-sm">Hủy</button>
                {/* Nút Xác nhận: Nền xanh, chữ trắng */}
                <button type="submit" className="flex-1 py-3.5 bg-emerald-400 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg shadow-emerald-100 active:scale-95 transition text-sm">XÁC NHẬN BÁN</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL XÁC NHẬN HOÀN TÁC (STYLE INFORMATION) --- */}
        {showUndoConfirm && (
          <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-[100] backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl border border-blue-100 transform animate-in zoom-in-95 duration-200">
              
              {/* Icon & Title */}
              <div className="flex items-center gap-4 mb-5">
                <div className="p-3 bg-blue-50 text-blue-600 rounded-xl">
                  <Activity size={24} /> 
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-800">Xác nhận hoàn tác</h3>
                  <p className="text-xs font-medium text-blue-500 uppercase tracking-wider">Hệ thống thông báo</p>
                </div>
              </div>

              {/* Nội dung */}
              <p className="text-slate-600 text-sm leading-relaxed mb-6">
                Bạn có chắc chắn muốn <span className="font-bold text-slate-800">hủy bỏ lệnh mua gần nhất</span>? Tiền và cổ phiếu sẽ được hoàn lại như trước khi khớp lệnh.
              </p>

              {/* Nút bấm */}
              <div className="flex gap-3">
                <button 
                  onClick={() => setShowUndoConfirm(false)}
                  className="flex-1 py-3 bg-slate-100 text-slate-600 font-bold rounded-xl hover:bg-slate-200 transition text-sm"
                >
                  Hủy bỏ
                </button>
                <button 
                  onClick={confirmUndo}
                  className="flex-1 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 shadow-lg shadow-blue-100 active:scale-95 transition text-sm"
                >
                  Xác nhận
                </button>
              </div>
            </div>
          </div>
        )}      
    {/* Thêm dòng này vào cuối file, trước </main> */}
      <Toaster 
        position="top-center" 
        richColors 
        expand={true}
        closeButton
        theme="light"
      />
      
    </main>
  );
}
// 1. Component SummaryCard (Đã thêm logic Blur)
// 1. Component SummaryCard (Đã chỉnh Font Đậm & Màu rõ nét)
// 1. Component SummaryCard (Đã thêm dấu phẩy ngăn cách & Font thanh mảnh)
function SummaryCard({ title, value, icon, color, bg, isPrivate, trends }) {
  
  // Logic: Nếu value là số (hoặc chuỗi số), tự động thêm dấu phẩy. 
  // Nếu là chữ thì giữ nguyên.
  const formattedValue = (value && !isNaN(String(value).replace(/,/g, ''))) 
    ? Number(String(value).replace(/,/g, '')).toLocaleString('en-US') 
    : value;

  return (
    <div className="bg-white p-6 rounded-2xl shadow-lg border border-emerald-100 hover:shadow-xl transition duration-200">
      <div className="flex justify-between items-start mb-4">
        <div>
           {/* TITLE: Giữ nguyên độ rõ nét */}
           <p className="text-xs font-bold text-emerald-900 uppercase tracking-widest mb-1 opacity-80">{title}</p>
           
           {/* VALUE: Đã sửa thành 'font-medium' (Thanh mảnh) và dùng 'formattedValue' (Có dấu phẩy) */}
           <h3 className={`text-2xl font-medium tracking-tight ${color}`}>
             {isPrivate ? '******' : formattedValue} 
             <span className="text-xs text-slate-400 font-bold ml-1">VNĐ</span>
           </h3>
        </div>
        <div className={`p-3 rounded-xl ${bg} ${color} shadow-sm`}>
          {icon}
        </div>
      </div>

      {/* TRENDS: Phần % Tăng giảm */}
      {trends && (
        <div className="grid grid-cols-4 gap-2 border-t border-slate-50 pt-3 mt-1">
          {trends.map((t, i) => (
            <div key={i} className="text-center">
              <p className="text-[10px] font-bold text-slate-600 uppercase mb-0.5">{t.label}</p>
              <p className={`text-[11px] font-bold ${t.value >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                {t.value > 0 ? '+' : ''}{t.value}%
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// 2. Component PerfBox (Đã thêm logic Blur)
function PerfBox({ label, data, isPrivate }) {
  const isProfit = (data?.val || 0) >= 0;
  const colorClass = isProfit ? "text-emerald-600" : "text-rose-500";

  return (
    <div className="p-6 text-center hover:bg-emerald-100 transition">
      <p className="text-gray-900 text-[11px] uppercase font-medium mb-3 tracking-[0.2em] opacity-90">
        {label}
      </p>
      
      {/* LOGIC CHE MỜ SỐ TIỀN */}
      <p className={`text-xl font-bold tracking-tighter transition-all duration-300 ${colorClass} ${isPrivate ? 'blur-md select-none opacity-50' : 'blur-0'}`}>
        {isProfit ? '+' : ''}{Math.floor(data?.val || 0).toLocaleString()}
      </p>
      
      {/* LOGIC CHE MỜ PHẦN TRĂM (NẾU MUỐN) */}
      <p className={`text-xs font-medium mt-1 opacity-80 ${colorClass} ${isPrivate ? 'blur-sm select-none' : ''}`}>
        ({isProfit ? '+' : ''}{data?.pct?.toFixed(2)}%)
      </p>
    </div>
  );
}