"use client";
import React, { useState, useEffect } from "react";
import { Trash2, Loader2, ArrowUpDown, Bookmark, Pencil } from "lucide-react";
import { toast } from "sonner";
import * as api from "@/lib/api";
import WatchlistRow from "../components/WatchlistRow";
import WatchlistToolbar from "../components/WatchlistToolbar";
import WLCreateModal from "../modals/WLCreateModal";
import WLRenameModal from "../modals/WLRenameModal";
import WLAddTickerModal from "../modals/WLAddTickerModal";
import ConfirmModal from "../modals/ConfirmModal";
const WATCHLIST_COLORS = [
    { active: "bg-purple-500 border-purple-500", dot: "bg-purple-400", badge: "bg-purple-700/50", hover: "hover:border-purple-200 hover:text-purple-500", text: "text-purple-500" },
    { active: "bg-emerald-600 border-emerald-600", dot: "bg-emerald-500", badge: "bg-emerald-800/50", hover: "hover:border-emerald-200 hover:text-emerald-600", text: "text-emerald-600" },
    { active: "bg-orange-400 border-orange-400", dot: "bg-orange-300", badge: "bg-orange-600/50", hover: "hover:border-orange-200 hover:text-orange-500", text: "text-orange-500" },
    { active: "bg-slate-600 border-slate-600", dot: "bg-slate-500", badge: "bg-slate-800/50", hover: "hover:border-slate-300 hover:text-slate-600", text: "text-slate-600" },
    { active: "bg-blue-600 border-blue-600", dot: "bg-blue-500", badge: "bg-blue-800/50", hover: "hover:border-blue-200 hover:text-blue-600", text: "text-blue-600" },
];

