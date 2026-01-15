"use client";
import React, { useState } from 'react';
import { X, Banknote, Scale, Info, ChevronDown } from 'lucide-react';
import { toast } from 'sonner';
import { registerDividend, API_BASE_URL } from '@/lib/api';
import axios from 'axios';

export default function DividendModal({
    isOpen,
    onClose,
    holdings = [],
    cashBalance = 0,
    initialData = null
}) {
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('stock'); // Default to CT Cổ Phiếu as per image
    const [formData, setFormData] = useState({
        ticker: holdings[0]?.ticker || '',
        ratio: '0',
        date: new Date().toISOString().split('T')[0],
        paymentDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        ownedQuantity: holdings[0]?.volume || 0,
        rightsQuantity: '0',
        purchasePrice: '0',
        registerDate: new Date().toISOString().split('T')[0]
    });

    const handleTickerChange = (ticker) => {
        const holding = holdings.find(h => h.ticker === ticker);
        setFormData({
            ...formData,
            ticker,
            ownedQuantity: holding ? holding.volume : 0
        });
    };

    // Update default ratio and auto-calculate rightsQuantity when tab, ratio or ownedQuantity changes
    React.useEffect(() => {
        if (activeTab === 'rights' && formData.ratio.includes(':')) {
            const [base, receive] = formData.ratio.split(':').map(Number);
            if (base > 0 && receive > 0) {
                const calculated = Math.floor((formData.ownedQuantity * receive) / base);
                setFormData(prev => ({ ...prev, rightsQuantity: calculated.toString() }));
            }
        }

        // Reset ratio ONLY if tab changed (detected by comparing activeTab)
        // We use a ref or just rely on the fact that this runs on every change
    }, [formData.ratio, formData.ownedQuantity, activeTab]);

    React.useEffect(() => {
        if (initialData) {
            // Populate form with initialData for editing
            setActiveTab(initialData.type === 'dividend_cash' ? 'cash'
                : initialData.type === 'dividend_stock' ? 'stock'
                    : 'rights');

            setFormData({
                ticker: initialData.ticker,
                ratio: initialData.ratio || '0',
                date: initialData.ex_dividend_date,
                paymentDate: initialData.payment_date,
                ownedQuantity: 0, // Will be updated by useEffect or need logic to fetch logic holding??
                // Wait, initialData usually doesn't have ownedQuantity snapshotted unless we stored it in 'owned_volume'
                // Yes, DividendRecord has owned_volume
                ownedQuantity: parseInt(initialData.owned_volume) || 0,
                rightsQuantity: initialData.rights_quantity?.toString() || '0',
                purchasePrice: initialData.purchase_price?.toString() || '0',
                registerDate: initialData.register_date || new Date().toISOString().split('T')[0]
            });
            // Also need amount_per_share logic for cash if ratio is amount?
            if (initialData.type === 'dividend_cash' && initialData.amount_per_share) {
                // If it was amount based, ratio might be null or something?
                // Backend schema: ratio is optional string. amount_per_share is optional decimal.
                // If we saved amount_per_share, we should show it in Ratio box?
                // Or if we saved ratio string, use it.
                if (!initialData.ratio && initialData.amount_per_share) {
                    setFormData(prev => ({ ...prev, ratio: initialData.amount_per_share.toString() }));
                }
            }
        } else {
            // Reset to defaults if no initialData (New Mode)
            setFormData(prev => ({
                ...prev,
                ratio: '0',
                rightsQuantity: '0',
                purchasePrice: '0',
                registerDate: new Date().toISOString().split('T')[0]
            }));
        }
    }, [initialData, activeTab]); // Dependencies: initialData is key. activeTab change should not wipe data if editing?

    // Modification: The existing useEffect that resets form on activeTab change will CONFLICT with the one above setting activeTab.
    // We need to disable the auto-reset if we are just switching tabs during initialization?
    // Actually, initializing activeTab sets the state. Then the other useEffect triggers.
    // We should guard the reset.

    React.useEffect(() => {
        if (!initialData) {
            setFormData(prev => ({
                ...prev,
                ratio: '0',
                rightsQuantity: '0',
                purchasePrice: '0',
                registerDate: new Date().toISOString().split('T')[0]
            }));
        }
    }, [activeTab]);

    const handleRegisterDividend = async () => {
        if (!formData.ticker) {
            toast.error("Vui lòng chọn mã chứng khoán");
            return;
        }

        setLoading(true);
        try {
            const isPercent = formData.ratio.includes('%');
            const payload = {
                ticker: formData.ticker,
                type: activeTab,
                ratio: formData.ratio,
                ex_dividend_date: formData.date,
                register_date: activeTab === 'rights' ? formData.registerDate : null,
                payment_date: formData.paymentDate,
                owned_quantity: formData.ownedQuantity,
                amount_per_share: (activeTab === 'cash' && !isPercent) ? parseFloat(formData.ratio.replace(/,/g, '')) : null,
                purchase_price: activeTab === 'rights' ? parseFloat(formData.purchasePrice.replace(/,/g, '')) || 0 : null,
                rights_quantity: activeTab === 'rights' ? parseInt(formData.rightsQuantity.replace(/,/g, '')) || 0 : null
            };

            if (initialData?.id) {
                // Edit Mode
                await axios.put(`${API_BASE_URL}/dividends/${initialData.id}`, payload);
                toast.success("Đã cập nhật cổ tức thành công");
            } else {
                // Create Mode
                await registerDividend(payload);
                toast.success("Đã đăng ký cổ tức thành công");
            }
            onClose();
        } catch (error) {
            console.error("Register dividend error:", error);
            const errorMsg = error.response?.data?.message || "Không thể kết nối với máy chủ";
            toast.error(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const tabs = [
        { id: 'cash', label: 'CT Tiền' },
        { id: 'stock', label: 'CT Cổ Phiếu' },
        { id: 'rights', label: 'Quyền mua' },
    ];

    // Simple calculation logic for "Dự kiến nhận"
    const calculateExpected = () => {
        const ratio = formData.ratio || '';
        let gross = 0;
        let units = 0;

        if (activeTab === 'cash') {
            if (ratio.includes('%')) {
                const rate = parseFloat(ratio.replace('%', '')) / 100;
                gross = formData.ownedQuantity * rate * 10000;
            } else {
                const amountPerStock = parseFloat(ratio.replace(/,/g, '')) || 0;
                gross = formData.ownedQuantity * amountPerStock;
            }
            const net = gross * 0.95; // 5% TNCN Tax
            return { gross, net, type: 'cash' };
        }

        if (activeTab === 'stock') {
            if (ratio.includes('%')) {
                const rate = parseFloat(ratio.replace('%', '')) / 100;
                units = Math.floor(formData.ownedQuantity * rate);
            } else if (ratio.includes(':')) {
                const [base, receive] = ratio.split(':').map(Number);
                if (base > 0 && receive > 0) {
                    units = Math.floor((formData.ownedQuantity * receive) / base);
                }
            }
            return { units, type: 'stock' };
        }

        if (activeTab === 'rights') {
            const qty = parseInt(formData.rightsQuantity.replace(/,/g, '')) || 0;
            const price = parseFloat(formData.purchasePrice.replace(/,/g, '')) || 0;
            const cost = qty * price;
            return { units: qty, cost, type: 'rights' };
        }

        return { gross: 0, net: 0, units: 0, type: 'none' };
    };

    const calculation = calculateExpected();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center p-4 z-[110] backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-white rounded-[32px] w-full max-w-[600px] shadow-2xl overflow-hidden transform animate-in zoom-in-95 duration-200 border border-slate-100">

                {/* Header */}
                <div className="p-6 flex items-center justify-between border-b border-slate-50">
                    <div className="flex items-center gap-3">
                        <div className="p-2.5 bg-amber-50 rounded-xl">
                            <Banknote size={24} className="text-orange-500" />
                        </div>
                        <h2 className="text-xl font-bold text-slate-800 tracking-tight">Quản lý Cổ tức</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-slate-600"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex px-2 border-b border-slate-100">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`flex-1 py-4 text-sm font-bold transition-all relative ${activeTab === tab.id
                                ? 'text-emerald-600'
                                : 'text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            {tab.label}
                            {activeTab === tab.id && (
                                <div className="absolute bottom-0 left-0 right-0 h-1 bg-emerald-500 rounded-t-full mx-8" />
                            )}
                        </button>
                    ))}
                </div>

                {/* Body */}
                <div className="p-8 space-y-6">
                    <div className="grid grid-cols-2 gap-6">
                        {/* Mã CK */}
                        <div className="space-y-2">
                            <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">Mã CK</label>
                            <div className="relative">
                                <select
                                    value={formData.ticker}
                                    onChange={(e) => handleTickerChange(e.target.value)}
                                    className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl font-bold text-slate-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all appearance-none"
                                >
                                    <option value="" disabled>Chọn mã CK</option>
                                    {holdings.map(h => (
                                        <option key={h.ticker} value={h.ticker}>{h.ticker}</option>
                                    ))}
                                </select>
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                                    <ChevronDown size={18} />
                                </div>
                            </div>
                        </div>

                        {/* Tỉ lệ chia / Số tiền */}
                        <div className="space-y-2">
                            <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">
                                {activeTab === 'cash' ? 'Tỉ lệ (%) hoặc Số tiền (đ/CP)' : 'Tỉ lệ chia (vd: 15% hoặc 100:15)'}
                            </label>
                            <div className="relative">
                                <input
                                    type="text"
                                    value={formData.ratio}
                                    onChange={(e) => setFormData({ ...formData, ratio: e.target.value })}
                                    className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl font-bold text-slate-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all pr-12"
                                    placeholder={activeTab === 'cash' ? "Ví dụ: 10% hoặc 1,000" : "15% hoặc 100:15"}
                                />
                                {activeTab !== 'cash' && <Scale size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-300" />}
                                {activeTab === 'cash' && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 font-bold text-xs uppercase">{formData.ratio.includes('%') ? '%' : 'đ'}</span>}
                            </div>
                        </div>

                        {/* Ngày GDKHQ */}
                        <div className="space-y-2">
                            <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">Ngày GDKHQ</label>
                            <div className="relative">
                                <input
                                    type="date"
                                    value={formData.date}
                                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                                    className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl font-bold text-slate-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all"
                                />
                            </div>
                        </div>

                        {/* Số lượng */}
                        <div className="space-y-2">
                            <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">Số lượng CP sở hữu</label>
                            <div className="relative">
                                <input
                                    type="text"
                                    readOnly
                                    value={formData.ownedQuantity.toLocaleString()}
                                    className="w-full p-4 bg-slate-100 border border-slate-100 rounded-2xl font-bold text-slate-700 outline-none"
                                />
                            </div>
                        </div>

                        {/* Quyền mua: Số lượng & Giá mua */}
                        {activeTab === 'rights' && (
                            <>
                                <div className="space-y-2 animate-in slide-in-from-left-4 duration-300">
                                    <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">SL CP mua ưu đãi</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={formData.rightsQuantity}
                                            onChange={(e) => setFormData({ ...formData, rightsQuantity: e.target.value })}
                                            className="w-full p-4 bg-emerald-50/50 border border-emerald-100 rounded-2xl font-bold text-emerald-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all"
                                            placeholder="0"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2 animate-in slide-in-from-right-4 duration-300">
                                    <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">Giá mua (đ/CP)</label>
                                    <div className="relative">
                                        <input
                                            type="text"
                                            value={formData.purchasePrice}
                                            onChange={(e) => setFormData({ ...formData, purchasePrice: e.target.value })}
                                            className="w-full p-4 bg-orange-50/50 border border-orange-100 rounded-2xl font-bold text-orange-700 outline-none focus:ring-4 focus:ring-orange-50 transition-all"
                                            placeholder="0"
                                        />
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Ngày nhận & Đăng ký (Cho Quyền mua) */}
                        {activeTab === 'rights' && (
                            <div className="space-y-2">
                                <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">Ngày đăng ký mua</label>
                                <div className="relative">
                                    <input
                                        type="date"
                                        value={formData.registerDate}
                                        onChange={(e) => setFormData({ ...formData, registerDate: e.target.value })}
                                        className="w-full p-4 bg-emerald-50 border border-emerald-100 rounded-2xl font-bold text-emerald-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all"
                                    />
                                </div>
                            </div>
                        )}

                        {/* Ngày nhận (Cho cả Tiền và Quyền mua) */}
                        {(activeTab === 'cash' || activeTab === 'rights') && (
                            <div className="space-y-2">
                                <label className="text-[11px] font-medium text-slate-700 uppercase tracking-widest px-1">
                                    {activeTab === 'cash' ? 'Ngày nhận tiền' : 'Ngày cổ phiếu về'}
                                </label>
                                <div className="relative">
                                    <input
                                        type="date"
                                        value={formData.paymentDate}
                                        onChange={(e) => setFormData({ ...formData, paymentDate: e.target.value })}
                                        className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl font-bold text-slate-700 outline-none focus:ring-4 focus:ring-emerald-50 transition-all"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Info Box */}
                    <div className="bg-emerald-50 border border-emerald-100 p-5 rounded-2xl flex gap-4 items-start">
                        <div className="p-1 bg-emerald-500 rounded-full text-white mt-0.5">
                            <Info size={14} />
                        </div>
                        <div className="flex-1">
                            <p className="text-emerald-700 font-bold text-sm">
                                {activeTab === 'cash' ? 'Số tiền thực nhận (sau thuế 5%)' :
                                    activeTab === 'rights' ? 'SL CP dự kiến sở hữu thêm' : 'Dự kiến nhận cổ phiếu'}
                            </p>
                            <div className="flex flex-col">
                                <p className="text-2xl font-normal text-emerald-600">
                                    {activeTab === 'cash'
                                        ? <span>{calculation.net.toLocaleString()} <span className="text-[0.8em]">VND</span></span>
                                        : <span>+{calculation.units.toLocaleString()} <span className="text-[0.8em]">CP</span></span>
                                    }
                                </p>

                                {activeTab === 'cash' && calculation.gross > 0 && (
                                    <div className="mt-1 space-y-0.5">
                                        <p className="text-[12.5px] text-emerald-600/70 font-medium">
                                            Tổng cổ tức: <span className="font-bold">{calculation.gross.toLocaleString()} VND</span>
                                        </p>
                                        <p className="text-[12.5px] text-orange-600/70 font-medium">
                                            Thuế TNCN (5%): <span className="font-bold">-{(calculation.gross * 0.05).toLocaleString()} VND</span>
                                        </p>
                                    </div>
                                )}

                                {activeTab === 'rights' && calculation.cost > 0 && (
                                    <div className="mt-1 space-y-0.5">
                                        <p className="text-[12.5px] text-emerald-600/70 font-medium">
                                            Tổng tiền cần nạp: <span className="font-bold text-orange-600">{calculation.cost.toLocaleString()} VND</span>
                                        </p>
                                        <p className="text-[10px] text-slate-400 italic">
                                            * Hệ thống sẽ tự động trừ tiền mặt vào ngày CP về
                                        </p>

                                        {/* Cảnh báo nạp tiền */}
                                        {(() => {
                                            const regDate = new Date(formData.registerDate);
                                            const today = new Date();
                                            today.setHours(0, 0, 0, 0);
                                            regDate.setHours(0, 0, 0, 0);
                                            const diffTime = regDate - today;
                                            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                                            if (diffDays <= 5 && cashBalance < calculation.cost) {
                                                return (
                                                    <div className="mt-3 p-3 bg-rose-50 border border-rose-100 rounded-xl flex items-center gap-2 text-rose-600 animate-pulse">
                                                        <Info size={14} className="shrink-0" />
                                                        <p className="text-[11px] font-bold uppercase tracking-tight">Cần nạp tiền để đảm bảo quyền mua CP</p>
                                                    </div>
                                                );
                                            }
                                            return null;
                                        })()}
                                    </div>
                                )}

                                <p className="text-xs text-emerald-600 font-medium mt-2 italic">
                                    {activeTab === 'cash'
                                        ? `Dự kiến cộng vào NAV ngày: ${new Date(formData.paymentDate).toLocaleDateString('vi-VN')}`
                                        : `Cổ phiếu sẽ về tài khoản ngày: ${new Date(formData.paymentDate).toLocaleDateString('vi-VN')}`
                                    }
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Footer Buttons */}
                    <div className="flex gap-4 pt-4">
                        <button
                            onClick={handleRegisterDividend}
                            disabled={loading}
                            className={`flex-[2] py-4 bg-emerald-500 text-white font-bold rounded-2xl shadow-lg shadow-emerald-100 hover:bg-emerald-600 active:scale-[0.98] transition-all text-sm uppercase tracking-wide flex items-center justify-center gap-2 ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
                        >
                            {loading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                    Đang xử lý...
                                </>
                            ) : "Xác nhận"}
                        </button>
                        <button
                            onClick={onClose}
                            className="flex-1 py-4 bg-slate-50 text-slate-700 font-medium rounded-2xl hover:bg-slate-100 transition-all text-sm uppercase tracking-wide"
                        >
                            Hủy
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
