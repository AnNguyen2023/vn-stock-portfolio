"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";

export default function VnindexChart({ data, referencePrice, symbol }) {
    const chartContainerRef = useRef(null);

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        const chart = createChart(chartContainerRef.current, {
            height: 200,
            layout: {
                background: { type: ColorType.Solid, color: "#0f172a" },
                textColor: "#94a3b8",
            },
            grid: {
                vertLines: { color: "#1e293b" },
                horzLines: { color: "#1e293b" },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
                borderColor: "#334155",
            },
            rightPriceScale: {
                borderColor: "#334155",
            },
            crosshair: {
                mode: 0,
            },
        });

        // Price line series (green)
        const lineSeries = chart.addLineSeries({
            color: "#10b981",
            lineWidth: 2,
            crosshairMarkerVisible: true,
            crosshairMarkerRadius: 4,
            lastValueVisible: true,
            priceLineVisible: false,
        });

        // Transform data to lightweight-charts format
        const priceData = data.map((point) => ({
            time: point.time || point.timestamp,
            value: point.value || point.p,
        }));

        lineSeries.setData(priceData);

        // Volume histogram (light blue)
        const volumeSeries = chart.addHistogramSeries({
            color: "#60a5fa",
            priceFormat: {
                type: "volume",
            },
            priceScaleId: "",
            scaleMargins: {
                top: 0.7,
                bottom: 0,
            },
        });

        const volumeData = data
            .filter((point) => (point.volume || point.v) != null)
            .map((point) => ({
                time: point.time || point.timestamp,
                value: point.volume || point.v,
                color: "#60a5fa",
            }));

        volumeSeries.setData(volumeData);

        // Reference line (if provided)
        if (referencePrice) {
            lineSeries.createPriceLine({
                price: referencePrice,
                color: "#64748b",
                lineWidth: 1,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: "Ref",
            });
        }

        // Handle resize
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({
                    width: chartContainerRef.current.clientWidth,
                });
            }
        };

        const resizeObserver = new ResizeObserver(handleResize);
        resizeObserver.observe(chartContainerRef.current);

        // Fit content
        chart.timeScale().fitContent();

        return () => {
            resizeObserver.disconnect();
            chart.remove();
        };
    }, [data, referencePrice]);

    if (!data || data.length === 0) {
        return (
            <div className="flex items-center justify-center w-full h-[200px] bg-slate-900 rounded">
                <div className="text-center">
                    <span className="text-sm text-slate-400 italic">Chưa có dữ liệu phiên</span>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full">
            <div ref={chartContainerRef} className="w-full" />
            {symbol && (
                <div className="mt-2 text-xs text-slate-500 text-center">
                    {symbol} - Intraday Chart
                </div>
            )}
        </div>
    );
}
