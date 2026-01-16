"use client";
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Clock, Activity, ChevronDown, BarChart3, RefreshCw } from 'lucide-react';
import LightweightChart from './LightweightChart';
import { getMarketSummary } from '../../lib/api';
import LiveTicker from './LiveTicker';

export default function MarketSummary() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [lastUpdate, setLastUpdate] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            const response = await getMarketSummary();
            const isSuccess = response.data?.success || response.data?.status === 'success';

            if (isSuccess || Array.isArray(response.data)) {
                const marketData = Array.isArray(response.data) ? response.data : response.data.data;
                if (marketData) {
                    setData(marketData);
                    setLastUpdate(new Date());
                }
            }
        } catch (error) {
            console.error('Error fetching market summary:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000);
        return () => clearInterval(interval);
    }, []);

    const IndexCard = ({ indexData }) => {
        if (!indexData) return null;

        const isPositive = indexData.change >= 0;

        const colorGreen = '#10b981';
        const colorRed = '#f43f5e';

        const displayPrice = indexData.price;
        const displayChange = indexData.change;
        const refPrice = indexData.ref_price || (displayPrice - displayChange);
        const hasData = displayPrice > 0;
        const showChart = indexData.sparkline && indexData.sparkline.length > 0;

        if (!hasData) {
            return (
                <div className="flex-1 bg-white border border-slate-200 rounded-xl p-3 flex items-center justify-center shadow-sm min-h-[180px]">
                    <p className="text-slate-400 text-sm italic">Chưa có dữ liệu</p>
                </div>
            );
        }

        return (
            <div className="flex-1 bg-slate-50 border border-slate-200 rounded-xl p-3 shadow-sm relative overflow-hidden flex flex-col group min-h-[176px] hover:shadow-md transition-shadow">
                {/* Header - Index Name & Live Badge */}
                <div className="flex items-center gap-2 mb-2 relative z-10 px-1">
                    <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{indexData.index}</h4>
                    <div className="flex items-center gap-1 bg-emerald-50 px-1.5 py-0.5 rounded text-[8px] font-bold text-emerald-600 animate-pulse border border-emerald-100">
                        <Activity size={8} />
                        LIVE
                    </div>
                </div>

                {/* Chart Area */}
                <div className="flex-1 -mx-3 mb-2 min-h-[80px] relative bg-white/50 overflow-hidden">
                    {showChart ? (
                        <LightweightChart
                            data={indexData.sparkline}
                            refPrice={refPrice}
                            isPositive={isPositive}
                            ticker={indexData.index}
                            height={100}
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center text-slate-300 text-[10px] font-black uppercase tracking-widest">No Chart Data</div>
                    )}
                </div>

                {/* Price & Change Info - Below Chart */}
                <div className="flex justify-between items-start mb-2 relative z-10 px-1 border-t border-slate-100 pt-2">
                    <div className="flex flex-col">
                        <div className="flex items-baseline gap-2">
                            <span className={`text-[25px] font-bold tabular-nums tracking-tight ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                                {displayPrice?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className={`text-base font-bold tabular-nums flex items-center gap-1 ${isPositive ? 'text-emerald-600' : 'text-rose-600'}`}>
                            {isPositive ? <TrendingUp size={16} strokeWidth={3} /> : <TrendingDown size={16} strokeWidth={3} />}
                            {isPositive ? '+' : ''}{displayChange?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </span>
                        <span className={`text-[13px] font-bold tabular-nums ${isPositive ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {indexData.change_pct?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%
                        </span>
                    </div>
                </div>

                {/* Footer - Volume & Liquidity */}
                <div className="flex items-center justify-between text-[10px] text-slate-500 relative z-10 border-t border-slate-100 pt-2 px-1">
                    <div className="flex flex-col">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-tight">Khối lượng</span>
                        <span className="text-[14.5px] font-bold text-slate-900 tabular-nums">
                            {indexData.volume > 0
                                ? `${(indexData.volume / 1000000).toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}M CP`
                                : '-- CP'}
                        </span>
                    </div>

                    <div className="flex flex-col items-end">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-tight">Thanh khoản</span>
                        <span className="text-[14.5px] font-bold text-slate-900 tabular-nums">
                            {indexData.value > 0
                                ? `${indexData.value.toLocaleString('en-US', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} Tỷ`
                                : '-- Tỷ'}
                        </span>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-300 p-3 mb-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-3 gap-4">
                <div className="flex items-center gap-3 whitespace-nowrap">
                    <BarChart3 size={18} className="text-slate-600" />
                    <h3 className="text-[14px] sm:text-base font-black text-slate-700 uppercase tracking-tighter">Thông tin Thị trường</h3>
                    {data && data.length > 0 && data[0].last_updated && (
                        <span className="text-xs font-bold text-slate-400 hidden md:inline">
                            {new Date(data[0].last_updated).toLocaleDateString('vi-VN')}
                        </span>
                    )}
                </div>

                <div className="flex-1 min-w-0 flex items-center gap-2">
                    <div className="flex-1 min-w-0">
                        <LiveTicker />
                    </div>
                    <button
                        onClick={fetchData}
                        disabled={loading}
                        className="h-10 w-10 flex items-center justify-center bg-slate-50 border border-slate-200 rounded-xl hover:bg-slate-100 hover:border-slate-300 transition-all shadow-sm group"
                        title="Làm mới"
                    >
                        <RefreshCw size={14} className={`text-slate-400 group-hover:text-emerald-500 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {loading && !data ? (
                <div className="flex items-center justify-center h-48 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                    <Activity size={24} className="text-slate-300 animate-pulse" />
                </div>
            ) : data && data.length > 0 ? (
                <div className="flex flex-col lg:flex-row gap-3">
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
