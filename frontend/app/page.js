"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { RefreshCw, Wallet, TrendingUp, PieChart as PieChartIcon } from "lucide-react";
import { Toaster, toast } from "sonner";

import SummaryCard from "./components/SummaryCard";
import PerfBox from "./components/PerfBox";
import CashModal from "./modals/CashModal";
import TradeModal from "./modals/TradeModal";
import UndoModal from "./modals/UndoModal";
import NoteModal from "./modals/NoteModal";

import Header from "./sections/Header";
import StockTable from "./sections/StockTable";

import GrowthChart from "./sections/GrowthChart";
const HistoryTabs = dynamic(() => import("./sections/HistoryTabs"), { ssr: false });
const WatchlistPro = dynamic(() => import("./sections/WatchlistPro"), { ssr: false });

import {
  getPortfolio,
  depositMoney,
  withdrawMoney,
  buyStock,
  sellStock,
  getAuditLog,
  getHistorySummary,
  getPerformance,
  getHistoricalData,
  getChartGrowth,
  getNavHistory,
  undoLastBuy,
  updateTransactionNote,
} from "@/lib/api";

// --- CẤU HÌNH MÀU SẮC (Dành cho 10 mã cổ phiếu) ---
const PIE_COLORS = [
  "#16a34a",
  "#2563eb",
  "#ea580c",
  "#ca8a04",
  "#9333ea",
  "#06b6d4",
  "#f43f5e",
  "#84cc16",
  "#64748b",
  "#1e40af",
];

// -----------------------------
// Helpers: normalize chart data
// -----------------------------
const normalizeData = (responses, stockTickers, chartTickers, portfolioSeries = []) => {
  // Map PORTFOLIO: { 'YYYY-MM-DD': close% }
  const portfolioMap = {};
  if (Array.isArray(portfolioSeries)) {
    portfolioSeries.forEach((p) => {
      if (p?.date != null) portfolioMap[p.date] = p.PORTFOLIO;
    });
  }

  // Base timeline: ưu tiên PORTFOLIO series, nếu không có thì lấy từ historical
  let baseData = null;
  if (portfolioSeries && portfolioSeries.length > 0) {
    baseData = portfolioSeries.map((p) => ({ date: p.date }));
  } else {
    const validResponse = responses.find((r) => r?.data && r.data.length > 0);
    if (!validResponse) return [];
    baseData = validResponse.data;
  }

  // Build price maps cho các mã cổ phiếu
  const priceMaps = {};
  const firstPrices = {};

  stockTickers.forEach((ticker, index) => {
    const stockData = responses[index]?.data || [];
    if (stockData.length > 0) {
      priceMaps[ticker] = {};
      stockData.forEach((item) => {
        priceMaps[ticker][item.date] = item.close;
      });
      firstPrices[ticker] = stockData[0].close;
    }
  });

  // Merge ra chartData
  return baseData.map((item) => {
    const dateStr = item.date; // YYYY-MM-DD
    const point = { date: dateStr }; // Full date for tooltip calculation

    chartTickers.forEach((ticker) => {
      if (ticker === "PORTFOLIO") {
        point.PORTFOLIO = Number(portfolioMap[dateStr] ?? 0);
        return;
      }

      const currentPrice = priceMaps[ticker]?.[dateStr];
      const startPrice = firstPrices[ticker];

      if (currentPrice != null && startPrice != null && startPrice !== 0) {
        const growth = ((currentPrice - startPrice) / startPrice) * 100;
        point[ticker] = parseFloat(growth.toFixed(2));
      } else {
        point[ticker] = 0;
      }
    });

    return point;
  });
};

