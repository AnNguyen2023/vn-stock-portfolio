"use client";
import React from "react";
import { ListPlus, Plus, Trash2, Download, Bookmark } from "lucide-react";

export default function WatchlistToolbar({
    onShowCreate,
    onShowAdd,
    onBulkDelete,
    onExport,
    selectedCount
}) {
    return (
        <div className="p-4 border-b border-slate-300 flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-50/30">
            <div className="flex items-center gap-2">
                <Bookmark size={20} className="text-slate-600" />
                <h2 className="text-[17px] font-medium text-slate-600 uppercase tracking-tight">Watchlist Pro</h2>
            </div>


            <div className="flex gap-2 w-full md:w-auto">
                <button
                    onClick={onShowCreate}
                    className="flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 bg-purple-500 text-white rounded-2xl text-xs font-bold uppercase hover:bg-purple-600 transition-all shadow-md shadow-purple-200"
                >
                    <ListPlus size={16} /> Tạo List
                </button>
                <button
                    onClick={onShowAdd}
                    className="flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 bg-white border border-purple-200 text-purple-600 rounded-2xl text-xs font-bold uppercase hover:bg-purple-50 transition-all"
                >
                    <Plus size={16} /> Thêm mã
                </button>
                <button
                    onClick={onBulkDelete}
                    disabled={selectedCount === 0}
                    className={`flex-1 md:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-2xl text-xs font-bold uppercase transition-all shadow-md ${selectedCount > 0
                        ? "bg-rose-400 text-white shadow-rose-200 hover:bg-rose-500"
                        : "bg-slate-50 text-slate-300 border border-slate-100 shadow-none cursor-not-allowed"
                        }`}
                >
                    <Trash2 size={14} /> Xoá Mã {selectedCount > 0 && `(${selectedCount})`}
                </button>
                <button
                    onClick={onExport}
                    className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-3 bg-emerald-500 text-white rounded-2xl text-[10px] font-bold uppercase hover:bg-emerald-600 transition-all shadow-lg shadow-emerald-100"
                >
                    <Download size={14} /> Xuất CSV
                </button>
            </div>
        </div>
    );
}
