"use client";

import SummaryCard from './components/SummaryCard';
import PerfBox from './components/PerfBox';
import CashModal from './modals/CashModal';
import TradeModal from './modals/TradeModal';
import UndoModal from './modals/UndoModal';
import NoteModal from './modals/NoteModal';
import Header from './sections/Header';
import StockTable from './sections/StockTable';
import GrowthChart from './sections/GrowthChart';
import HistoryTabs from './sections/HistoryTabs';

import { useEffect, useState } from 'react';
import { 
  getPortfolio, depositMoney, withdrawMoney, 
  buyStock, sellStock, getAuditLog, 
  getHistorySummary, getPerformance, getHistoricalData, undoLastBuy, updateTransactionNote
} from '@/lib/api';

import { 
  Wallet, TrendingUp, RefreshCw, PlusCircle, 
  MinusCircle, Book, History, Eye, 
  EyeOff, Calendar, Activity, List, RotateCcw,
  PieChart as PieChartIcon 
} from 'lucide-react';

import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  PieChart, Pie, Cell 
} from 'recharts';

import { Toaster, toast } from 'sonner';

// --- CẤU HÌNH MÀU SẮC (Dành cho 10 mã cổ phiếu) ---
const PIE_COLORS = [
  '#16a34a', '#2563eb', '#ea580c', '#ca8a04', '#9333ea', 
  '#06b6d4', '#f43f5e', '#84cc16', '#64748b', '#1e40af'
];

const COLORS = [
  '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4',
  '#f43f5e', '#ea580c', '#84cc16', '#a855f7', '#14b8a6'
];

export default function Dashboard() {
  // 1. DỮ LIỆU CHÍNH TỪ BACKEND
  const [data, setData] = useState(null);           // Thông tin Portfolio & Holdings
  const [logs, setLogs] = useState([]);             // Nhật ký giao dịch tổng hợp
  const [perf, setPerf] = useState(null);           // Chỉ số hiệu suất 1D, 1M, YTD
  const [loading, setLoading] = useState(true);     // Trạng thái tải trang đầu tiên
  const [chartData, setChartData] = useState([]);   // Dữ liệu đã chuẩn hóa cho biểu đồ đường
  const [historicalProfit, setHistoricalProfit] = useState(null); // Kết quả tra cứu lãi/lỗ theo ngày
  const [navHistory, setNavHistory] = useState([]); // Lịch sử biến động NAV (nếu có)
  // 2. Thêm 2 state này vào trong hàm Dashboard()
 const [editingNote, setEditingNote] = useState({ id: null, content: '' });
 const [showNoteModal, setShowNoteModal] = useState(false);

  // 2. TRẠNG THÁI ĐIỀU KHIỂN GIAO DIỆN (UI)
  const [isPrivate, setIsPrivate] = useState(true);              // Chế độ ẩn/hiện số dư
  const [activeHistoryTab, setActiveHistoryTab] = useState('allocation'); // Tab Nhật ký đang chọn
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);    // Đóng/mở chọn mã so sánh
  const [chartRange, setChartRange] = useState('1m');             // Chu kỳ biểu đồ (1m, 3m, 1y)
  const [selectedComparisons, setSelectedComparisons] = useState(['PORTFOLIO', 'VNINDEX']); // Các đường trên biểu đồ

  // 3. TRẠNG THÁI ĐÓNG/MỞ CỬA SỔ (MODALS)
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [showBuy, setShowBuy] = useState(false);
  const [showSell, setShowSell] = useState(false);
  const [showUndoConfirm, setShowUndoConfirm] = useState(false);

  // 4. TRẠNG THÁI BIỂU MẪU (FORMS)
  const [amount, setAmount] = useState('');         // Số tiền nạp/rút
  const [description, setDescription] = useState(''); // Ghi chú giao dịch
  const [startDate, setStartDate] = useState('');   // Ngày bắt đầu tra cứu
  const [endDate, setEndDate] = useState('');       // Ngày kết thúc tra cứu
  
  // Form Mua cổ phiếu
  const [buyForm, setBuyForm] = useState({ 
    ticker: '', volume: '', price: '', fee_rate: 0.0015 , note: '' });
  
  // Form Bán cổ phiếu
  const [sellForm, setSellForm] = useState({ 
    ticker: '', volume: '', price: '', available: 0, note: ''
  });

  const handleUpdateNote = async () => {
    try {
        await updateTransactionNote(editingNote.id, editingNote.content);
        setShowNoteModal(false);
        fetchAllData(); // Tải lại nhật ký để thấy note mới
        toast.success('Đã lưu ghi chú');
    } catch (error) {
        toast.error('Không thể lưu ghi chú');
    }
    };

  {/* --- KẾT THÚC BLOCK I --- */}
  {/* ========================================================================================= */}
  {/* BLOCK II: CÁC HÀM HỖ TRỢ (HELPERS) & LOGIC CHUẨN HÓA DỮ LIỆU */}
  {/* ========================================================================================= */}

  // 1. Tự động kích hoạt chế độ ẩn số dư sau 5 phút không thao tác (Bảo mật)
  useEffect(() => {
    let timer;
    if (!isPrivate) {
      // 300,000ms = 5 phút
      timer = setTimeout(() => { 
        setIsPrivate(true); 
        toast.info('Chế độ riêng tư', { description: 'Số dư đã được ẩn tự động sau 15 giây.' });
      }, 15000); 
    }
    return () => clearTimeout(timer);
  }, [isPrivate]);


  /**
   * 2. Hàm normalizeData: Chuẩn hóa dữ liệu từ nhiều API (VN-Index & các mã CP)
   * Giúp đưa tất cả về cùng một mốc thời gian và tính toán % tăng trưởng từ ngày 0.
   */
  // page.js - BLOCK II
