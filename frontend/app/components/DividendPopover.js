import React, { useState, useEffect } from 'react';
import { Loader2, Trash2, Edit2, Info, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE_URL } from '@/lib/api';
import axios from 'axios';

export default function DividendPopover({ onClose, onEdit }) {
    const [loading, setLoading] = useState(true);
    const [dividends, setDividends] = useState([]);

    useEffect(() => {
        fetchDividends();
    }, []);

    const fetchDividends = async () => {
        try {
            const res = await axios.get(`${API_BASE_URL}/dividends/pending`);
            setDividends(res.data);
        } catch (error) {
            console.error("Failed to fetch dividends:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id, ticker) => {
        if (!confirm(`Bạn có chắc chắn muốn xóa lịch cổ tức của ${ticker}?`)) return;

        try {
            await axios.delete(`${API_BASE_URL}/dividends/${id}`);
            toast.success(`Đã xóa cổ tức ${ticker}`);
            fetchDividends(); // Reload
        } catch (error) {
            toast.error("Không thể xóa cổ tức");
        }
    };

    if (loading) {
        return (
            <div className="p-4 flex justify-center items-center text-slate-400">
                <Loader2 size={24} className="animate-spin" />
            </div>
        );
    }

    if (dividends.length === 0) {
        return (
            <div className="p-4 text-center text-slate-500 text-sm">
                <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-2 text-slate-400">
                    <Info size={20} />
                </div>
                <p>Không có cổ tức nào đang chờ.</p>
            </div>
        );
    }

    return (
        <div className="w-[400px] max-h-[400px] overflow-y-auto bg-white rounded-xl shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <div className="p-3 border-b border-slate-100 bg-slate-50 sticky top-0 z-10">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Cổ tức đang chờ ({dividends.length})</h3>
            </div>
            <div className="divide-y divide-slate-100">
                {dividends.map((div) => (
                    <div key={div.id} className="p-4 hover:bg-slate-50 transition-colors group">
                        <div className="flex justify-between items-start mb-1">
                            <div>
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-slate-800">{div.ticker}</span>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${div.type === 'dividend_cash' ? 'bg-emerald-100 text-emerald-700' :
                                        div.type === 'dividend_stock' ? 'bg-blue-100 text-blue-700' :
                                            'bg-purple-100 text-purple-700'
                                        }`}>
                                        {div.type === 'dividend_cash' ? 'Tiền' :
                                            div.type === 'dividend_stock' ? 'Cổ phiếu' : 'Quyền mua'}
                                    </span>
                                </div>
                                <div className="text-xs text-slate-500 mt-1 space-y-0.5">
                                    <p>Thực nhận: <span className="font-medium text-slate-700">
                                        {div.type === 'dividend_cash'
                                            ? `${div.expected_value.toLocaleString()} đ`
                                            : `${div.expected_value.toLocaleString()} CP`
                                        }
                                    </span></p>
                                    <p>Ngày về: {new Date(div.payment_date).toLocaleDateString('vi-VN')}</p>
                                </div>
                            </div>
                            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button
                                    onClick={() => onEdit && onEdit(div)}
                                    className="p-1.5 text-blue-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                    title="Sửa"
                                >
                                    <Edit2 size={16} />
                                </button>
                                <button
                                    onClick={() => handleDelete(div.id, div.ticker)}
                                    className="p-1.5 text-rose-400 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                                    title="Xóa"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
