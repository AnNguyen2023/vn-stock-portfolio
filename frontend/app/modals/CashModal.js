"use client";

export default function CashModal({ 
  showDeposit, showWithdraw, amount, setAmount, description, setDescription, 
  handleAmountChange, handleDeposit, handleWithdraw, closeModals 
}) {
  if (!showDeposit && !showWithdraw) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center p-4 z-[100] backdrop-blur-sm animate-in fade-in duration-300">
      <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl border border-slate-100 transform animate-in zoom-in-95 duration-200">
        <h2 className={`text-xl font-black mb-6 uppercase tracking-tight ${showDeposit ? 'text-emerald-600' : 'text-purple-600'}`}>
          {showDeposit ? 'Nạp tiền vào ví' : 'Rút tiền khỏi ví'}
        </h2>
        <form onSubmit={showDeposit ? handleDeposit : handleWithdraw} className="space-y-6">
          <div>
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-2 block">Số tiền (VND)</label>
            <div className="relative flex items-center">
              <input type="text" required autoFocus className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-2xl font-bold outline-none focus:ring-4 focus:ring-emerald-100 transition-all" value={amount} onChange={handleAmountChange} placeholder="0" />
              <span className="absolute right-4 text-slate-400 font-bold text-xs">VND</span>
            </div>
          </div>
          <div>
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 mb-2 block">Ghi chú giao dịch</label>
            <input type="text" className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-emerald-100" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="..." />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={closeModals} className="flex-1 py-4 bg-slate-100 text-slate-500 font-black rounded-2xl text-xs uppercase tracking-widest hover:bg-slate-200 transition-all">Hủy bỏ</button>
            <button type="submit" className={`flex-1 py-4 text-white font-black rounded-2xl text-xs uppercase tracking-widest shadow-lg active:scale-95 transition-all ${showDeposit ? 'bg-emerald-500 shadow-emerald-100' : 'bg-purple-600 shadow-purple-100'}`}>Xác nhận</button>
          </div>
        </form>
      </div>
    </div>
  );
}