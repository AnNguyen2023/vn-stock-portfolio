"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { RefreshCw, Wallet, TrendingUp, PieChart as PieChartIcon } from "lucide-react";
import { Toaster, toast } from "sonner";

import SummaryCard from "./components/SummaryCard";
import MarketSummary from "./components/MarketSummary";
import ScrollToTop from "./components/ScrollToTop";
import CashModal from "./modals/CashModal";
import TradeModal from "./modals/TradeModal";
import UndoModal from "./modals/UndoModal";
import NoteModal from "./modals/NoteModal";

import Header from "./sections/Header";
import StockTable from "./sections/StockTable";
import GrowthChart from "./sections/GrowthChart";

// Custom Hooks
import useDashboardData from "./hooks/useDashboardData";
import useTradeActions from "./hooks/useTradeActions";
import { getChartGrowth, getHistoricalData } from "@/lib/api";

const HistoryTabs = dynamic(() => import("./sections/HistoryTabs"), { ssr: false });
const WatchlistPro = dynamic(() => import("./sections/WatchlistPro"), { ssr: false });
const ScannerSection = dynamic(() => import("./sections/ScannerSection"), { ssr: false });

// --- CẤU HÌNH MÀU SẮC (Dành cho 10 mã cổ phiếu) ---
const PIE_COLORS = [
  "#16a34a", "#2563eb", "#ea580c", "#ca8a04", "#9333ea",
  "#06b6d4", "#f43f5e", "#84cc16", "#64748b", "#1e40af",
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

  // Base timeline
  let baseData = null;
  if (portfolioSeries && portfolioSeries.length > 0) {
    baseData = portfolioSeries.map((p) => ({ date: p.date }));
  } else {
    // Nếu responses[index] đã là mảng (do interceptor giải nén), dùng trực tiếp
    const validResponse = responses.find((r) => (Array.isArray(r) ? r.length > 0 : r?.data?.length > 0));
    if (!validResponse) return [];
    baseData = Array.isArray(validResponse) ? validResponse : validResponse.data;
  }

  // Build price maps
  const priceMaps = {};
  const firstPrices = {};

  stockTickers.forEach((ticker, index) => {
    const rawRes = responses[index];
    const stockData = Array.isArray(rawRes) ? rawRes : (rawRes?.data || []);
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
    const dateStr = item.date;
    const point = { date: dateStr };

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
  // 1) HOOKS - CORE DATA
  const {
    data, logs, loading, navHistory, historicalProfit, portfolioLastUpdated,
    startDate, setStartDate, endDate, setEndDate,
    fetchAllData, handleCalculateProfit
  } = useDashboardData();

  // 2) HOOKS - ACTIONS
  const {
    showDeposit, setShowDeposit, showWithdraw, setShowWithdraw,
    showBuy, setShowBuy, showSell, setShowSell, showUndoConfirm, setShowUndoConfirm,
    amount, setAmount, description, setDescription,
    buyForm, setBuyForm, sellForm, setSellForm,
    editingNote, setEditingNote, showNoteModal, setShowNoteModal,
    closeModals, handleAmountChange, handleVolumeChange, handlePriceChange, handlePriceBlur,
    handleUndo, confirmUndo, handleDeposit, handleWithdraw, handleBuy, handleSell, handleUpdateNote
  } = useTradeActions(fetchAllData);

  // 3) UI STATE (Local)
  const [activeMainTab, setActiveMainTab] = useState("watchlist");
  const [chartData, setChartData] = useState([]);
  const [isPrivate, setIsPrivate] = useState(true);
  const [activeHistoryTab, setActiveHistoryTab] = useState("allocation");
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [chartRange, setChartRange] = useState("1m");
  const [selectedComparisons, setSelectedComparisons] = useState(["PORTFOLIO", "VNINDEX"]);

  // Auto privacy
  useEffect(() => {
    let timer;
    if (!isPrivate) {
      timer = setTimeout(() => {
        setIsPrivate(true);
        toast.info("Chế độ riêng tư", { description: "Số dư đã được ẩn tự động sau 5 phút." });
      }, 300000);
    }
    return () => clearTimeout(timer);
  }, [isPrivate]);

  // Chart Fetching Logic (Still local as it depends on UI state)
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
          toast.error("Không tải được dữ liệu tăng trưởng", { description: "Vui lòng kiểm tra kết nối Backend." });
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

  const toggleComparison = (ticker) => {
    if (selectedComparisons.includes(ticker)) {
      setSelectedComparisons(selectedComparisons.filter((t) => t !== ticker));
    } else {
      if (selectedComparisons.length >= 5) {
        toast.warning("Giới hạn so sánh", { description: "Chỉ được chọn tối đa 5 đường cùng lúc." });
        return;
      }
      setSelectedComparisons([...selectedComparisons, ticker]);
    }
  };

  // Holding tickers
  const holdingTickers = data?.holdings?.map((h) => h.ticker) || [];

  // Loading Screen
  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f8fafc]">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 border-4 border-emerald-100 rounded-full"></div>
            <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
          </div>
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

  return (
    <main className="min-h-screen bg-[#f8fafc] p-4 md:p-6 font-sans text-slate-900">
      <div className="max-w-7xl mx-auto">
        <Header
          {...{
            isPrivate, setIsPrivate, setShowDeposit, setShowWithdraw, setShowBuy,
            fetchAllData, handleUndo
          }}
        />

        {/* SUMMARY */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <SummaryCard isPrivate={isPrivate} title="Vốn thực có (NAV)" value={Math.floor(data?.total_nav || 0)} icon={<PieChartIcon size={26} />} color="text-emerald-700" bg="bg-emerald-50" />
          <SummaryCard isPrivate={isPrivate} title="Tiền mặt" value={Math.floor(data?.cash_balance || 0)} icon={<Wallet size={26} />} color="text-teal-600" bg="bg-teal-50" />
          <SummaryCard isPrivate={isPrivate} title="Giá trị cổ phiếu" value={Math.floor(data?.total_stock_value || 0)} icon={<TrendingUp size={26} />} color="text-purple-600" bg="bg-purple-50" />
        </div>

        {/* Market Summary */}
        <div className="mb-6"><MarketSummary /></div>

        {/* MAIN CONTENT TABS */}
        <div className="mb-6">
          <div className="flex items-center gap-1 p-1 bg-slate-100/50 rounded-2xl w-fit mb-4 border border-slate-400">
            {['watchlist', 'growth', 'scanner'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveMainTab(tab)}
                className={`px-6 py-2.5 rounded-xl text-xs font-black uppercase transition-all ${activeMainTab === tab ? "bg-white text-emerald-600 shadow-sm" : "text-slate-400 hover:text-slate-600"}`}
              >
                {tab === 'watchlist' ? 'Watchlist Pro' : tab === 'growth' ? 'Hiệu suất tăng trưởng' : 'TITAN Scanner'}
              </button>
            ))}
          </div>

          {activeMainTab === "growth" ? (
            <GrowthChart {...{ chartData, chartRange, setChartRange, isDropdownOpen, setIsDropdownOpen, selectedComparisons, holdingTickers, toggleComparison, totalNav: data?.total_nav }} />
          ) : activeMainTab === "scanner" ? (
            <ScannerSection />
          ) : (
            <WatchlistPro />
          )}
        </div>

        {/* TABLE */}
        <StockTable {...{ data, buyForm, setBuyForm, sellForm, setSellForm, setShowBuy, setShowSell, lastUpdated: portfolioLastUpdated }} />

        {/* HISTORY */}
        <HistoryTabs {...{ activeHistoryTab, setActiveHistoryTab, startDate, setStartDate, endDate, setEndDate, handleCalculateProfit, data, PIE_COLORS, historicalProfit, navHistory, logs, setEditingNote, setShowNoteModal }} />

        {/* MODALS */}
        <CashModal {...{ showDeposit, showWithdraw, amount, setAmount, description, setDescription, handleAmountChange, handleDeposit, handleWithdraw, closeModals, cash: data?.cash_balance || 0 }} />
        <TradeModal {...{ showBuy, showSell, buyForm, setBuyForm, sellForm, setSellForm, handleBuy, handleSell, handleVolumeChange, handlePriceChange, handlePriceBlur, closeModals, data }} />
        <UndoModal {...{ showUndoConfirm, setShowUndoConfirm, confirmUndo }} />
        <NoteModal {...{ showNoteModal, setShowNoteModal, editingNote, setEditingNote, handleUpdateNote }} />

        <Toaster position="top-center" richColors expand={true} closeButton theme="light" />
        <ScrollToTop />
      </div>
    </main>
  );
}
