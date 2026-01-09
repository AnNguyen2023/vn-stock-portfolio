"use client";
import React from "react";

export default function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = "Xác nhận",
    confirmColor = "bg-[#2563eb]"
}) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[140] flex items-center justify-center p-4">
            <div className="bg-white rounded-[32px] p-8 w-full max-w-sm shadow-2xl animate-in zoom-in-95 duration-200 border border-slate-100">
                <div className="mb-6">
                    <h3 className="text-lg font-bold text-slate-800 uppercase leading-tight tracking-tight">
                        {title.toUpperCase()}
                    </h3>
                </div>

                <div className="text-base text-[#4b5563] font-medium mb-10 leading-relaxed font-sans">
                    {message.split(' ').map((word, i) =>
                        word.startsWith('hoàn') || word.startsWith('tác') || word.includes('xóa')
                            ? <span key={i} className="text-blue-600 font-bold underline decoration-2 underline-offset-4 mr-1">{word} </span>
                            : word + ' '
                    )}
                </div>

                <div className="flex gap-4">
                    <button
                        onClick={onClose}
                        className="flex-1 py-4 bg-[#f8fafc] text-[#94a3b8] font-medium rounded-2xl text-sm uppercase hover:bg-slate-100 transition-all"
                    >
                        {title === "Thêm mã thành công" ? "Đóng" : "Hủy bỏ"}
                    </button>
                    <button
                        onClick={onConfirm}
                        className={`flex-1 py-4 ${confirmColor} text-white font-medium rounded-2xl text-sm uppercase hover:opacity-90 transition-all shadow-lg active:scale-95`}
                    >
                        {title === "Thêm mã thành công" ? "Tuyệt vời" : confirmText}
                    </button>
                </div>
            </div>
        </div>
    );
}
