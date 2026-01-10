"use client";
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Activity, RefreshCw } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer, YAxis, CartesianGrid, ReferenceLine } from 'recharts';
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

        // --- DATA SANITIZATION (Frontend Hotfix) ---
        // Indices are usually around 1000-2000. VND prices are 1,000,000+.
        const scaleFactor = (indexData.price > 10000) ? 1000 : 1;

        let displayPrice = indexData.price / scaleFactor;
        let displayChange = indexData.change / scaleFactor;

        // Reference price (previous close) must use the same scale
        const refPrice = displayPrice - displayChange;
        const hasData = displayPrice > 0;

        // Sparkline normalizing: Force Point scale (e.g. 1860 instead of 1860000)
        let sparkValues = (indexData.sparkline || []).map(v => (v > 10000 ? v / 1000 : v));

        // --- Anchor: Chart always starts at 9:00 AM (Ref Price) ---
        if (sparkValues.length > 0) {
            // Prepend refPrice to represent the 9:00 AM status
            sparkValues = [refPrice, ...sparkValues];
        }

        const chartData = sparkValues.map((val, i) => ({ i, value: val }));
        const showChart = chartData.length > 1;

        // Advanced coloring: Green above ref, Red below ref
        const maxY = Math.max(...sparkValues, refPrice);
        const minY = Math.min(...sparkValues, refPrice);
        const range = maxY - minY;

        // Offset for gradient (0 is top/maxY, 1 is bottom/minY)
        const offset = range > 0 ? (maxY - refPrice) / range : 0.5;

        const colorGreen = '#10b981';
        const colorRed = '#f43f5e';

        if (!hasData) {
            return (
                <div className="flex-1 bg-white border border-slate-200 rounded-xl p-3 flex items-center justify-center shadow-sm">
                    <p className="text-slate-400 text-sm">Chưa có dữ liệu</p>
                </div>
            );
        }

        return (
            <div className="flex-1 bg-slate-50 border border-slate-300 rounded-xl p-3 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
                {/* Header Info */}
                <div className="flex justify-between items-start mb-2 relative z-10">
                    <div>
                        <div className="flex items-center gap-1 mb-0.5">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">{indexData.index}</h4>
                        </div>
                        <div className="flex items-baseline gap-2">
                            <div className="flex items-center gap-1">
                                {isPositive ? (
                                    <TrendingUp size={20} className="text-emerald-700" />
                                ) : (
                                    <TrendingDown size={20} className="text-rose-600" />
                                )}
                                <span className={`text-2xl font-bold ${isPositive ? 'text-emerald-700' : 'text-rose-600'}`}>
                                    {displayPrice?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                            </div>
                            <span className={`text-base font-bold ${isPositive ? 'text-emerald-700' : 'text-rose-600'}`}>
                                {isPositive ? '+' : ''}{displayChange?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({indexData.change_pct?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%)
                            </span>
                        </div>
                    </div>
                </div>

                {/* Chart Area */}
                <div className="h-16 -mx-3 mb-2 bg-white/40 border-y border-slate-200">
                    {showChart ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={chartData} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id={`gradient-${indexData.index}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0" stopColor={colorGreen} stopOpacity={0.4} />
                                        <stop offset={offset} stopColor={colorGreen} stopOpacity={0.4} />
                                        <stop offset={offset} stopColor={colorRed} stopOpacity={0.4} />
                                        <stop offset="1" stopColor={colorRed} stopOpacity={0.4} />
                                    </linearGradient>
                                    <linearGradient id={`stroke-${indexData.index}`} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0" stopColor={colorGreen} stopOpacity={1} />
                                        <stop offset={offset} stopColor={colorGreen} stopOpacity={1} />
                                        <stop offset={offset} stopColor={colorRed} stopOpacity={1} />
                                        <stop offset="1" stopColor={colorRed} stopOpacity={1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid vertical={false} horizontal={true} stroke="#e2e8f0" strokeDasharray="1 3" />
                                <YAxis domain={[minY - (range * 0.1), maxY + (range * 0.1)]} hide />
                                <ReferenceLine
                                    y={refPrice}
                                    stroke="#64748b"
                                    strokeDasharray="3 3"
                                    strokeWidth={1}
                                    label={{
                                        position: 'top',
                                        value: refPrice.toLocaleString('en-US', { maximumFractionDigits: 2 }),
                                        fill: '#475569',
                                        fontSize: 10,
                                        fontWeight: 'bold',
                                        offset: 5
                                    }}
                                />
                                <Area
                                    type="linear"
                                    dataKey="value"
                                    stroke={`url(#stroke-${indexData.index})`}
                                    strokeWidth={3}
                                    fillOpacity={1}
                                    fill={`url(#gradient-${indexData.index})`}
                                    baseValue={refPrice}
                                    isAnimationActive={false}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="h-full flex items-center justify-center text-slate-300 text-xs">No Chart</div>
                    )}
                </div>

                {/* Footer Info */}
                <div className="flex items-center justify-between text-xs text-slate-700 relative z-10 border-t border-slate-200 pt-2">
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Khối lượng</span>
                        <span className="font-bold text-slate-700">
                            {indexData.volume > 0
                                ? `${(indexData.volume / 1e6).toLocaleString('en-US', { maximumFractionDigits: 1 })}M`
                                : '--'}
                        </span>
                    </div>

                    <div className="flex flex-col items-end">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-tighter">Thanh khoản</span>
                        <span className="font-bold text-slate-700">
                            {indexData.value > 0
                                ? `${indexData.value.toLocaleString('en-US', { maximumFractionDigits: 1 })} Tỷ`
                                : '-- Tỷ'}
                        </span>
                    </div>
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
                            {new Date(data[0].last_updated).toLocaleDateString('vi-VN')}
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
