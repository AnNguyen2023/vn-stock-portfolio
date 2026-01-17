"use client";
import React, { useMemo, useEffect } from 'react';

export default function IntradayChart({ data, referencePrice, height = 110 }) {
    // Debug logging
    useEffect(() => {
        console.log('[IntradayChart] Received props:', {
            dataLength: data?.length,
            dataType: typeof data,
            dataIsArray: Array.isArray(data),
            referencePrice,
            firstItem: data?.[0],
            rawData: data
        });
    }, [data, referencePrice]);

    // 1. Validate inputs
    if (!data || data.length === 0 || !referencePrice) {
        return (
            <div className="flex items-center justify-center w-full h-full bg-slate-50 border border-dashed border-slate-200">
                <div className="text-center px-3">
                    <span className="text-xs text-slate-400 italic block">Chưa có dữ liệu phiên</span>
                    <span className="text-[10px] text-slate-300">Vui lòng đợi hoặc làm mới</span>
                </div>
            </div>
        );
    }

    // 2. Constants & Settings
    const PADDING_TOP = 15;
    const PADDING_BOTTOM = 15;
    const CHART_HEIGHT = height;

    // Transform backend data format {t, p, v} to internal format
    const transformedData = useMemo(() => {
        const transformed = data.map(d => ({
            time: d.t || d.time,
            value: d.p !== undefined ? d.p : d.value,
            volume: d.v !== undefined ? d.v : (d.volume || 0)
        })).filter(d => d.value != null && d.value > 0);

        console.log('[IntradayChart] Transformed:', {
            originalLength: data.length,
            transformedLength: transformed.length,
            sampleOriginal: data[0],
            sampleTransformed: transformed[0]
        });

        return transformed;
    }, [data]);

    if (transformedData.length === 0) {
        console.warn('[IntradayChart] No valid data after transformation. Raw data:', data);
        return (
            <div className="flex items-center justify-center w-full h-full bg-slate-50 border border-dashed border-slate-200">
                <div className="text-center px-3">
                    <span className="text-xs text-slate-400 italic block">Dữ liệu không hợp lệ</span>
                    <span className="text-[10px] text-slate-300">Kiểm tra console để biết chi tiết</span>
                </div>
            </div>
        );
    }

    // Epsilon for "Sideways" (Yellow) detection
    const EPSILON = Math.max(referencePrice * 0.0001, 0.05);

    // 3. Process Data & Scales
    const values = transformedData.map(d => d.value);
    const minPrice = Math.min(...values, referencePrice);
    const maxPrice = Math.max(...values, referencePrice);

    const priceRange = maxPrice - minPrice || 1;
    const yMin = minPrice - priceRange * 0.05;
    const yMax = maxPrice + priceRange * 0.05;
    const yRange = yMax - yMin;

    const getX = (index) => {
        return (index / (transformedData.length - 1)) * 100;
    };

    const getY = (price) => {
        const normalized = (price - yMin) / yRange;
        const availableHeight = CHART_HEIGHT - PADDING_TOP - PADDING_BOTTOM;
        return CHART_HEIGHT - PADDING_BOTTOM - (normalized * availableHeight);
    };

    const yRef = getY(referencePrice);

    // 4. Build Segments - Color based on position relative to reference price
    const segments = useMemo(() => {
        const colorMap = {
            green: '#10b981',  // Above reference
            red: '#ef4444'      // Below reference
        };

        // Determine color based on value vs reference price
        const getColorType = (value) => {
            return value >= referencePrice ? 'green' : 'red';
        };

        if (transformedData.length < 2) return [];

        let pathDefs = [];
        let pendingD = `M ${getX(0)} ${getY(transformedData[0].value)}`;
        let activeColor = getColorType(transformedData[0].value);

        for (let i = 1; i < transformedData.length; i++) {
            const prev = transformedData[i - 1];
            const curr = transformedData[i];

            const x1 = getX(i - 1);
            const y1 = getY(prev.value);
            const x2 = getX(i);
            const y2 = getY(curr.value);

            const color = getColorType(curr.value);

            if (color !== activeColor) {
                pathDefs.push({ color: activeColor, d: pendingD });
                pendingD = `M ${x1} ${y1} L ${x2} ${y2}`;
                activeColor = color;
            } else {
                pendingD += ` L ${x2} ${y2}`;
            }
        }
        pathDefs.push({ color: activeColor, d: pendingD });

        return pathDefs.map((def, idx) => ({
            ...def,
            hex: colorMap[def.color],
            key: idx
        }));
    }, [transformedData, referencePrice, CHART_HEIGHT]);

    // 5. Generate time grid lines (9h - 15h)
    const timeGridLines = useMemo(() => {
        const hours = [9, 10, 11, 12, 13, 14, 15];
        return hours.map(hour => {
            // Assuming 72 points from 9:00-15:00 (6 hours * 12 points/hour)
            // Each hour = 12 points
            const pointsPerHour = transformedData.length / 6;
            const hourIndex = (hour - 9) * pointsPerHour;
            const xPos = (hourIndex / (transformedData.length - 1)) * 100;

            return {
                hour,
                x: xPos,
                label: `${hour}h`
            };
        });
    }, [transformedData.length]);


    return (
        <div className="w-full h-full relative select-none">
            <svg
                width="100%"
                height="100%"
                viewBox={`0 0 100 ${CHART_HEIGHT}`}
                preserveAspectRatio="none"
                className="overflow-visible"
            >
                {/* Time Grid Lines */}
                {timeGridLines.map((grid) => (
                    <line
                        key={grid.hour}
                        x1={grid.x}
                        y1="0"
                        x2={grid.x}
                        y2={CHART_HEIGHT}
                        stroke="#e2e8f0"
                        strokeWidth="0.5"
                        vectorEffect="non-scaling-stroke"
                        opacity="0.5"
                    />
                ))}

                {/* Reference Line */}
                <line
                    x1="0"
                    y1={yRef}
                    x2="100"
                    y2={yRef}
                    stroke="#94a3b8"
                    strokeWidth="1"
                    strokeDasharray="3 2"
                    vectorEffect="non-scaling-stroke"
                />

                {/* Price Segments */}
                {segments.map((seg) => (
                    <path
                        key={seg.key}
                        d={seg.d}
                        stroke={seg.hex}
                        strokeWidth="1.5"
                        fill="none"
                        vectorEffect="non-scaling-stroke"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    />
                ))}
            </svg>

            {/* Reference Label */}
            <div
                className="absolute w-full flex justify-center pointer-events-none"
                style={{ top: `${(yRef / CHART_HEIGHT) * 100}%` }}
            >
                <span className="bg-white/80 px-1 text-[10px] font-medium text-slate-500 rounded backdrop-blur-[1px]">
                    {referencePrice?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
            </div>

            {/* Time Labels */}
            <div className="absolute bottom-0 left-0 right-0 flex justify-between px-1 pointer-events-none">
                {timeGridLines.map((grid) => (
                    <span
                        key={grid.hour}
                        className="text-[10px] text-slate-700 font-semibold"
                        style={{
                            position: 'absolute',
                            left: `${grid.x}%`,
                            transform: 'translateX(-50%)',
                            textShadow: '0 0 3px white, 0 0 3px white'
                        }}
                    >
                        {grid.label}
                    </span>
                ))}
            </div>

        </div>
    );
}
