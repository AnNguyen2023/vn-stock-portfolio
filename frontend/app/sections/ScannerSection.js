"use client";

import React, { useState, useEffect } from "react";
import { Play, Activity, CheckCircle, AlertCircle, Search, TrendingUp, TrendingDown, Square, ArrowUpDown, Brain, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { triggerTitanScan, getTitanStatus, getTitanResults, stopTitanScan } from "@/lib/api";

export default function ScannerSection() {
    const [status, setStatus] = useState({ is_running: false, progress: 0, total: 0, current_symbol: "" });
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [stopping, setStopping] = useState(false);
    const [activeMode, setActiveMode] = useState("Balanced");
    const [sortConfig, setSortConfig] = useState({ key: 'signal', direction: 'desc' });

    const MODES = {
        "Fast": {
            label: "Nhanh",
            description: "Lọc watchlist mỗi ngày",
            settings: {
                fee_bps: 18, slippage_bps: 7,
                wf_train_bars: 252, wf_test_bars: 63, wf_step_bars: 63, wf_min_folds: 3,
                stability_lambda: 0.9, trade_penalty_bps: 2
            }
        },
        "Balanced": {
            label: "Cân bằng",
            description: "Khuyến nghị vốn vừa & nhỏ",
            settings: {
                fee_bps: 22, slippage_bps: 10,
                wf_train_bars: 252, wf_test_bars: 63, wf_step_bars: 21, wf_min_folds: 4,
                stability_lambda: 1.1, trade_penalty_bps: 3
            }
        },
        "Tight": {
            label: "Chặt",
            description: "Ít kèo nhưng chất",
            settings: {
                fee_bps: 25, slippage_bps: 12,
                wf_train_bars: 252, wf_test_bars: 63, wf_step_bars: 10, wf_min_folds: 5,
                stability_lambda: 1.4, trade_penalty_bps: 4
            }
        }
    };

    // Check status on mount to resume UI state
    useEffect(() => {
        const fetchInitialStatus = async () => {
            try {
                const res = await getTitanStatus();
                setStatus(res.data);
                if (res.data.is_running) {
                    setLoading(true);
                } else {
                    // If not running, fetch the latest results
                    const resResults = await getTitanResults();
                    setResults(resResults.data);
                }
            } catch (e) {
                console.error("Failed to fetch initial TITAN status");
            }
        };
        fetchInitialStatus();
    }, []);

    // Poll status when scanning
    useEffect(() => {
        let interval;
        if (loading) {
            interval = setInterval(async () => {
                const res = await getTitanStatus();
                setStatus(res.data);
                if (!res.data.is_running) {
                    setLoading(false);
                    const resResults = await getTitanResults();
                    setResults(resResults.data);
                }
            }, 1000);
        }
        return () => clearInterval(interval);
    }, [loading]);

    const handleStartScan = async () => {
        if (loading || status.is_running) return;
        try {
            setLoading(true);
            await triggerTitanScan(MODES[activeMode].settings);
            toast.success("Đã bắt đầu quét VN100 (Mode: " + MODES[activeMode].label + ")");
        } catch (error) {
            toast.error("Không thể bắt đầu quét");
            setLoading(false);
        }
    };

    const handleStopScan = async () => {
        try {
            setStopping(true);
            await stopTitanScan();
            toast.info("Đang gửi lệnh dừng...");
        } catch (e) {
            toast.error("Không thể dừng quét");
            setStopping(false);
        }
    };

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    // Format price like Watchlist
    const formatPrice = (p) => new Intl.NumberFormat("vi-VN").format(p);

    const sortedResults = React.useMemo(() => {
        let sortableItems = [...results];
        if (sortConfig.key !== null) {
            sortableItems.sort((a, b) => {
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                // Logic đặc biệt cho Tín hiệu
                if (sortConfig.key === 'signal') {
                    const getRank = (item) => {
                        if (item.is_buy_signal && item.is_valid) return 3;
                        if (item.is_valid) return 2;
                        return 1;
                    };
                    aValue = getRank(a);
                    bValue = getRank(b);
                }

                if (aValue < bValue) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (aValue > bValue) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [results, sortConfig]);

    const SortIcon = ({ columnKey }) => {
        const isActive = sortConfig.key === columnKey;
        return (
            <ArrowUpDown
                size={14}
                className={`inline-block ml-1 transition-colors ${isActive ? 'text-emerald-500' : 'text-slate-400'}`}
            />
        );
    };

    return (
        <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h2 className="text-[17px] font-medium text-slate-600 uppercase tracking-tight flex items-center gap-2">
                        <Activity className="text-emerald-500" size={20} />
                        TITAN Scanner
                    </h2>
                    <p className="text-sm text-slate-500">Quét 120 mã VN100 & Tối ưu hóa tham số DI (1-40)</p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {/* Mode Selector */}
                    <div className="flex bg-slate-100 p-1 rounded-2xl mr-2">
                        {Object.entries(MODES).map(([key, mode]) => (
                            <div key={key} className="relative group/mode">
                                <button
                                    onClick={() => setActiveMode(key)}
                                    disabled={status.is_running}
                                    className={`px-3 py-2 rounded-xl text-sm font-bold transition-all flex flex-col items-center min-w-[80px] ${activeMode === key
                                        ? "bg-white text-emerald-600 shadow-sm"
                                        : "text-slate-700 hover:text-slate-900"
                                        } ${status.is_running ? "opacity-50 cursor-not-allowed" : ""}`}
                                >
                                    <span>{mode.label}</span>
                                </button>
                                {/* Mode Tooltip */}
                                <div className="hidden group-hover/mode:block absolute top-full left-1/2 -translate-x-1/2 mt-3 w-52 z-50 animate-in fade-in zoom-in-95 duration-200">
                                    {/* Arrow pointing up */}
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 border-[6px] border-transparent border-b-slate-700"></div>

                                    <div className="bg-slate-700 text-white p-3.5 rounded-xl shadow-2xl text-center border border-white/10 backdrop-blur-sm">
                                        <p className="font-bold text-[13px] mb-1 text-emerald-400 uppercase tracking-wide">{mode.label}</p>
                                        <p className="text-[12px] font-medium text-slate-300 leading-relaxed">{mode.description}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {status.is_running && (
                        <button
                            onClick={handleStopScan}
                            disabled={stopping}
                            className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold uppercase text-sm transition-all bg-rose-50 text-rose-500 hover:bg-rose-100 border border-rose-200 ${stopping ? "opacity-50 cursor-not-allowed" : ""}`}
                        >
                            <Square size={16} fill="currentColor" />
                            Dừng quét
                        </button>
                    )}
                    <button
                        onClick={handleStartScan}
                        disabled={status.is_running || loading}
                        className={`flex items-center gap-2 px-6 py-3 rounded-2xl font-bold uppercase text-sm transition-all ${status.is_running || loading
                            ? "bg-slate-100 text-slate-600 cursor-not-allowed"
                            : "bg-emerald-500 text-white hover:bg-emerald-600 shadow-lg shadow-emerald-100"
                            }`}
                    >
                        {status.is_running || loading ? (
                            <>
                                <RefreshCw className="animate-spin" size={16} />
                                Đang quét... {status.progress}/{status.total}
                            </>
                        ) : (
                            <>
                                <Play size={16} fill="currentColor" />
                                Bắt đầu quét mới
                            </>
                        )}
                    </button>
                </div>
            </div>

            {status.is_running && (
                <div className="mb-8 p-4 bg-emerald-50 rounded-2xl border border-emerald-100">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                            Tiến độ: {Math.round((status.progress / status.total) * 100)}%
                        </span>
                        <span className="text-xs font-medium text-emerald-600 uppercase flex items-center gap-2">
                            Đang phân tích: <span className="text-xl text-orange-600 font-normal">{status.current_symbol}</span>
                        </span>
                    </div>
                    <div className="w-full bg-emerald-100 h-2 rounded-full overflow-hidden">
                        <div
                            className="bg-emerald-500 h-full transition-all duration-500"
                            style={{ width: `${(status.progress / status.total) * 100}%` }}
                        ></div>
                    </div>
                </div>
            )}

            <div className="overflow-x-auto overflow-y-auto max-h-[600px] rounded-2xl border border-slate-100">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50/50 text-slate-500 text-[13px] uppercase font-bold tracking-[0.12em] border-b border-slate-100">
                        <tr>
                            <th className="px-6 py-4 text-left cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('symbol')}>
                                Mã <SortIcon columnKey="symbol" />
                            </th>
                            <th className="px-4 py-4 text-left cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('close_price')}>
                                Giá TT <SortIcon columnKey="close_price" />
                            </th>
                            <th className="px-4 py-4 text-right cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('alpha')}>
                                Alpha <SortIcon columnKey="alpha" />
                            </th>
                            <th className="px-4 py-4 text-center cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('optimal_length')}>
                                Opt Len <SortIcon columnKey="optimal_length" />
                            </th>
                            <th className="px-4 py-4 text-center cursor-pointer hover:bg-emerald-100 transition-colors" onClick={() => requestSort('signal')}>
                                Tín hiệu <SortIcon columnKey="signal" />
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                        {sortedResults.length > 0 ? (
                            sortedResults.map((r, i) => (
                                <tr key={i} className="hover:bg-emerald-50 transition-colors group">
                                    <td className="px-4 py-4">
                                        <span className="font-semibold text-slate-900 group-hover:text-emerald-600 transition-colors text-[15px]">{r.symbol}</span>
                                    </td>
                                    <td className="px-4 py-4">
                                        <span className="text-sm font-medium text-slate-600 font-tabular-nums">{formatPrice(r.close_price)}</span>
                                    </td>
                                    <td className="px-4 py-4 text-right">
                                        <div className={`inline-flex items-center gap-1 font-bold ${r.alpha > 0 ? "text-emerald-500" : "text-rose-500"}`}>
                                            {r.alpha > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                                            {r.alpha > 0 ? "+" : ""}{parseFloat(r.alpha).toFixed(1)}%
                                        </div>
                                    </td>
                                    <td className="px-4 py-4 text-center">
                                        <span className="px-2.5 py-1 bg-slate-200 rounded-lg text-xs font-bold text-slate-700">DI={r.optimal_length}</span>
                                    </td>
                                    <td className="px-4 py-4 text-center">
                                        {r.is_buy_signal && r.is_valid ? (
                                            <div className="relative group/tooltip inline-block">
                                                <span className="inline-flex items-center gap-1 px-4 py-1.5 bg-emerald-500 text-white text-[12px] font-medium rounded-xl shadow-sm hover:scale-105 hover:shadow-lg hover:shadow-emerald-200 transition-all cursor-help">
                                                    MUA MẠNH
                                                </span>
                                                {/* Tooltip Popup - Moved to Left */}
                                                <div className="hidden group-hover/tooltip:block absolute top-1/2 right-full -translate-y-1/2 mr-4 w-72 z-50 animate-in fade-in slide-in-from-right-2 duration-200">
                                                    <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 p-4 text-left relative">
                                                        <div className="flex items-start gap-3">
                                                            <div className="p-2 bg-emerald-50 rounded-lg">
                                                                <Brain size={18} className="text-emerald-500" />
                                                            </div>
                                                            <div>
                                                                <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Lý giải thuật toán TITAN</h4>
                                                                <p className="text-[13px] text-slate-600 leading-relaxed">
                                                                    Phát hiện <span className="font-bold text-emerald-600">Impulse Ignition</span> (Điểm bùng nổ) khi xu hướng đảo chiều dương với tham số tối ưu <span className="font-bold text-slate-900">DI={r.optimal_length}</span>.
                                                                    Hệ thống xác nhận <span className="font-bold text-emerald-600">Alpha Guardrails</span> đạt <span className="font-bold text-slate-900">+{parseFloat(r.alpha).toFixed(1)}%</span> vượt trội so với thị trường.
                                                                </p>
                                                            </div>
                                                        </div>
                                                        {/* Triangle pointer pointing right */}
                                                        <div className="absolute top-1/2 left-full -translate-y-1/2 border-8 border-transparent border-l-white"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : r.is_valid ? (
                                            <span className="inline-flex items-center gap-1 px-4 py-1.5 bg-sky-500 text-white text-[12px] font-medium rounded-xl shadow-sm hover:scale-105 hover:shadow-lg hover:shadow-sky-200 transition-all cursor-default">
                                                THEO DÕI
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1 px-4 py-1.5 bg-slate-100 text-slate-400 text-[12px] font-medium rounded-xl hover:bg-slate-200 transition-all cursor-default">
                                                BỎ QUA
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan="5" className="px-4 py-12 text-center">
                                    <div className="flex flex-col items-center gap-2">
                                        <Search className="text-slate-200" size={40} />
                                        <p className="text-slate-400 text-sm font-medium">Chưa có kết quả quét nào được lưu.</p>
                                    </div>
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}


