"use client";
import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, BaselineSeries, HistogramSeries } from 'lightweight-charts';

const LightweightChart = ({
    data,
    refPrice,
    isPositive,
    ticker,
    height = 120,
    colors = {
        backgroundColor: 'transparent',
        lineColor: isPositive ? '#10b981' : '#ef4444',
        textColor: '#64748b',
        areaTopColor: isPositive ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
        areaBottomColor: 'rgba(255, 255, 255, 0)',
    }
}) => {
    const chartContainerRef = useRef();

    useEffect(() => {
        if (!chartContainerRef.current || !data || data.length === 0) return;

        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: colors.backgroundColor },
                textColor: colors.textColor,
                fontSize: 11,
                fontFamily: 'Inter, sans-serif',
                attributionLogo: false,
            },
            grid: {
                vertLines: { color: 'rgba(148, 163, 184, 0.18)', style: 0, visible: true }, // Reduced by 40% (0.3 -> 0.18)
                horzLines: { visible: false },
            },
            width: chartContainerRef.current.clientWidth,
            height: height,
            timeScale: {
                visible: true,
                borderVisible: false,
                secondsVisible: false,
                timeVisible: true,
                barSpacing: 1.8, // Even tighter to force ~50% more vertical lines (aiming for highly dense grid)
                minBarSpacing: 0.5,
            },
            rightPriceScale: {
                visible: false,
                borderVisible: false,
            },
            localization: {
                locale: 'vi-VN',
            },
            crosshair: {
                vertLine: {
                    color: '#0f172a',
                    width: 1,
                    style: 0, // Solid for better visibility
                    labelVisible: false,
                },
                horzLine: {
                    color: '#0f172a',
                    width: 1,
                    style: 0, // Solid
                    labelVisible: false,
                },
                mode: 0,
            },
            handleScroll: false,
            handleScale: false,
            watermark: {
                visible: false,
            },
        });

        // Use Baseline series for Green/Red split relative to refPrice (v5 API)
        const areaSeries = chart.addSeries(BaselineSeries, {
            baseValue: { type: 'price', price: refPrice },
            topLineColor: '#10b981',
            topFillColor1: 'rgba(16, 185, 129, 0.15)', // Reduced by 40% (0.25 -> 0.15)
            topFillColor2: 'rgba(16, 185, 129, 0.0)',
            bottomLineColor: '#ef4444',
            bottomFillColor1: 'rgba(239, 68, 68, 0.15)', // Reduced by 40% (0.25 -> 0.15)
            bottomFillColor2: 'rgba(239, 68, 68, 0.0)',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: true,
        });


        // Main Reference Price Line (Solid & Lightened further)
        areaSeries.createPriceLine({
            price: refPrice,
            color: 'rgba(15, 23, 42, 0.44)', // Reduced another 20% (from 0.55)
            lineWidth: 2,
            lineStyle: 0, // Solid
            axisLabelVisible: false,
            title: '',
        });

        // Reduced Auxiliary Grid Lines (-40% density: only +/- 1%)
        const auxOffsets = [0.01, -0.01];
        auxOffsets.forEach(offset => {
            areaSeries.createPriceLine({
                price: refPrice * (1 + offset),
                color: 'rgba(255, 140, 0, 0.4)', // Distinct Orange, slightly higher opacity for visibility
                lineWidth: 1,
                lineStyle: 2, // Dashed for better "interrupted" look
                axisLabelVisible: false,
                title: '',
            });
        });

        // Add volume histogram (v5 API)
        const volumeSeries = chart.addSeries(HistogramSeries, {
            color: '#64748b33',
            priceFormat: { type: 'volume' },
            priceScaleId: '', // overlay
            priceLineVisible: false,
            lastValueVisible: false,
        });

        volumeSeries.priceScale().applyOptions({
            scaleMargins: {
                top: 0.8, // volume at the bottom
                bottom: 0,
            },
        });

        // Prepare data with deduplication and sorting (safeguard for lightweight-charts)
        const processData = (rawData, valueKey) => {
            const seenTimes = new Set();
            return rawData
                .filter(d => d[valueKey] !== null && d.timestamp)
                .map(d => ({
                    time: d.timestamp,
                    value: d[valueKey],
                    color: valueKey === 'v' ? '#64748b22' : undefined
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

        if (chartPoints.length > 0) areaSeries.setData(chartPoints);
        if (volumePoints.length > 0) volumeSeries.setData(volumePoints);

        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [data, refPrice, colors, height]);

    return (
        <div ref={chartContainerRef} className="w-full relative h-full" />
    );
};

export default LightweightChart;
