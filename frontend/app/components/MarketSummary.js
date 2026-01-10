"use client";
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Activity, RefreshCw } from 'lucide-react';
import { getMarketSummary } from '../../lib/api';

export default function MarketSummary() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const response = await getMarketSummary();
            if (response.data?.status === 'success') {
                setData(response.data.data);
                setLastUpdate(new Date());
            }
        } catch (error) {
            console.error('Error fetching market summary:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // Auto refresh every 30 seconds
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const IndexCard = ({ indexData }) => {
        if (!indexData) return null;

        const isPositive = indexData.change >= 0;
        const hasData = indexData.price > 0;

        if (!hasData) {
            return (
                <div className="flex-1 bg-slate-50 rounded-xl p-3 flex items-center justify-center">
                    <p className="text-slate-400 text-sm">Chưa có dữ liệu</p>
                </div>
            );
        }

        return (
            <div className="flex-1 bg-slate-50/60 rounded-xl p-2.5">
                {/* Line 1: Index name + Price + Change */}
                <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-slate-700 uppercase">{indexData.index} ▼</span>
                    <div className="flex items-center gap-1.5">
                        <span className={`text-lg font-semibold ${isPositive ? 'text-emerald-600' : 'text-rose-500'}`}>
                            {isPositive ? '↑' : '↓'} {indexData.price?.toLocaleString('vi-VN', { minimumFractionDigits: 2 })}
                        </span>
                        <span className={`text-sm font-medium ${isPositive ? 'text-emerald-600' : 'text-rose-500'}`}>
                            ({indexData.change?.toFixed(2)} {indexData.change_pct?.toFixed(2)}%)
                        </span>
                    </div>
                </div>

                {/* Line 2: Volume + Value */}
                <div className="flex items-center justify-between mb-1">
                    <span className="text-base font-normal text-slate-800">
                        {indexData.volume > 0 ? (
                            <>{(indexData.volume / 1e6).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} CP</>
                        ) : (
                            <>-- CP</>
                        )}
                    </span>
                    <span className="text-base font-normal text-slate-800">
                        {indexData.value > 0 ? (
                            <>{indexData.value?.toLocaleString('vi-VN', { maximumFractionDigits: 2 })} Tỷ</>
                        ) : (
                            <>-- Tỷ</>
                        )}
                    </span>
                </div>

                {/* Line 3: Market breadth + Status */}
                <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                        {indexData.advance > 0 && (
                            <span className="text-emerald-600 font-medium">↑ {indexData.advance} ({indexData.advance_strong || 0})</span>
                        )}
                        {indexData.no_change > 0 && (
                            <span className="text-amber-600 font-medium">— {indexData.no_change}</span>
                        )}
                        {indexData.decline > 0 && (
                            <span className="text-rose-500 font-medium">↓ {indexData.decline} ({indexData.decline_strong || 0})</span>
                        )}
                    </div>
                    {indexData.is_closed && (
                        <span className="text-slate-500 font-medium">Đóng cửa</span>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-400 p-3">
            {/* Header */}
            <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-3">
                    <BarChart3 size={18} className="text-slate-600" />
                    <h3 className="text-base font-medium text-slate-600 uppercase tracking-tight">Thông tin Thị trường</h3>
                    {data && data.length > 0 && data[0].last_updated && (
                        <span className="text-xs font-medium text-slate-500">
                            Phiên: {new Date(data[0].last_updated).toLocaleDateString('vi-VN')}
                        </span>
                    )}
                </div>
                <button
                    onClick={fetchData}
                    disabled={loading}
                    className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors"
                    title="Làm mới"
                >
                    <RefreshCw size={14} className={`text-slate-400 ${loading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {loading && !data ? (
                <div className="flex items-center justify-center h-24">
                    <Activity size={24} className="text-slate-300 animate-pulse" />
                </div>
            ) : data && data.length > 0 ? (
                <div className="flex gap-2.5">
                    {data.map((indexData, idx) => (
                        <IndexCard key={idx} indexData={indexData} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-8">
                    <p className="text-slate-400 text-sm">Không thể tải dữ liệu thị trường</p>
                </div>
            )}
        </div>
    );
}
