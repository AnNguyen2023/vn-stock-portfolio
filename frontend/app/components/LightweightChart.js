"use client";
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, BaselineSeries, LineSeries } from 'lightweight-charts';

const LightweightChart = ({
    data,
    refPrice,
    isPositive,
    ticker,
    height = 120,
}) => {
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#64748b',
                fontSize: 10,
                fontFamily: 'Inter, sans-serif',
                attributionLogo: false,
            },
            grid: {
                vertLines: { color: 'rgba(148, 163, 184, 0.1)', visible: false },
                horzLines: { color: 'rgba(148, 163, 184, 0.1)', visible: false },
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            timeScale: {
                visible: true,
                borderVisible: false,
                secondsVisible: false,
                timeVisible: true,
                barSpacing: 2,
                tickMarkFormatter: (time) => {
                    const dt = new Date(time * 1000);
                    const h = String(dt.getHours()).padStart(2, '0');
                    return `${h}h`;
                },
            },
            rightPriceScale: {
                visible: false,
                borderVisible: false,
                scaleMargins: {
                    top: 0.15,
                    bottom: 0.25,
                },
            },
            handleScroll: false,
            handleScale: false,
        });

        // 1. Baseline Series (green above ref, red below ref)
        const priceSeries = chart.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: refPrice },
            topLineColor: '#22c55e',
            topFillColor1: 'rgba(34, 197, 94, 0.18)',
            topFillColor2: 'rgba(34, 197, 94, 0.0)',
            bottomLineColor: '#ef4444',
            bottomFillColor1: 'rgba(239, 68, 68, 0.18)',
            bottomFillColor2: 'rgba(239, 68, 68, 0.0)',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
        });

        // 2. Reference Price Line (Dashed Yellow)
        priceSeries.createPriceLine({
            price: refPrice,
            color: '#94a3b8',
            lineWidth: 1,
            lineStyle: 2, // Dashed
            axisLabelVisible: false,
        });

        // 3. Centering Logic (Visible but transparent to force scale)
        const limitSeries = chart.addSeries(LineSeries, {
            color: 'transparent',
            visible: true,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false,
            autoscaleInfoProvider: () => ({
                priceRange: {
                    minValue: refPrice - (Math.max(Math.abs(Math.max(...(data.map(d => d.p).filter(v => v != null)) || [refPrice]) - refPrice), Math.abs(Math.min(...(data.map(d => d.p).filter(v => v != null)) || [refPrice]) - refPrice)) * 1.1 + refPrice * 0.0005),
                    maxValue: refPrice + (Math.max(Math.abs(Math.max(...(data.map(d => d.p).filter(v => v != null)) || [refPrice]) - refPrice), Math.abs(Math.min(...(data.map(d => d.p).filter(v => v != null)) || [refPrice]) - refPrice)) * 1.1 + refPrice * 0.0005),
                },
            }),
        });

        // 5. Data Processing
        const processData = (rawData, valueKey) => {
            const seenTimes = new Set();
            return rawData
                .filter(d => d[valueKey] !== null && d.timestamp)
                .map(d => ({
                    time: d.timestamp,
                    value: d[valueKey],
                }))
                .filter(d => {
                    if (seenTimes.has(d.time)) return false;
                    seenTimes.add(d.time);
                    return true;
                })
                .sort((a, b) => a.time - b.time);
        };

        const chartPoints = processData(data, 'p');
        if (chartPoints.length > 0) {
            priceSeries.setData(chartPoints);

            const prices = chartPoints.map(p => p.value);
            const minP = Math.min(...prices);
            const maxP = Math.max(...prices);
            const diff = Math.max(Math.abs(maxP - refPrice), Math.abs(minP - refPrice));
            const range = Math.max(diff * 1.1, refPrice * 0.0005);

            // Force X-axis range from 9:00 to 15:00
            const times = chartPoints.map(p => p.time);
            const dataStartTime = times[0];
            const sessionDate = new Date(dataStartTime * 1000);
            sessionDate.setHours(9, 0, 0, 0);
            const sessionStartTs = Math.floor(sessionDate.getTime() / 1000);
            sessionDate.setHours(15, 0, 0, 0);
            const sessionEndTs = Math.floor(sessionDate.getTime() / 1000);

            limitSeries.setData([
                { time: sessionStartTs, value: refPrice + range },
                { time: sessionEndTs, value: refPrice - range }
            ]);

            chart.timeScale().setVisibleRange({
                from: sessionStartTs,
                to: sessionEndTs,
            });
        }

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, refPrice, isPositive, height]);

    return (
        <div ref={chartContainerRef} className="w-full relative h-full bg-gradient-to-b from-slate-50 via-white to-slate-100">
            {refPrice ? (
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[11px] font-semibold text-slate-500 pointer-events-none">
                    {refPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
            ) : null}
        </div>
    );
};

export default LightweightChart;
