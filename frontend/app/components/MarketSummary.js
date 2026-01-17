"use client";
import React, { useState, useEffect } from 'react';
import { BarChart3, RefreshCw, Activity } from 'lucide-react';
import { getIndexWidgetData } from '../../lib/api';
import VnindexWidget from './VnindexWidget';
import LiveTicker from './LiveTicker';

export default function MarketSummary() {
    const [vnindex, setVnindex] = useState(null);
    const [vn30, setVn30] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [viRes, v30Res] = await Promise.all([
                getIndexWidgetData("VNINDEX"),
                getIndexWidgetData("VN30")
            ]);

            if (viRes.data) setVnindex(viRes.data);
            if (v30Res.data) setVn30(v30Res.data);
        } catch (error) {
            console.error('Error fetching market summary:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 30000); // 30s refresh
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-300 p-3 mb-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-3 gap-4">
                <div className="flex items-center gap-3 whitespace-nowrap">
                    <BarChart3 size={18} className="text-slate-600" />
                    <h3 className="text-[17px] font-medium text-slate-600 uppercase tracking-tight">Thông tin Thị trường</h3>
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

            {loading && !vnindex ? (
                <div className="flex items-center justify-center h-48 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                    <Activity size={24} className="text-slate-300 animate-pulse" />
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <VnindexWidget
                        symbol="VNINDEX"
                        data={vnindex?.series_points}
                        sessionInfo={vnindex?.session_info}
                        refLevel={vnindex?.ref_level}
                    />
                    <VnindexWidget
                        symbol="VN30"
                        data={vn30?.series_points}
                        sessionInfo={vn30?.session_info}
                        refLevel={vn30?.ref_level}
                    />
                </div>
            )}
        </div>
    );
}