export default function Dashboard() {
  // 1) DỮ LIỆU CHÍNH
  const [data, setData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [perf, setPerf] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeMainTab, setActiveMainTab] = useState("watchlist"); // 'watchlist' hoặc 'growth'
  const [chartData, setChartData] = useState([]);
  const [historicalProfit, setHistoricalProfit] = useState(null);
  const [navHistory, setNavHistory] = useState([]);
  const [portfolioLastUpdated, setPortfolioLastUpdated] = useState(new Date());

  // Note modal
  const [editingNote, setEditingNote] = useState({ id: null, content: "" });
  const [showNoteModal, setShowNoteModal] = useState(false);

  // 2) UI STATE
  const [isPrivate, setIsPrivate] = useState(true);
  const [activeHistoryTab, setActiveHistoryTab] = useState("allocation");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [chartRange, setChartRange] = useState("1m");
  const [selectedComparisons, setSelectedComparisons] = useState(["PORTFOLIO", "VNINDEX"]);

  // 3) MODALS
  const [showDeposit, setShowDeposit] = useState(false);
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [showBuy, setShowBuy] = useState(false);
  const [showSell, setShowSell] = useState(false);
  const [showUndoConfirm, setShowUndoConfirm] = useState(false);

  // 4) FORMS
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [startDate, setStartDate] = useState(new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toLocaleDateString('en-CA'));
  const [endDate, setEndDate] = useState(new Date().toLocaleDateString('en-CA'));

  const [buyForm, setBuyForm] = useState({
    ticker: "",
    volume: "",
    price: "",
    fee_rate: 0.0015,
    note: "",
  });

  const [sellForm, setSellForm] = useState({
    ticker: "",
    volume: "",
    price: "",
    available: 0,
    note: "",
  });

  // -----------------------------
  // Auto privacy after 5 minutes
  // -----------------------------
  useEffect(() => {
    let timer;
    if (!isPrivate) {
      timer = setTimeout(() => {
        setIsPrivate(true);
        toast.info("Chế độ riêng tư", {
          description: "Số dư đã được ẩn tự động sau 5 phút.",
        });
      }, 300000); // 5 phút
    }
    return () => clearTimeout(timer);
  }, [isPrivate]);

  // -----------------------------
  // Fetch Dashboard Core Data
  // -----------------------------
  const fetchAllData = React.useCallback(async () => {
    try {
      const resP = await getPortfolio();
      if (resP?.data) {
        setData(resP.data);
        setPortfolioLastUpdated(new Date());
      }

      setLoading(false);

      getAuditLog()
        .then((resL) => {
          if (resL?.data) setLogs(resL.data);
        })
        .catch((err) => console.error("Lỗi tải Nhật ký:", err));

      getPerformance()
        .then((resEf) => {
          if (resEf?.data) setPerf(resEf.data);
        })
        .catch((err) => console.error("Lỗi tải Hiệu suất:", err));

      if (typeof getNavHistory === "function") {
        getNavHistory(startDate, endDate)
          .then((res) => {
            if (res?.data) setNavHistory(res.data);
          })
          .catch(() => { });
      }
    } catch (error) {
      console.error("LỖI KẾT NỐI BACKEND:", error);
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 10000);
    return () => clearInterval(interval);
  }, [fetchAllData]);

  const fetchChart = React.useCallback(async () => {
    try {
      const wantPortfolio = selectedComparisons.includes("PORTFOLIO");
      let portfolioSeries = [];
      if (wantPortfolio) {
        try {
          const resG = await getChartGrowth(chartRange);
          portfolioSeries = resG?.data?.portfolio || [];
        } catch (e) {
          console.warn("Không lấy được chart-growth:", e);
          portfolioSeries = [];
        }
      }
      const stockTickers = selectedComparisons.filter((t) => t !== "PORTFOLIO");
      const effectiveStockTickers = stockTickers.length > 0 ? stockTickers : portfolioSeries.length > 0 ? [] : ["VNINDEX"];
      const responses = await Promise.all(
        effectiveStockTickers.map((ticker) => getHistoricalData(ticker, chartRange))
      );
      const finalData = normalizeData(responses, effectiveStockTickers, selectedComparisons, portfolioSeries);
      setChartData(finalData?.length ? finalData : [{ date: "N/A", VNINDEX: 0, PORTFOLIO: 0 }]);
    } catch (error) {
      console.error("LỖI FETCH BIỂU ĐỒ:", error);
      setChartData([{ date: "Lỗi", VNINDEX: 0, PORTFOLIO: 0 }]);
    }
  }, [chartRange, selectedComparisons]);

  useEffect(() => {
    fetchChart();
  }, [fetchChart]);

  // -----------------------------
  // Actions
  // -----------------------------
  const closeModals = () => {
    setShowDeposit(false);
    setShowWithdraw(false);
    setShowBuy(false);
    setShowSell(false);

    setAmount("");
    setDescription("");

    setBuyForm({ ticker: "", volume: "", price: "", fee_rate: 0.0015, note: "" });
    setSellForm({ ticker: "", volume: "", price: "", available: 0, note: "" });
  };

  const handleAmountChange = (e) => {
    // Chỉ cho nhập số, tự động thêm dấu phẩy ngăn cách hàng nghìn
    const rawValue = e.target.value.replace(/[^0-9]/g, "");
    if (!rawValue) {
      setAmount("");
      return;
    }
    setAmount(new Intl.NumberFormat("en-US").format(rawValue));
  };

  const handleVolumeChange = (e, type) => {
    const raw = e.target.value.replace(/[^0-9]/g, "");
    const formatted = raw ? new Intl.NumberFormat("en-US").format(raw) : "";
    if (type === "buy") setBuyForm({ ...buyForm, volume: formatted });
    else setSellForm({ ...sellForm, volume: formatted });
  };

  const handlePriceChange = (e, type) => {
    const val = e.target.value;
    if (/^[\d,.]*$/.test(val)) {
      if (type === "buy") setBuyForm({ ...buyForm, price: val });
      else setSellForm({ ...sellForm, price: val });
    }
  };

  const handlePriceBlur = (type) => {
    const form = type === "buy" ? buyForm : sellForm;
    let valStr = form.price.toString().replace(/,/g, "");
    let val = parseFloat(valStr);
    if (!val) return;
    if (val < 1000) val = val * 1000;
    const formatted = new Intl.NumberFormat("en-US").format(val);
    if (type === "buy") setBuyForm({ ...buyForm, price: formatted });
    else setSellForm({ ...sellForm, price: formatted });
  };

  const handleUndo = () => setShowUndoConfirm(true);

  const confirmUndo = async () => {
    setShowUndoConfirm(false);
    try {
      const res = await undoLastBuy();
      fetchAllData();
      toast.success("Hoàn tác thành công", { description: res.data.message });
    } catch (error) {
      toast.error("Không thể hoàn tác", {
        description: error.response?.data?.detail || "Lỗi hệ thống.",
      });
    }
  };

  const handleDeposit = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const cleanAmount = parseFloat(amount.replace(/,/g, ""));
      await depositMoney({ amount: cleanAmount, description });
      closeModals();
      fetchAllData();
      toast.success("Nạp tiền thành công", {
        description: `Đã cộng ${amount} VND vào tài khoản.`,
      });
    } catch (error) {
      toast.error("Lỗi nạp tiền", { description: error.response?.data?.detail });
    }
  };

  const handleWithdraw = async (e) => {
    e.preventDefault();
    if (!amount) return;
    try {
      const cleanAmount = parseFloat(amount.replace(/,/g, ""));
      await withdrawMoney({ amount: cleanAmount, description });
      closeModals();
      fetchAllData();
      toast.success("Rút vốn thành công", {
        description: `Đã trừ ${amount} VND khỏi tài khoản.`,
      });
    } catch (error) {
      toast.error("Rút vốn thất bại", {
        description: error.response?.data?.detail || "Vui lòng kiểm tra lại số dư.",
      });
    }
  };

  const handleBuy = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(buyForm.price.toString().replace(/,/g, ""));
      const cleanVolume = parseInt(buyForm.volume.toString().replace(/,/g, ""), 10);

      await buyStock({ ...buyForm, volume: cleanVolume, price: cleanPrice });
      closeModals();
      fetchAllData();
      toast.success("Khớp lệnh MUA thành công", {
        description: `Mua ${cleanVolume.toLocaleString()} ${buyForm.ticker} giá ${cleanPrice.toLocaleString()}.`,
      });
    } catch (error) {
      toast.error("Lệnh mua bị từ chối", {
        description: error.response?.data?.detail || "Vui lòng kiểm tra số dư tiền mặt.",
      });
    }
  };

  const handleSell = async (e) => {
    e.preventDefault();
    try {
      const cleanPrice = parseFloat(sellForm.price.toString().replace(/,/g, ""));
      const cleanVolume = parseInt(sellForm.volume.toString().replace(/,/g, ""), 10);

      await sellStock({ ...sellForm, volume: cleanVolume, price: cleanPrice });
      closeModals();
      fetchAllData();
      toast.success("Khớp lệnh BÁN thành công", {
        description: `Bán ${cleanVolume.toLocaleString()} ${sellForm.ticker} giá ${cleanPrice.toLocaleString()}.`,
      });
    } catch (error) {
      toast.error("Lệnh bán bị từ chối", {
        description: error.response?.data?.detail || "Không đủ số lượng cổ phiếu.",
      });
    }
  };

  const toggleComparison = (ticker) => {
    if (selectedComparisons.includes(ticker)) {
      setSelectedComparisons(selectedComparisons.filter((t) => t !== ticker));
    } else {
      if (selectedComparisons.length >= 5) {
        toast.warning("Giới hạn so sánh", {
          description: "Chỉ được chọn tối đa 5 đường cùng lúc.",
        });
        return;
      }
      setSelectedComparisons([...selectedComparisons, ticker]);
    }
  };

  const handleCalculateProfit = async () => {
    if (!startDate || !endDate) {
      toast.info("Thông tin thiếu", { description: "Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc." });
      return;
    }
    const res = await getHistorySummary(startDate, endDate);
    setHistoricalProfit(res.data);

    // Đồng thời cập nhật luôn bảng NAV History theo khoảng ngày này
    try {
      const resNav = await getNavHistory(startDate, endDate);
      if (resNav?.data) setNavHistory(resNav.data);
    } catch (e) {
      console.error("Lỗi cập nhật NAV History:", e);
    }

    toast.success("Đã cập nhật dữ liệu đối soát.");
  };

  useEffect(() => {
    handleCalculateProfit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpdateNote = async () => {
    try {
      await updateTransactionNote(editingNote.id, editingNote.content);
      setShowNoteModal(false);
      fetchAllData();
      toast.success("Đã lưu ghi chú");
    } catch (error) {
      toast.error("Không thể lưu ghi chú");
    }
  };

  // Holding tickers để dropdown so sánh
  const holdingTickers = data?.holdings?.map((h) => h.ticker) || [];

  // -----------------------------
  // Loading Screen
  // -----------------------------
  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f8fafc]">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-emerald-100 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
          </div>

          <h2 className="text-xl font-bold text-emerald-900 tracking-tight mb-2 uppercase italic">
            INVEST JOURNAL
          </h2>
          <div className="flex items-center justify-center gap-2 text-emerald-600 font-medium animate-pulse">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-sm tracking-widest uppercase">Đang kết nối hệ thống...</span>
          </div>

          <p className="mt-8 text-slate-400 text-xs font-medium uppercase tracking-[0.3em]">
            v1.1.0 - Docker Stable
          </p>
        </div>
      </div>
    );
  }

  // -----------------------------
  // Main UI
  // -----------------------------
  return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-6 font-sans text-slate-900">
      <div className="max-w-7xl mx-auto">
        <Header
          {...{
            isPrivate,
            setIsPrivate,
            setShowDeposit,
            setShowWithdraw,
            setShowBuy,
            fetchAllData,
            handleUndo,
          }}
        />


        {/* SUMMARY */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <SummaryCard
            isPrivate={isPrivate}
            title="Vốn thực có (NAV)"
            value={Math.floor(data?.total_nav || 0)}
            icon={<PieChartIcon size={26} />}
            color="text-purple-600"
            bg="bg-purple-50"
          />

          <SummaryCard
            isPrivate={isPrivate}
            title="Tiền mặt"
            value={Math.floor(data?.cash_balance || 0)}
            icon={<Wallet size={26} />}
            color="text-emerald-600"
            bg="bg-emerald-50"
          />

          <SummaryCard
            isPrivate={isPrivate}
            title="Giá trị cổ phiếu"
            value={Math.floor(data?.total_stock_value || 0)}
            icon={<TrendingUp size={26} />}
            color="text-fuchsia-600"
            bg="bg-fuchsia-50"
          />
        </div>

        {/* MAIN CONTENT TABS (Watchlist / Growth) */}
        <div className="mb-6">
          <div className="flex items-center gap-1 p-1 bg-slate-100/50 rounded-2xl w-fit mb-4 border border-slate-400">
            <button
              onClick={() => setActiveMainTab("watchlist")}
              className={`px-6 py-2.5 rounded-xl text-xs font-black uppercase transition-all ${activeMainTab === "watchlist" ? "bg-white text-emerald-600 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
            >
              Watchlist Pro
            </button>
            <button
              onClick={() => setActiveMainTab("growth")}
              className={`px-6 py-2.5 rounded-xl text-xs font-black uppercase transition-all ${activeMainTab === "growth" ? "bg-white text-emerald-600 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
            >
              Hiệu suất tăng trưởng
            </button>
          </div>

          {activeMainTab === "growth" ? (
            <GrowthChart
              {...{
                chartData,
                chartRange,
                setChartRange,
                isDropdownOpen,
                setIsDropdownOpen,
                selectedComparisons,
                holdingTickers,
                toggleComparison,
                totalNav: data?.total_nav,
              }}
            />
          ) : (
            <WatchlistPro />
          )}
        </div>

        {/* TABLE */}
        <StockTable {...{ data, buyForm, setBuyForm, sellForm, setSellForm, setShowBuy, setShowSell, lastUpdated: portfolioLastUpdated }} />

        {/* HISTORY */}
        <HistoryTabs
          {...{
            activeHistoryTab,
            setActiveHistoryTab,
            startDate,
            setStartDate,
            endDate,
            setEndDate,
            handleCalculateProfit,
            data,
            PIE_COLORS,
            historicalProfit,
            navHistory,
            logs,
            setEditingNote,
            setShowNoteModal,
          }}
        />

        {/* MODALS */}
        <CashModal
          {...{
            showDeposit,
            showWithdraw,
            amount,
            setAmount,
            description,
            setDescription,
            handleAmountChange,
            handleDeposit,
            handleWithdraw,
            closeModals,
          }}
        />

        <TradeModal
          {...{
            showBuy,
            showSell,
            buyForm,
            setBuyForm,
            sellForm,
            setSellForm,
            handleBuy,
            handleSell,
            handleVolumeChange,
            handlePriceChange,
            handlePriceBlur,
            closeModals,
            data,
          }}
        />

        <UndoModal {...{ showUndoConfirm, setShowUndoConfirm, confirmUndo }} />

        <NoteModal {...{ showNoteModal, setShowNoteModal, editingNote, setEditingNote, handleUpdateNote }} />

        <Toaster position="top-center" richColors expand={true} closeButton theme="light" />
      </div>
    </main>
  );
}
