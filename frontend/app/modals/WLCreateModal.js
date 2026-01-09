"use client";
import React, { useState } from "react";

export default function WLCreateModal({ isOpen, onClose, onCreate }) {
    const [name, setName] = useState("");

    if (!isOpen) return null;

    const handleCreate = () => {
        if (!name.trim()) return;
        onCreate(name);
        setName("");
    };

    return (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[130] flex items-center justify-center p-4">
            <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 border border-slate-100">
                <h3 className="text-lg font-bold text-slate-700 uppercase mb-6 tracking-tight">Tạo danh sách mới</h3>
                <div className="relative mb-8">
                    <input
                        type="text"
                        placeholder="Ví dụ: Công nghệ, Ngân hàng..."
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full p-5 bg-[#f8fafc] border-2 border-[#d1fae5] rounded-[24px] text-slate-700 outline-none focus:border-emerald-400 transition-all font-bold placeholder:text-slate-400"
                        autoFocus
                        onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
                    />
                </div>
                <div className="flex gap-4">
                    <button onClick={onClose} className="flex-1 py-4 bg-[#f1f5f9] text-[#94a3b8] font-medium rounded-2xl text-sm uppercase hover:bg-slate-200 transition-all">Hủy</button>
                    <button onClick={handleCreate} className="flex-1 py-4 bg-[#00b894] text-white font-medium rounded-2xl text-sm uppercase hover:bg-[#00a383] transition-all shadow-lg shadow-emerald-100">Tạo ngay</button>
                </div>
            </div>
        </div>
    );
}
