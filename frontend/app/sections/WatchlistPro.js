"use client";
import React, { useState, useEffect } from "react";
import { Plus, Search, Download, Trash2, Loader2, ListPlus, Activity, ArrowUpDown, Bookmark } from "lucide-react";
import { toast } from "sonner";
import * as api from "@/lib/api";
import WatchlistRow from "../components/WatchlistRow";

export default function WatchlistPro() {
    const [watchlists, setWatchlists] = useState([]);
    const [activeWatchlistId, setActiveWatchlistId] = useState(null);
    const [watchlistDetail, setWatchlistDetail] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedTickers, setSelectedTickers] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [sortConfig, setSortConfig] = useState({ key: 'change_pct', direction: 'desc' }); // Mặc định xếp theo % thay đổi giảm dần

    // UI States for Modals
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [newWLName, setNewWLName] = useState("");
    const [showAddTicker, setShowAddTicker] = useState(false);
    const [newTicker, setNewTicker] = useState("");

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
    const handleCreateWL = async () => {
        if (!newWLName) return;
        try {
            const res = await api.createWatchlist(newWLName);
            setWatchlists([...watchlists, res.data]);
            setActiveWatchlistId(res.data.id);
            setNewWLName("");
            setShowCreateModal(false);
            toast.success(`Đã tạo danh sách: ${newWLName}`);
        } catch (error) {
            toast.error(error.response?.data?.detail || "Lỗi tạo danh sách");
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

    const handleAddTicker = async () => {
        if (!newTicker || !activeWatchlistId) return;
        try {
            await api.addTickerToWatchlist(activeWatchlistId, newTicker);
            fetchDetail();
            const tickerAdded = newTicker.toUpperCase();
            setNewTicker("");
            setShowAddTicker(false);

            // Hiện toast nhỏ gọn thay vì modal to
            toast.success(`Đã thêm mã ${tickerAdded} thành công! 🚀`);
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
        if (selectedTickers.length === filteredItems.length) {
            setSelectedTickers([]);
        } else {
            setSelectedTickers(filteredItems.map(i => i.ticker));
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

    const filteredItems = sortedItems.filter(i =>
        i.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
        i.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

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
                {watchlists.map((wl) => (
                    <div key={wl.id} className="flex shrink-0">
                        <button
                            onClick={() => setActiveWatchlistId(wl.id)}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all border-2 ${activeWatchlistId === wl.id
                                ? "bg-purple-500 text-white border-purple-500 shadow-lg shadow-purple-100"
                                : "bg-white text-slate-400 border-slate-100 hover:border-purple-200 hover:text-purple-500"
                                }`}
                        >
                            <div className={`w-2 h-2 rounded-full ${activeWatchlistId === wl.id ? "bg-white animate-pulse" : "bg-purple-400"}`} />
                            {wl.name}
                            <span className={`ml-1 px-1.5 py-0.5 rounded-md text-[10px] ${activeWatchlistId === wl.id ? "bg-purple-700/50" : "bg-slate-100"}`}>
                                {wl.tickers?.length || 0}
                            </span>
                        </button>
                        {activeWatchlistId === wl.id && (
                            <button
                                onClick={() => handleDeleteWL(wl.id)}
                                className="ml-1 p-2 text-slate-300 hover:text-rose-500 transition-colors"
                                title="Xóa nhóm này"
                            >
                                <Trash2 size={14} />
                            </button>
                        )}
                    </div>
                ))}
            </div>

            {/* MAIN TABLE AREA */}
            <div className="bg-white rounded-3xl border border-slate-400 shadow-xl shadow-slate-200/50 overflow-hidden">
                {/* Table Toolbar */}
                <div className="p-4 border-b border-slate-300 flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-50/30">
                    <div className="flex items-center gap-2">
                        <Bookmark size={20} className="text-slate-600" />
                        <h2 className="text-xl font-bold text-slate-600 uppercase tracking-tight">Watchlist Pro</h2>
                    </div>

                    <div className="flex gap-2 w-full md:w-auto">
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 bg-purple-500 text-white rounded-2xl text-xs font-bold uppercase hover:bg-purple-600 transition-all shadow-md shadow-purple-200"
                        >
                            <ListPlus size={16} /> Tạo List
                        </button>
                        <button
                            onClick={() => setShowAddTicker(true)}
                            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 bg-white border border-purple-200 text-purple-600 rounded-2xl text-xs font-bold uppercase hover:bg-purple-50 transition-all"
                        >
                            <Plus size={16} /> Thêm mã
                        </button>
                        <button
                            onClick={handleBulkDelete}
                            disabled={selectedTickers.length === 0}
                            className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-2xl text-xs font-bold uppercase transition-all shadow-md ${selectedTickers.length > 0
                                ? "bg-rose-400 text-white shadow-rose-200 hover:bg-rose-500"
                                : "bg-slate-50 text-slate-300 border border-slate-100 shadow-none cursor-not-allowed"
                                }`}
                        >
                            <Trash2 size={14} /> Xoá Mã {selectedTickers.length > 0 && `(${selectedTickers.length})`}
                        </button>
                        <button
                            onClick={handleExportCSV}
                            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 text-white rounded-2xl text-[10px] font-black uppercase hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100"
                        >
                            <Download size={14} /> Xuất CSV
                        </button>
                    </div>
                </div>

                {/* Table Content */}
                <div className="overflow-x-auto">
                    {loading ? (
                        <div className="py-20 flex flex-col items-center justify-center gap-4">
                            <Loader2 className="animate-spin text-emerald-500" size={32} />
                            <p className="text-slate-400 font-black text-xs uppercase tracking-widest">Đang tải dữ liệu Pro...</p>
                        </div>
                    ) : filteredItems.length > 0 ? (
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-slate-50/50 text-slate-500 text-[13px] uppercase font-bold tracking-[0.12em] border-b border-slate-100">
                                <tr>
                                    <th className="p-4 pl-6 w-10">
                                        <div
                                            onClick={handleToggleSelectAll}
                                            className={`w-5 h-5 rounded-full border-2 flex items-center justify-center cursor-pointer transition-all ${selectedTickers.length === filteredItems.length && filteredItems.length > 0
                                                ? "bg-orange-500 border-orange-500"
                                                : "bg-white border-slate-200"
                                                }`}
                                        >
                                            {selectedTickers.length === filteredItems.length && filteredItems.length > 0 && (
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
                                    <th className="p-4 text-center">Biểu đồ</th>
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
                                {filteredItems.map(item => (
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
                                <Search size={24} className="text-slate-200" />
                            </div>
                            <p className="text-slate-400 font-bold">Chưa có mã nào trong danh sách này.</p>
                            <button onClick={() => setShowAddTicker(true)} className="mt-4 text-emerald-500 font-black text-xs uppercase hover:underline">Thêm mã ngay</button>
                        </div>
                    )}
                </div>

                <div className="p-5 bg-slate-50/50 border-t border-slate-100 flex justify-between items-center px-8">
                    <span className="text-sm font-bold text-slate-600 uppercase tracking-[0.05em]">{filteredItems.length} mã trong danh sách</span>
                    <span className="text-sm font-bold text-slate-500">
                        Cập nhật lúc: <span className="text-emerald-600 font-extrabold">{lastUpdated.toLocaleTimeString('vi-VN')}</span>
                    </span>
                </div>
            </div>

            {/* MODALS */}
            {showCreateModal && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[130] flex items-center justify-center p-4">
                    <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 border border-slate-100">
                        <h3 className="text-lg font-bold text-slate-700 uppercase mb-6 tracking-tight">Tạo danh sách mới</h3>
                        <div className="relative mb-8">
                            <input
                                type="text"
                                placeholder="Ví dụ: Công nghệ, Ngân hàng..."
                                value={newWLName}
                                onChange={(e) => setNewWLName(e.target.value)}
                                className="w-full p-5 bg-[#f8fafc] border-2 border-[#d1fae5] rounded-[24px] text-slate-700 outline-none focus:border-emerald-400 transition-all font-bold placeholder:text-slate-400"
                                autoFocus
                            />
                        </div>
                        <div className="flex gap-4">
                            <button onClick={() => setShowCreateModal(false)} className="flex-1 py-4 bg-[#f1f5f9] text-[#94a3b8] font-extrabold rounded-2xl text-[13px] uppercase hover:bg-slate-200 transition-all">Hủy</button>
                            <button onClick={handleCreateWL} className="flex-1 py-4 bg-[#00b894] text-white font-extrabold rounded-2xl text-[13px] uppercase hover:bg-[#00a383] transition-all shadow-lg shadow-emerald-100">Tạo ngay</button>
                        </div>
                    </div>
                </div>
            )}

            {showAddTicker && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[130] flex items-center justify-center p-4">
                    <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 border border-slate-100">
                        <h3 className="text-lg font-bold text-slate-700 uppercase mb-6 tracking-tight">Thêm mã theo dõi</h3>
                        <div className="relative mb-8">
                            <input
                                type="text"
                                placeholder="MÃ CHỨNG KHOÁN (VD: FPT)"
                                value={newTicker}
                                onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                                className="w-full p-5 bg-[#f8fafc] border-2 border-[#d1fae5] rounded-[24px] text-slate-700 outline-none focus:border-emerald-400 transition-all font-extrabold uppercase placeholder:text-slate-400"
                                autoFocus
                            />
                        </div>
                        <div className="flex gap-4">
                            <button onClick={() => setShowAddTicker(false)} className="flex-1 py-4 bg-[#f1f5f9] text-[#94a3b8] font-extrabold rounded-2xl text-[13px] uppercase hover:bg-slate-200 transition-all">Hủy</button>
                            <button onClick={handleAddTicker} className="flex-1 py-4 bg-[#00b894] text-white font-extrabold rounded-2xl text-[13px] uppercase hover:bg-[#00a383] transition-all shadow-lg shadow-emerald-100">Thêm</button>
                        </div>
                    </div>
                </div>
            )}
            {/* CONFIRM / SUCCESS MODAL */}
            {confirmModal.show && (
                <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[140] flex items-center justify-center p-4">
                    <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 border border-slate-100">
                        <div className="flex items-start gap-4 mb-6">
                            <div className="w-14 h-14 bg-[#f0f7ff] rounded-2xl flex items-center justify-center shrink-0 shadow-sm border border-blue-50">
                                <Activity className="text-[#2563eb]" size={28} />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-slate-800 uppercase leading-tight tracking-tight">{confirmModal.title === "Xác nhận xóa" ? "XÁC NHẬN XÓA" : confirmModal.title.toUpperCase()}</h3>
                                <div className="text-[11px] font-black text-blue-500 uppercase tracking-widest mt-0.5">HỆ THỐNG INFORMATION</div>
                            </div>
                        </div>

                        <div className="text-base text-[#4b5563] font-medium mb-10 leading-relaxed font-sans">
                            {confirmModal.message.split(' ').map((word, i) =>
                                word.startsWith('hoàn') || word.startsWith('tác') || word.includes('xóa')
                                    ? <span key={i} className="text-blue-600 font-bold underline decoration-2 underline-offset-4 mr-1">{word} </span>
                                    : word + ' '
                            )}
                        </div>

                        <div className="flex gap-4">
                            <button
                                onClick={() => setConfirmModal(prev => ({ ...prev, show: false }))}
                                className="flex-1 py-4 bg-[#f8fafc] text-[#94a3b8] font-extrabold rounded-2xl text-[13px] uppercase hover:bg-slate-100 transition-all"
                            >
                                {confirmModal.title === "Thêm mã thành công" ? "Đóng" : "Hủy bỏ"}
                            </button>
                            <button
                                onClick={confirmModal.onConfirm}
                                className={`flex-1 py-4 ${confirmModal.title === "Thêm mã thành công" ? "bg-[#00b894]" : "bg-[#2563eb]"} text-white font-extrabold rounded-2xl text-[13px] uppercase hover:opacity-90 transition-all shadow-lg ${confirmModal.title === "Thêm mã thành công" ? "shadow-emerald-100" : "shadow-blue-100"} active:scale-95`}
                            >
                                {confirmModal.title === "Thêm mã thành công" ? "Tuyệt vời" : "Xác nhận"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
