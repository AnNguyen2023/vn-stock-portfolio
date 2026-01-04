"use client";
import { Eye, EyeOff, PlusCircle, MinusCircle, RefreshCw, RotateCcw } from 'lucide-react';

export default function Header({ 
  isPrivate, setIsPrivate, setShowDeposit, setShowWithdraw, setShowBuy, fetchAllData, handleUndo 
}) {
  return (
    <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-10">
      <div className="flex items-center gap-4">
        <h1 className="text-3xl font-black text-emerald-900 italic tracking-tight">INVEST JOURNAL</h1>
        <button onClick={() => setIsPrivate(!isPrivate)} className="p-2 rounded-full hover:bg-slate-200 text-slate-400 transition-colors">
          {isPrivate ? <EyeOff size={22} /> : <Eye size={22} />}
        </button>
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        <button onClick={() => setShowDeposit(true)} className="bg-emerald-500 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-emerald-600 shadow-md shadow-emerald-100 active:scale-95 transition-all"><PlusCircle size={18}/> Nạp tiền</button>
        <button onClick={() => setShowWithdraw(true)} className="bg-purple-600 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-purple-700 shadow-md shadow-purple-100 active:scale-95 transition-all"><MinusCircle size={18}/> Rút tiền</button>
        <button onClick={() => setShowBuy(true)} className="bg-rose-400 text-white px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 hover:bg-rose-500 shadow-md shadow-rose-100 active:scale-95 transition-all"><PlusCircle size={18}/> Mua mới</button>
        <button onClick={fetchAllData} className="p-2.5 bg-white border border-slate-200 rounded-xl text-slate-400 hover:text-emerald-500 transition-all shadow-sm active:rotate-180 duration-500"><RefreshCw size={20}/></button>
        <button onClick={handleUndo} className="flex items-center gap-2 px-4 py-2.5 bg-white border border-rose-100 rounded-xl text-rose-500 hover:bg-rose-50 transition-all shadow-sm active:scale-95"><RotateCcw size={18} /><span className="font-bold text-xs uppercase tracking-wider">Undo Buy</span></button>
      </div>
    </div>
  );
}