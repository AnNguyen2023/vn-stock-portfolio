"use client";
import React, { useEffect, useRef } from "react";
import { createChart, ColorType, LineStyle, BaselineSeries, HistogramSeries } from "lightweight-charts";
import { Activity } from "lucide-react";

export default function VnindexWidget({ data, sessionInfo, refLevel, symbol }) {
    const chartContainerRef = useRef(null);
    const chartRef = useRef(null);

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        // Initialize Chart
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: "#ffffff" },
                textColor: "#334155",
                fontSize: 10,
                fontFamily: "Inter, sans-serif",
            },
            grid: {
                vertLines: { color: "rgba(226, 232, 240, 0.5)", visible: true },
                horzLines: { color: "rgba(226, 232, 240, 0.5)", visible: true },
            },
            width: chartContainerRef.current.clientWidth,
            height: 180,
            timeScale: {
                visible: true,
                borderColor: "#e2e8f0",
                timeVisible: true,
                secondsVisible: false,
                tickMarkFormatter: (time) => {
                    const date = new Date(time * 1000);
                    return date.toLocaleTimeString('vi-VN', {
                        timeZone: 'Asia/Ho_Chi_Minh',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                    });
                },
            },
            rightPriceScale: {
                visible: true,
                borderColor: "#e2e8f0",
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.25,
                },
            },
            leftPriceScale: {
                visible: false,
            },
            crosshair: {
                mode: 0, // Normal
                vertLine: { color: "#94a3b8", labelVisible: false, style: LineStyle.SparseDashed },
                horzLine: { color: "#94a3b8", labelVisible: false, style: LineStyle.SparseDashed },
            },
            handleScale: false,
            handleScroll: false,
        });

        chartRef.current = chart;

        // Use BaselineSeries for segment-based coloring (Green if > ref, Red if < ref)
        const baselineSeries = chart.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: refLevel || (data[0].p || data[0].value) },
            topLineColor: "#22c55e", // Green
            topFillColor1: "rgba(34, 197, 94, 0.05)",
            topFillColor2: "rgba(34, 197, 94, 0)",
            bottomLineColor: "#ef4444", // Red
            bottomFillColor1: "rgba(239, 68, 68, 0)",
            bottomFillColor2: "rgba(239, 68, 68, 0.05)",
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
        });

        // Prepare Price Data
        // Ensure data is sorted by time
        const sortedData = [...data].sort((a, b) => (a.timestamp || a.time) - (b.timestamp || b.time));
        const priceData = sortedData.map((p) => ({
            time: p.timestamp || p.time,
            value: p.value || p.p,
        }));

        baselineSeries.setData(priceData);

        // Volume Histogram (Gray, at bottom)
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: "rgba(148, 163, 184, 0.2)",
            priceFormat: { type: "volume" },
            priceScaleId: "", // Overlay
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });

        const volumeData = sortedData
            .filter((p) => (p.volume || p.v) != null)
            .map((p) => ({
                time: p.timestamp || p.time,
                value: p.volume || p.v,
            }));

        volumeSeries.setData(volumeData);

        // Reference Line (Orange, Dashed)
        if (refLevel) {
            baselineSeries.createPriceLine({
                price: refLevel,
                color: "#f97316", // Orange
                lineWidth: 1,
                lineStyle: LineStyle.Dashed,
                axisLabelVisible: true,
                axisLabelBackgroundColor: "#eab308", // Yellow background for label
                axisLabelTextColor: "#000000",
                title: "", // We want the value on the axis
            });
        }

        // Adjust Time Scale for 09:00 - 15:00 (Asia/Ho_Chi_Minh)
        if (priceData.length > 0) {
            const firstTime = priceData[0].time;
            const date = new Date(firstTime * 1000);
            const vnDateStr = date.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }); // YYYY-MM-DD

            const startRange = Math.floor(new Date(`${vnDateStr}T09:00:00+07:00`).getTime() / 1000);
            const endRange = Math.floor(new Date(`${vnDateStr}T15:00:00+07:00`).getTime() / 1000);

            chart.timeScale().setVisibleRange({
                from: startRange,
                to: endRange,
            });
        }

        // Resize Handler
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        const resizeObserver = new ResizeObserver(handleResize);
        resizeObserver.observe(chartContainerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
        };
    }, [data, refLevel]);

    if (!data || data.length === 0 || !sessionInfo) {
        return (
            <div className="bg-white rounded-xl border border-slate-200 p-4 h-[320px] flex items-center justify-center shadow-sm">
                <div className="flex flex-col items-center gap-2">
                    <Activity className="text-slate-300 animate-pulse" size={24} />
                    <span className="text-slate-400 text-xs font-medium">Đang tải {symbol || "Index"}...</span>
                </div>
            </div>
        );
    }

    const changeAbs = sessionInfo.change_abs || 0;
    const changePct = sessionInfo.change_pct || 0;
    const isUp = changeAbs > 0;
    const isDown = changeAbs < 0;
    const colorClass = isUp ? "text-emerald-500" : isDown ? "text-rose-500" : "text-yellow-500";
    const bgClass = isUp ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-slate-50 text-slate-400 border-slate-100";

    const formatNumber = (num, decimals = 2) =>
        (num || 0).toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

    const formatVolume = (vol) => {
        if (vol >= 1_000_000_000) return `${(vol / 1_000_000_000).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B CP`;
        if (vol >= 1_000_000) return `${(vol / 1_000_000).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}M CP`;
        return `${vol.toLocaleString("en-US")} CP`;
    };

    const formatValue = (val) => `${(val / 1_000_000_000).toLocaleString("en-US", { minimumFractionDigits: 3, maximumFractionDigits: 3 })} Tỷ`;

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col group hover:shadow-md transition-shadow h-full">
            {/* Header Area */}
            <div className="p-3 pb-0 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <h4 className="text-sm font-black text-slate-700 uppercase tracking-wider">{symbol || sessionInfo.index_name}</h4>
                    <div className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${bgClass} flex items-center gap-1`}>
                        <Activity size={10} className={isUp ? "animate-pulse" : ""} />
                        LIVE
                    </div>
                </div>
            </div>

            {/* Chart Area */}
            <div className="px-2" ref={chartContainerRef} style={{ height: "180px", position: "relative" }} />

            {/* Info Area */}
            <div className="p-4 pt-1 bg-slate-50/30 border-t border-slate-100 mt-auto">
                <div className="flex justify-between items-start mb-3">
                    {/* Left: Big Price */}
                    <div>
                        <span className={`text-[28px] font-bold tracking-tight tabular-nums ${colorClass}`}>
                            {formatNumber(sessionInfo.last_value)}
                        </span>
                    </div>
                    {/* Right: Change Stacked */}
                    <div className="flex flex-col items-end">
                        <span className={`text-sm font-bold tabular-nums ${colorClass}`}>
                            {isUp ? "+" : ""}{formatNumber(changeAbs)}
                        </span>
                        <span className={`text-sm font-bold tabular-nums ${colorClass}`}>
                            {isUp ? "+" : ""}{formatNumber(changePct)}%
                        </span>
                    </div>
                </div>

                {/* Bottom Row */}
                <div className="grid grid-cols-2 gap-4 border-t border-slate-100 pt-2.5">
                    <div className="flex flex-col">
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">Khối lượng</span>
                        <span className="text-[13px] font-bold text-slate-900 tabular-nums">
                            {formatVolume(sessionInfo.total_volume)}
                        </span>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest leading-none mb-1">Thanh khoản</span>
                        <span className="text-[13px] font-bold text-slate-900 tabular-nums">
                            {formatValue(sessionInfo.total_value)}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
}
