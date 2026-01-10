"use client";
import { useState, useEffect, useCallback } from 'react';
import { getPortfolio, getAuditLog, getPerformance, getNavHistory, getHistorySummary } from '@/lib/api';
import { toast } from 'sonner';

export default function useDashboardData() {
    const [data, setData] = useState(null);
    const [logs, setLogs] = useState([]);
    const [perf, setPerf] = useState(null);
    const [loading, setLoading] = useState(true);
    const [navHistory, setNavHistory] = useState([]);
    const [historicalProfit, setHistoricalProfit] = useState(null);
    const [portfolioLastUpdated, setPortfolioLastUpdated] = useState(new Date());

    // Date Filters
    // Date Filters: Mặc định lùi 30 ngày để xem được nhiều dữ liệu hơn
    const [startDate, setStartDate] = useState(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-CA'));
    const [endDate, setEndDate] = useState(new Date().toLocaleDateString('en-CA'));

    const fetchAllData = useCallback(async () => {
        try {
            const resP = await getPortfolio();
            if (resP?.data) {
                setData(resP.data);
                setPortfolioLastUpdated(new Date());
            }

            setLoading(false);

            // Parallel fetch for history data
            Promise.all([
                getAuditLog().then(res => res.data).catch(() => []),
                getPerformance().then(res => res.data).catch(() => null),
                getNavHistory(startDate, endDate).then(res => res.data).catch(() => []),
                getHistorySummary(startDate, endDate).then(res => res.data).catch(() => ({ total_profit: 0, trade_count: 0 }))
            ]).then(([l, p, n, h]) => {
                if (l) setLogs(l);
                if (p) setPerf(p);
                if (n) setNavHistory(n);
                if (h) setHistoricalProfit(h);
            });
        } catch (error) {
            console.error("LỖI KẾT NỐI BACKEND:", error);
            setLoading(false);
        }
    }, [startDate, endDate]);

    useEffect(() => {
        fetchAllData();
        const interval = setInterval(fetchAllData, 10000);
        return () => clearInterval(interval);
    }, [fetchAllData]);

    const handleCalculateProfit = async () => {
        if (!startDate || !endDate) {
            toast.info("Thông tin thiếu", { description: "Vui lòng chọn đầy đủ ngày bắt đầu và kết thúc." });
            return;
        }
        const res = await getHistorySummary(startDate, endDate);
        setHistoricalProfit(res.data);

        // Đồng thời cập nhật luôn bảng NAV History theo khoảng ngày này
        try {
            const resNav = await getNavHistory(startDate, endDate);
            if (resNav?.data) setNavHistory(resNav.data);
        } catch (e) {
            console.error("Lỗi cập nhật NAV History:", e);
        }

        toast.success("Đã cập nhật dữ liệu đối soát.");
    };

    return {
        data, logs, perf, loading, navHistory, historicalProfit, portfolioLastUpdated,
        startDate, setStartDate, endDate, setEndDate,
        fetchAllData, handleCalculateProfit
    };
}