export default function WatchlistPro() {
    const [watchlists, setWatchlists] = useState([]);
    const [activeWatchlistId, setActiveWatchlistId] = useState(null);
    const [watchlistDetail, setWatchlistDetail] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedTickers, setSelectedTickers] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [sortConfig, setSortConfig] = useState({ key: 'change_pct', direction: 'desc' }); // Mặc định xếp theo % thay đổi giảm dần

    // UI States for Modals
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showRenameModal, setShowRenameModal] = useState(false);
    const [showAddTicker, setShowAddTicker] = useState(false);

    // Confirm Modal state
    const [confirmModal, setConfirmModal] = useState({
        show: false,
        title: "",
        message: "",
        onConfirm: () => { },
        confirmText: "Xác nhận",
        confirmColor: "bg-rose-500"
    });

    // 1. Fetch all watchlists
    const fetchWatchlists = async () => {
        try {
            const res = await api.getWatchlists();
            setWatchlists(res.data);
            if (res.data.length > 0 && !activeWatchlistId) {
                setActiveWatchlistId(res.data[0].id);
            }
        } catch (error) {
            console.error("Lỗi lấy danh sách watchlist:", error);
        }
    };

    // 2. Fetch detail for active watchlist
    const fetchDetail = async () => {
        if (!activeWatchlistId) return;
        try {
            const res = await api.getWatchlistDetail(activeWatchlistId);
            setWatchlistDetail(res.data);
            setLastUpdated(new Date());
        } catch (error) {
            console.error("Lỗi tải dữ liệu chi tiết:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWatchlists();
    }, []);

    useEffect(() => {
        if (activeWatchlistId) {
            setLoading(true);
            fetchDetail();

            // Thiết lập Auto-refresh mỗi 10 giây
            const interval = setInterval(() => {
                fetchDetail();
            }, 10000);

            return () => clearInterval(interval);
        }
    }, [activeWatchlistId]);

    // Actions
    const handleCreateWL = async (name) => {
        try {
            const res = await api.createWatchlist(name);
            setWatchlists([...watchlists, res.data]);
            setActiveWatchlistId(res.data.id);
            setShowCreateModal(false);
            toast.success(`Đã tạo danh sách: ${name}`);
        } catch (error) {
            toast.error(error.response?.data?.detail || "Lỗi tạo danh sách");
        }
    };

    const handleRenameWL = async (newName) => {
        if (!activeWatchlistId) return;
        try {
            await api.renameWatchlist(activeWatchlistId, newName);
            setShowRenameModal(false);
            fetchWatchlists();
            toast.success("Đã đổi tên danh sách");
        } catch (error) {
            toast.error(error.response?.data?.detail || "Lỗi đổi tên danh sách");
        }
    };


    const handleDeleteWL = async (id) => {
        const wl = watchlists.find(w => w.id === id);
        setConfirmModal({
            show: true,
            title: "Xóa danh sách",
            message: `Bạn có chắc chắn muốn xóa danh sách "${wl?.name || ''}"?`,
            confirmText: "Xóa ngay",
            confirmColor: "bg-rose-500",
            onConfirm: async () => {
                try {
                    await api.deleteWatchlist(id);
                    const updated = watchlists.filter((w) => w.id !== id);
                    setWatchlists(updated);
                    if (updated.length > 0) setActiveWatchlistId(updated[0].id);
                    else {
                        setActiveWatchlistId(null);
                        setWatchlistDetail([]);
                    }
                    toast.success("Đã xóa danh sách");
                } catch (error) {
                    toast.error("Lỗi xóa danh sách");
                } finally {
                    setConfirmModal(prev => ({ ...prev, show: false }));
                }
            }
        });
    };

    const handleAddTicker = async (ticker) => {
        if (!activeWatchlistId) return;
        try {
            await api.addTickerToWatchlist(activeWatchlistId, ticker);
            fetchDetail();
            setShowAddTicker(false);
            toast.success(`Đã thêm mã ${ticker.toUpperCase()} thành công! 🚀`);
        } catch (error) {
            toast.error(error.response?.data?.detail || "Lỗi thêm mã");
        }
    };

    const handleRemoveTicker = async (ticker) => {
        const wl = watchlists.find(w => w.id === activeWatchlistId);
        if (!wl) return;
        const tickerObj = wl.tickers.find(t => t.ticker === ticker);
        if (!tickerObj) return;

        try {
            await api.removeTickerFromWatchlist(activeWatchlistId, tickerObj.id);
            fetchDetail();
            setSelectedTickers(prev => prev.filter(t => t !== ticker));
            toast.success(`Đã xóa ${ticker}`);
        } catch (error) {
            toast.error("Lỗi xóa mã");
        }
    };

    const handleBulkDelete = async () => {
        if (selectedTickers.length === 0) return;
        setConfirmModal({
            show: true,
            title: "Xác nhận xóa",
            message: `Bạn có chắc chắn muốn xóa ${selectedTickers.length} mã đã chọn?`,
            confirmText: "Xóa tất cả",
            confirmColor: "bg-rose-500",
            onConfirm: async () => {
                const wl = watchlists.find(w => w.id === activeWatchlistId);
                if (!wl) return;

                setLoading(true);
                setConfirmModal(prev => ({ ...prev, show: false }));
                try {
                    for (const ticker of selectedTickers) {
                        const tickerObj = wl.tickers.find(t => t.ticker === ticker);
                        if (tickerObj) {
                            await api.removeTickerFromWatchlist(activeWatchlistId, tickerObj.id);
                        }
                    }
                    setSelectedTickers([]);
                    fetchDetail();
                    toast.success(`Đã xóa ${selectedTickers.length} mã`);
                } catch (error) {
                    toast.error("Lỗi khi xóa hàng loạt");
                } finally {
                    setLoading(false);
                }
            }
        });
    };

    const handleToggleSelect = (ticker) => {
        setSelectedTickers(prev =>
            prev.includes(ticker)
                ? prev.filter(t => t !== ticker)
                : [...prev, ticker]
        );
    };

    const handleToggleSelectAll = () => {
        if (selectedTickers.length === sortedItems.length) {
            setSelectedTickers([]);
        } else {
            setSelectedTickers(sortedItems.map(i => i.ticker));
        }
    };

    const handleExportCSV = () => {
        if (watchlistDetail.length === 0) return;
        const headers = "Mã,Giá,Thay đổi %,ROE %,ROA %,PE\n";
        const rows = sortedItems.map(i => `${i.ticker},${i.price},${i.change_pct.toFixed(2)}%,${i.roe}%,${i.roa}%,${i.pe}`).join("\n");
        const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `watchlist_${activeWatchlistId}.csv`;
        link.click();
    };

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const sortedItems = React.useMemo(() => {
        let sortableItems = [...watchlistDetail];
        if (sortConfig.key !== null) {
            sortableItems.sort((a, b) => {
                let aValue = a[sortConfig.key];
                let bValue = b[sortConfig.key];

                // Xử lý null/undefined
                if (aValue === null || aValue === undefined) aValue = -Infinity;
                if (bValue === null || bValue === undefined) bValue = -Infinity;

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
    }, [watchlistDetail, sortConfig]);


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
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">

            {/* WATCHLIST TABS */}
            <div className="flex items-center gap-2 overflow-x-auto pb-4 no-scrollbar">
                {watchlists.map((wl, idx) => {
                    const color = WATCHLIST_COLORS[idx % WATCHLIST_COLORS.length];
                    const isActive = activeWatchlistId === wl.id;
                    return (
                        <div key={wl.id} className="flex shrink-0">
                            <button
                                onClick={() => setActiveWatchlistId(wl.id)}
                                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all border-2 ${isActive
                                    ? `${color.active} text-white shadow-lg`
                                    : `bg-white text-slate-400 border-slate-100 ${color.hover}`
                                    }`}
                            >
                                <div className={`w-2 h-2 rounded-full ${isActive ? "bg-white animate-pulse" : color.dot}`} />
                                {wl.name}
                                <span className={`ml-1 px-1.5 py-0.5 rounded-md text-xs font-bold ${isActive ? color.badge : "bg-slate-100 text-slate-500"}`}>
                                    {wl.tickers?.length || 0}
                                </span>
                            </button>
                            {isActive && (
                                <div className="flex items-center gap-0.5 ml-1">
                                    <button
                                        onClick={() => setShowRenameModal(true)}
                                        className="p-2 text-slate-300 hover:text-blue-500 transition-colors"
                                        title="Đổi tên"
                                    >
                                        <Pencil size={14} />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteWL(wl.id)}
                                        className="p-2 text-slate-300 hover:text-rose-500 transition-colors"
                                        title="Xóa nhóm này"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* MAIN TABLE AREA */}
            <div className="bg-white rounded-3xl border border-slate-400 shadow-xl shadow-slate-200/50 overflow-hidden">
                <WatchlistToolbar
                    onShowCreate={() => setShowCreateModal(true)}
                    onShowAdd={() => setShowAddTicker(true)}
                    onBulkDelete={handleBulkDelete}
                    onExport={handleExportCSV}
                    selectedCount={selectedTickers.length}
                />

                {/* Table Content */}
                <div className="overflow-x-auto">
                    {loading ? (
                        <div className="py-20 flex flex-col items-center justify-center gap-4">
                            <Loader2 className="animate-spin text-emerald-500" size={32} />
                            <p className="text-slate-400 font-bold text-xs uppercase tracking-widest">Đang tải dữ liệu Pro...</p>
                        </div>
                    ) : sortedItems.length > 0 ? (
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-slate-50/50 text-slate-500 text-[13px] uppercase font-bold tracking-[0.12em] border-b border-slate-100">
                                <tr>
                                    <th className="p-4 pl-6 w-10">
                                        <div
                                            onClick={handleToggleSelectAll}
                                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center cursor-pointer transition-all ${selectedTickers.length === sortedItems.length && sortedItems.length > 0
                                                ? "bg-orange-500 border-orange-500"
                                                : "bg-white border-slate-200"
                                                }`}
                                        >
                                            {selectedTickers.length === sortedItems.length && sortedItems.length > 0 && (
                                                <div className="w-2 h-2 bg-white rounded-full" />
                                            )}
                                        </div>
                                    </th>
                                    <th className="p-4 text-left cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('ticker')}>
                                        Mã CK <SortIcon columnKey="ticker" />
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('price')}>
                                        Giá TT <SortIcon columnKey="price" />
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('change_pct')}>
                                        % Thay đổi <SortIcon columnKey="change_pct" />
                                    </th>
                                    <th className="p-4 text-center">
                                        <div>Xu hướng</div>
                                        <div className="text-[10px] text-slate-800 font-normal">(5 phiên)</div>
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('volume')}>
                                        KL <SortIcon columnKey="volume" />
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('roe')}>
                                        ROE (%) <SortIcon columnKey="roe" />
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('roa')}>
                                        ROA (%) <SortIcon columnKey="roa" />
                                    </th>
                                    <th className="p-4 text-right cursor-pointer hover:bg-slate-100/50 transition-colors" onClick={() => requestSort('pe')}>
                                        P/E <SortIcon columnKey="pe" />
                                    </th>
                                    <th className="p-4 w-10"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {sortedItems.map(item => (
                                    <WatchlistRow
                                        key={item.ticker}
                                        item={item}
                                        onRemove={handleRemoveTicker}
                                        isSelected={selectedTickers.includes(item.ticker)}
                                        onToggle={() => handleToggleSelect(item.ticker)}
                                    />
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="py-20 text-center">
                            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Bookmark size={24} className="text-slate-200" />
                            </div>
                            <p className="text-slate-400 font-bold">Chưa có mã nào trong danh sách này.</p>
                            <button onClick={() => setShowAddTicker(true)} className="mt-4 text-emerald-500 font-black text-xs uppercase hover:underline">Thêm mã ngay</button>
                        </div>
                    )}
                </div>

                <div className="p-5 bg-slate-50/50 border-t border-slate-100 flex justify-between items-center px-8">
                    <span className="text-sm font-bold text-slate-600 uppercase tracking-[0.05em]">{sortedItems.length} mã trong danh sách</span>
                    <span className="text-sm font-bold text-slate-500">
                        Cập nhật lúc: <span className="text-emerald-600 font-extrabold">{lastUpdated.toLocaleTimeString('vi-VN')}</span>
                    </span>
                </div>
            </div>

            {/* MODALS */}
            <WLCreateModal
                isOpen={showCreateModal}
                onClose={() => setShowCreateModal(false)}
                onCreate={handleCreateWL}
            />

            <WLRenameModal
                isOpen={showRenameModal}
                onClose={() => setShowRenameModal(false)}
                onRename={handleRenameWL}
                initialName={watchlists.find(w => w.id === activeWatchlistId)?.name}
            />

            <WLAddTickerModal
                isOpen={showAddTicker}
                onClose={() => setShowAddTicker(false)}
                onAdd={handleAddTicker}
            />

            <ConfirmModal
                isOpen={confirmModal.show}
                onClose={() => setConfirmModal(prev => ({ ...prev, show: false }))}
                onConfirm={confirmModal.onConfirm}
                title={confirmModal.title}
                message={confirmModal.message}
                confirmText={confirmModal.confirmText}
                confirmColor={confirmModal.confirmColor}
            />
        </div>
    );
}
