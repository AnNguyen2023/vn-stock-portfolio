"use client";
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, BaselineSeries, HistogramSeries, LineSeries } from 'lightweight-charts';

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
                vertLines: { color: 'rgba(148, 163, 184, 0.1)', visible: true },
                horzLines: { color: 'rgba(148, 163, 184, 0.1)', visible: true },
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            timeScale: {
                visible: true,
                borderVisible: false,
                secondsVisible: false,
                timeVisible: true,
                barSpacing: 2,
            },
            rightPriceScale: {
                visible: true,
                borderVisible: false,
                scaleMargins: {
                    top: 0.15,
                    bottom: 0.25,
                },
            },
            handleScroll: false,
            handleScale: false,
        });

        // 1. Baseline Series - Green above ref, Red below ref
        const areaSeries = chart.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: refPrice },
            topLineColor: '#10b981',        // Green for prices ABOVE reference
            topFillColor1: 'rgba(16, 185, 129, 0.15)',
            topFillColor2: 'rgba(16, 185, 129, 0.0)',
            bottomLineColor: '#ef4444',     // Red for prices BELOW reference
            bottomFillColor1: 'rgba(239, 68, 68, 0.15)',
            bottomFillColor2: 'rgba(239, 68, 68, 0.0)',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
        });

        // 2. Reference Price Line (Dashed Yellow)
        areaSeries.createPriceLine({
            price: refPrice,
            color: '#eab308',
            lineWidth: 2,
            lineStyle: 2, // Dashed
            axisLabelVisible: true,
            title: `${refPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
        });

        // 3. Volume Histogram
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#64748b5c',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
            priceLineVisible: false,
            lastValueVisible: false,
        });

        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8,
                bottom: 0,
            },
        });

        // 4. Centering Logic
        const limitSeries = chart.addSeries(LineSeries, {
            color: 'transparent',
            visible: false,
            lastValueVisible: false,
            priceLineVisible: false,
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
        const volumePoints = processData(data, 'v');

        if (chartPoints.length > 0) {
            areaSeries.setData(chartPoints);

            const prices = chartPoints.map(p => p.value);
            const minP = Math.min(...prices);
            const maxP = Math.max(...prices);
            const diff = Math.max(Math.abs(maxP - refPrice), Math.abs(minP - refPrice));
            const range = Math.max(diff * 1.1, refPrice * 0.0005);

            const times = chartPoints.map(p => p.time);
            const startTime = times[0];
            const endTime = times.length > 1 ? times[times.length - 1] : startTime + 60;

            limitSeries.setData([
                { time: startTime, value: refPrice + range },
                { time: endTime, value: refPrice - range }
            ]);
        }

        if (volumePoints.length > 0) volumeSeries.setData(volumePoints);

        chart.timeScale().fitContent();
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, refPrice, isPositive, height]);

    return (
        <div ref={chartContainerRef} className="w-full relative h-full" />
    );
};

export default LightweightChart;
