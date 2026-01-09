"use client";
import { Activity } from 'lucide-react';

export default function UndoModal({ showUndoConfirm, setShowUndoConfirm, confirmUndo }) {
  if (!showUndoConfirm) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-[110] backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl p-8 w-full max-w-sm shadow-2xl border border-blue-100 transform animate-in zoom-in-95">
        <div className="flex items-center gap-4 mb-6">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl"><Activity size={28} /></div>
          <div>
            <h3 className="text-base font-bold text-slate-800 uppercase tracking-tight">Xác nhận Undo</h3>
            <p className="text-[10px] font-bold text-blue-500 uppercase tracking-widest">Hệ thống Information</p>
          </div>
        </div>
        <p className="text-slate-600 text-sm font-medium mb-8 leading-relaxed">
          Anh Zon có chắc chắn muốn <span className="text-blue-600 font-bold underline decoration-2 underline-offset-4">hoàn tác lệnh mua</span> gần nhất?
        </p>
        <div className="flex gap-3">
          <button onClick={() => setShowUndoConfirm(false)} className="flex-1 py-4 bg-slate-50 text-slate-400 font-black rounded-2xl text-xs uppercase hover:bg-slate-100 transition-all">Hủy bỏ</button>
          <button onClick={confirmUndo} className="flex-1 py-3 bg-blue-600 text-white font-black rounded-2xl text-xs uppercase shadow-lg shadow-blue-100 active:scale-95 transition-all">Xác nhận</button>
        </div>
      </div>
    </div>
  );
}