const normalizeData = (responses, tickers) => {
  // 1. Tìm bất kỳ mã nào có dữ liệu để làm mốc thời gian (X-Axis)
  // Ưu tiên VNINDEX, nếu không có thì lấy mã đầu tiên có data
  const validResponse = responses.find(r => r?.data && r.data.length > 0);
  if (!validResponse) {
    console.log("DEBUG: Không có dữ liệu để chuẩn hóa");
    return [];
  }

  const baseData = validResponse.data;
  const priceMaps = {};
  const firstPrices = {};

  // 2. Tạo bản đồ giá nhanh
  tickers.forEach((ticker, index) => {
    const stockData = responses[index]?.data || [];
    if (stockData.length > 0) {
      priceMaps[ticker] = {};
      stockData.forEach(item => {
        priceMaps[ticker][item.date] = item.close;
      });
      // Lấy giá đóng cửa đầu tiên để tính % tăng trưởng
      firstPrices[ticker] = stockData[0].close;
    }
  });

  // 3. Khớp dữ liệu vào mốc thời gian
  const result = baseData.map((item) => {
    const dateStr = item.date;
    const point = { date: dateStr.slice(5) }; // Hiện MM-DD

    tickers.forEach(ticker => {
      if (ticker === 'PORTFOLIO') {
        // Tạm thời lấy hiệu suất 1D để vẽ đường Portfolio
        point['PORTFOLIO'] = perf?.['1d']?.pct || 0;
      } else {
        const currentPrice = priceMaps[ticker]?.[dateStr];
        const startPrice = firstPrices[ticker];
        
        if (currentPrice && startPrice && startPrice !== 0) {
          const growth = ((currentPrice - startPrice) / startPrice) * 100;
          point[ticker] = parseFloat(growth.toFixed(2));
        } else {
          // Nếu ngày này mã đó kẹt giá, lấy bằng 0 hoặc Null để Recharts tự nối
          point[ticker] = 0; 
        }
      }
    });
    return point;
  });

  console.log("DEBUG: Dữ liệu biểu đồ sau chuẩn hóa:", result.length);
  return result;
};

  {/* --- KẾT THÚC BLOCK II --- */}
  // =========================================================================================
  // BLOCK III: LOGIC GỌI API (FETCH DATA & EFFECTS) - BẢN FIX LỖI XOAY BIỂU ĐỒ
  // =========================================================================================
  
  const fetchAllData = async () => {
    console.log("--- BẮT ĐẦU TẢI DỮ LIỆU DASHBOARD ---");
    try {
      // Nhóm Ưu tiên 1: Portfolio (Tiền mặt, Giá trị cổ phiếu, NAV)
      const resP = await getPortfolio();
      if (resP?.data) {
        setData(resP.data);
        console.log("DEBUG: Đã nhận dữ liệu Portfolio");
      }
      
      // Tắt màn hình loading chính ngay khi có Portfolio
      setLoading(false); 

      // Nhóm Ưu tiên 2: Chạy song song ngầm (Background)
      getAuditLog().then(resL => {
        if (resL?.data) setLogs(resL.data);
      }).catch(err => console.error("Lỗi tải Nhật ký:", err));

      getPerformance().then(resEf => {
        if (resEf?.data) setPerf(resEf.data);
      }).catch(err => console.error("Lỗi tải Hiệu suất:", err));

      // Lấy lịch sử NAV (nếu Backend đã có hàm này)
      if (typeof getNavHistory === 'function') {
        getNavHistory(20).then(res => {
          if(res?.data) setNavHistory(res.data);
        }).catch(() => {});
      }

    } catch (error) {
      console.error("LỖI KẾT NỐI BACKEND:", error);
      setLoading(false); 
    }
  };

  /**
   * 2. Effect khởi tạo: Chạy 1 lần duy nhất và lập lịch làm mới 30s
   */
  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  /**
   * 3. Effect Biểu đồ: Xử lý dứt điểm lỗi xoay tròn
   */
  useEffect(() => {
    const fetchChart = async () => {
      try {
        console.log("--- ĐANG TẢI DỮ LIỆU BIỂU ĐỒ ---");
        
        // Lọc danh sách mã cần gọi (trừ Portfolio)
        const apiTargets = selectedComparisons.filter(t => t !== 'PORTFOLIO');
        
        // Luôn đảm bảo có ít nhất 1 mã để lấy mốc thời gian
        const effectiveTargets = apiTargets.length > 0 ? apiTargets : ['VNINDEX'];

        const requests = effectiveTargets.map(ticker => getHistoricalData(ticker, chartRange));
        const responses = await Promise.all(requests);

        // Chuẩn hóa dữ liệu qua BLOCK II
        const finalData = normalizeData(responses, effectiveTargets);
        
        if (finalData && finalData.length > 0) {
          setChartData(finalData);
          console.log(`DEBUG: Đã vẽ biểu đồ với ${finalData.length} điểm dữ liệu`);
        } else {
          // NẾU RỖNG: Set mảng có dữ liệu mồi để thoát vòng xoay Loading
          console.log("WARNING: Dữ liệu rỗng, thoát xoay loading");
          setChartData([{ date: 'N/A', VNINDEX: 0 }]);
        }
      } catch (error) {
        console.error("LỖI FETCH BIỂU ĐỒ:", error);
        // Lỗi cũng phải thoát xoay
        setChartData([{ date: 'Lỗi', VNINDEX: 0 }]);
      }
    };

    // Chỉ gọi fetchChart khi Dashboard đã có dữ liệu Portfolio
    if (data) {
      fetchChart();
    }
  }, [selectedComparisons, chartRange, data]);

  // --- KẾT THÚC BLOCK III ---
  
  {/* ========================================================================================= */}
  {/* BLOCK IV: HÀM XỬ LÝ SỰ KIỆN (MUA, BÁN, NẠP, RÚT, HOÀN TÁC) */}
  {/* ========================================================================================= */}

  // --- 1. NHÓM XỬ LÝ HOÀN TÁC (UNDO) ---
  const handleUndo = () => setShowUndoConfirm(true); // Mở Modal xác nhận

  const confirmUndo = async () => {
    setShowUndoConfirm(false);
    try {
      const res = await undoLastBuy();
      fetchAllData(); // Refresh lại toàn bộ Dashboard
      toast.success('Hoàn tác thành công', { 
        description: res.data.message 
      });
    } catch (error) {
      toast.error('Không thể hoàn tác', { 
        description: error.response?.data?.detail || 'Lỗi hệ thống.' 
      });
    }
  };

  // --- 2. NHÓM XỬ LÝ TIỀN MẶT (CASH ACTIONS) ---
  const handleDeposit = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const cleanAmount = parseFloat(amount.replace(/,/g, ''));
      await depositMoney({ amount: cleanAmount, description });
      closeModals(); 
      fetchAllData();
      toast.success('Nạp tiền thành công', { 
        description: `Đã cộng ${amount} VND vào tài khoản.` 
      });
    } catch (error) {
      toast.error('Lỗi nạp tiền', { description: error.response?.data?.detail });
    }
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const cleanAmount = parseFloat(amount.replace(/,/g, ''));
      await withdrawMoney({ amount: cleanAmount, description });
      closeModals(); 
      fetchAllData();
      toast.success('Rút vốn thành công', { 
        description: `Đã trừ ${amount} VND khỏi tài khoản.` 
      });
    } catch (error) {
      toast.error('Rút vốn thất bại', { 
        description: error.response?.data?.detail || 'Vui lòng kiểm tra lại số dư.' 
      });
    }
  };

  {/* --- 3. NHÓM XỬ LÝ GIAO DỊCH CỔ PHIẾU (TRADING ACTIONS) --- */}
  {/* ========================================================================================= */}
  {/* BLOCK V: HÀM XỬ LÝ SỰ KIỆN (MUA, BÁN, NẠP, RÚT, HOÀN TÁC) */}
  {/* ========================================================================================= */}
  const handleBuy = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(buyForm.price.toString().replace(/,/g, ''));
      const cleanVolume = parseInt(buyForm.volume.toString().replace(/,/g, ''));
      
      await buyStock({ ...buyForm, volume: cleanVolume, price: cleanPrice });
      closeModals(); 
      fetchAllData();
      toast.success('Khớp lệnh MUA thành công', { 
        description: `Mua ${cleanVolume.toLocaleString()} ${buyForm.ticker} giá ${cleanPrice.toLocaleString()}.` 
      });
    } catch (error) {
      toast.error('Lệnh mua bị từ chối', { 
        description: error.response?.data?.detail || 'Vui lòng kiểm tra số dư tiền mặt.' 
      });
    }
  };

  const handleSell = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(sellForm.price.toString().replace(/,/g, ''));
      const cleanVolume = parseInt(sellForm.volume.toString().replace(/,/g, ''));
      
      await sellStock({ ...sellForm, volume: cleanVolume, price: cleanPrice });
      closeModals(); 
      fetchAllData();
      toast.success('Khớp lệnh BÁN thành công', { 
        description: `Bán ${cleanVolume.toLocaleString()} ${sellForm.ticker} giá ${cleanPrice.toLocaleString()}.` 
      });
    } catch (error) {
      toast.error('Lệnh bán bị từ chối', { 
        description: error.response?.data?.detail || 'Không đủ số lượng cổ phiếu.' 
      });
    }
  };

  {/* --- 4. CÁC HÀM TIỆN ÍCH CHO FORM (UI HELPERS) --- */}
  {/* ========================================================================================= */}
  {/* BLOCK VI: HÀM XỬ LÝ SỰ KIỆN (MUA, BÁN, NẠP, RÚT, HOÀN TÁC) */}
  {/* ========================================================================================= */}
  const closeModals = () => {
    setShowDeposit(false); setShowWithdraw(false); 
    setShowBuy(false); setShowSell(false);
    setAmount(''); setDescription('');
    // Reset note về rỗng
    setBuyForm({ ticker: '', volume: '', price: '', fee_rate: 0.0015, note: '' });
    setSellForm({ ticker: '', volume: '', price: '', available: 0, note: '' });
  };

  const handleAmountChange = (e) => {
    {/* Chỉ cho nhập số, tự động thêm dấu phẩy ngăn cách hàng nghìn */}
    const rawValue = e.target.value.replace(/[^0-9]/g, '');
    if (!rawValue) { setAmount(''); return; }
    setAmount(new Intl.NumberFormat('en-US').format(rawValue));
  };

  const handleVolumeChange = (e, type) => {
    const raw = e.target.value.replace(/[^0-9]/g, '');
    const formatted = raw ? new Intl.NumberFormat('en-US').format(raw) : '';
    if (type === 'buy') setBuyForm({ ...buyForm, volume: formatted });
    else setSellForm({ ...sellForm, volume: formatted });
  };

  const handlePriceChange = (e, type) => {
    // Chấp nhận số và dấu chấm/phẩy cho giá
    const val = e.target.value;
    if (/^[\d,.]*$/.test(val)) {
        if (type === 'buy') setBuyForm({ ...buyForm, price: val });
        else setSellForm({ ...sellForm, price: val });
    }
  };

  const handlePriceBlur = (type) => {
    // Tự động nhân 1000 nếu người dùng nhập giá lẻ (VD: gõ 12.5 -> 12,500)
    const form = type === 'buy' ? buyForm : sellForm;
    let valStr = form.price.toString().replace(/,/g, ''); 
    let val = parseFloat(valStr);
    if (!val) return;
    if (val < 1000) val = val * 1000;
    const formatted = new Intl.NumberFormat('en-US').format(val);
    if (type === 'buy') setBuyForm({ ...buyForm, price: formatted });
    else setSellForm({ ...sellForm, price: formatted });
  };

  // --- 5. LOGIC BIỂU ĐỒ & TRA CỨU ---
  const toggleComparison = (ticker) => {
    if (selectedComparisons.includes(ticker)) {
      setSelectedComparisons(selectedComparisons.filter(t => t !== ticker));
    } else {
      if (selectedComparisons.length >= 5) {
        toast.warning('Giới hạn so sánh', { description: 'Chỉ được chọn tối đa 5 đường cùng lúc.' });
        return;
      }
      setSelectedComparisons([...selectedComparisons, ticker]);
    }
  };

  const handleCalculateProfit = async () => {
    if (!startDate || !endDate) {
      toast.info('Thông tin thiếu', { description: 'Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc.' });
      return;
    }
    const res = await getHistorySummary(startDate, endDate);
    setHistoricalProfit(res.data);
    toast.success('Đã cập nhật dữ liệu đối soát.');
  };

  

  // Lấy danh sách các mã đang nắm giữ để đưa vào bộ lọc so sánh
  const holdingTickers = data?.holdings?.map(h => h.ticker) || [];

  {/* --- KẾT THÚC BLOCK IV --- */}
  {/* ========================================================================================= */}
  {/* BLOCK V: HIỆU ỨNG LOADING VÀ PHẦN ĐẦU TRANG (HEADER & QUICK ACTIONS) */}
  {/* ========================================================================================= */}

  {/* 1. Màn hình chờ (Loading Screen) - Chỉ hiện khi lần đầu tải trang và chưa có data */}
  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f8fafc]">
        <div className="text-center">
          {/* Vòng xoay Spinner phong cách hiện đại */}
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-emerald-100 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
          </div>
          
          {/* Thông báo trạng thái */}
          <h2 className="text-xl font-bold text-emerald-900 tracking-tight mb-2 uppercase italic">INVEST JOURNAL</h2>
          <div className="flex items-center justify-center gap-2 text-emerald-600 font-medium animate-pulse">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-sm tracking-widest uppercase">Đang kết nối hệ thống...</span>
          </div>
          
          <p className="mt-8 text-slate-400 text-xs font-medium uppercase tracking-[0.3em]">v1.1.0 - Docker Stable</p>
        </div>
      </div>
    );
  }

  // 2. Bắt đầu Render giao diện chính
  return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-8 font-sans text-slate-900">
      <div className="max-w-7xl mx-auto">
        {/* ========================================================================================= */}
        {/* BLOCK V: PHẦN ĐẦU TRANG (HEADER & QUICK ACTIONS) - ĐÃ TÁCH SANG SECTIONS/HEADER.JS        */}
        {/* ========================================================================================= */}
        <Header {...{isPrivate, setIsPrivate, setShowDeposit, setShowWithdraw, setShowBuy, fetchAllData, handleUndo}} />

        {/* ========================================================================================= */}
        {/* BLOCK VI: CÁC THẺ TỔNG QUAN (SUMMARY CARDS) & HIỆU SUẤT THEO MỐC THỜI GIAN                 */}
        {/* ========================================================================================= */}
        
        {/* --- 1. CỤM THẺ TỔNG QUAN TÀI SẢN (Sử dụng Grid 3 cột) --- */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          
          {/* Thẻ Vốn thực có (NAV) - Màu Tím */}
          <SummaryCard 
            isPrivate={isPrivate}
            title="Vốn thực có (NAV)" 
            value={Math.floor(data?.total_nav || 0)}
            icon={<PieChartIcon size={26}/>} 
            color="text-purple-600" 
            bg="bg-purple-50" 
          />

          {/* Thẻ Tiền mặt - Màu Xanh Emerald */}
          <SummaryCard 
            isPrivate={isPrivate}
            title="Tiền mặt" 
            value={Math.floor(data?.cash_balance || 0)} 
            icon={<Wallet size={26}/>} 
            color="text-emerald-600" 
            bg="bg-emerald-50" 
          />

          {/* Thẻ Giá trị cổ phiếu - Màu Hồng Fuchsia */}
          <SummaryCard 
            isPrivate={isPrivate}
            title="Giá trị cổ phiếu" 
            value={Math.floor(data?.total_stock_value || 0)} 
            icon={<TrendingUp size={26}/>} 
            color="text-fuchsia-600" 
            bg="bg-fuchsia-50" 
          />
        </div>

        {/* BLOCK VII: BIỂU ĐỒ TĂNG TRƯỞNG (%) - ĐÃ TÁCH SANG SECTIONS/GROWTHCHART.JS                */}
        {/* ========================================================================================= */}
        <GrowthChart {...{chartData, chartRange, setChartRange, isDropdownOpen, setIsDropdownOpen, selectedComparisons, holdingTickers, toggleComparison}} />
        {/* ========================================================================================= */}
        {/* BLOCK VIII: DANH MỤC CỔ PHIẾU HIỆN TẠI - CHI TIẾT TỪNG MÃ & TỶ TRỌNG */}
        {/* ========================================================================================= */}
        <StockTable {...{data, buyForm, setBuyForm, sellForm, setSellForm, setShowBuy, setShowSell}} />
        {/* ========================================================================================= */}
        {/* BLOCK IX: NHẬT KÝ DỮ LIỆU - ĐÃ TÁCH SANG SECTIONS/HISTORYTABS.JS                         */}
        {/* ========================================================================================= */}
        <HistoryTabs {...{ activeHistoryTab, setActiveHistoryTab, startDate, setStartDate, endDate, setEndDate, handleCalculateProfit, data, PIE_COLORS,
         historicalProfit, navHistory, logs, setEditingNote, setShowNoteModal }} />       
        {/* ========================================================================================= */}
        {/* BLOCK X: HỆ THỐNG CỬA SỔ (MODALS) - ĐÃ ĐƯỢC TÁCH FILE RIÊNG                               */}
        {/* ========================================================================================= */}
        <CashModal {...{showDeposit, showWithdraw, amount, setAmount, description, setDescription, handleAmountChange, handleDeposit, handleWithdraw, closeModals}} />

        <TradeModal {...{showBuy, showSell, buyForm, setBuyForm, sellForm, setSellForm, handleBuy, handleSell, handleVolumeChange, handlePriceChange, handlePriceBlur, closeModals, data}} />

        <UndoModal {...{showUndoConfirm, setShowUndoConfirm, confirmUndo}} />

        <NoteModal {...{showNoteModal, setShowNoteModal, editingNote, setEditingNote, handleUpdateNote}} />
        
        <Toaster position="top-center" richColors expand={true} closeButton theme="light" />
   
    </div>  {/* Đóng max-w-7xl */}
  </main> 
  ); {/* Đóng return */}
} {/* Đóng Dashboard function */}