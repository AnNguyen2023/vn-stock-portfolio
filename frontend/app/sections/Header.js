"use client";
import { useEffect } from "react";
import { Eye, EyeOff, PlusCircle, MinusCircle, RefreshCw, RotateCcw } from 'lucide-react';

export default function Header({
  isPrivate, setIsPrivate, setShowDeposit, setShowWithdraw, setShowBuy, setShowSell, fetchAllData, handleUndo
}) {
  // Auto-hide private mode after 15 seconds of being visible
  useEffect(() => {
    if (!isPrivate) {
      const timer = setTimeout(() => setIsPrivate(true), 15000);
      return () => clearTimeout(timer);
    }
  }, [isPrivate, setIsPrivate]);

  return (
    <div className="flex flex-col gap-1 mb-3">
      <div className="flex items-center relative gap-4">
        <h1 className="flex items-center gap-3 text-4xl font-black italic tracking-tighter select-none antialiased">
          <span className="bg-clip-text text-transparent bg-gradient-to-t from-indigo-950 via-purple-600 to-emerald-500 drop-shadow-[0_2px_15px_rgba(147,51,234,0.3)]">INVEST</span>
          <button
            onClick={() => setIsPrivate(!isPrivate)}
            className="text-slate-200 hover:text-slate-400 transition-colors p-1"
            title={isPrivate ? "Hiện thông tin" : "Che thông tin"}
          >
            {isPrivate ? <EyeOff size={20} /> : <Eye size={20} />}
          </button>
          <span className="bg-clip-text text-transparent bg-gradient-to-t from-indigo-950 via-purple-600 to-emerald-500 drop-shadow-[0_2px_15px_rgba(147,51,234,0.3)]">JOURNAL</span>
        </h1>
      </div>

      <div className="flex flex-wrap justify-end gap-3 w-full">
        <button onClick={() => setShowDeposit(true)} className="bg-emerald-500 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-emerald-600 shadow-md shadow-emerald-100 active:scale-95 transition-all"><PlusCircle size={18} /> Nạp tiền</button>
        <button onClick={() => setShowWithdraw(true)} className="bg-purple-500 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-purple-600 shadow-md shadow-purple-100 active:scale-95 transition-all"><MinusCircle size={18} /> Rút tiền</button>
        <button onClick={() => setShowBuy(true)} className="bg-rose-400 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-rose-500 shadow-md shadow-rose-100 active:scale-95 transition-all"><PlusCircle size={18} /> Mua</button>
        <button onClick={() => setShowSell(true)} className="bg-purple-500 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-purple-600 shadow-md shadow-purple-100 active:scale-95 transition-all"><MinusCircle size={18} /> Bán</button>
        <button onClick={handleUndo} className="flex items-center gap-2 px-4 py-2.5 bg-white border border-rose-100 rounded-xl text-rose-500 hover:bg-rose-50 transition-all shadow-sm active:scale-95"><RotateCcw size={18} /><span className="font-bold text-xs uppercase tracking-wider">Undo Buy</span></button>
      </div>
    </div>
  );
}