"use client";

export default function TradeModal({
  showBuy, showSell, buyForm, setBuyForm, sellForm, setSellForm,
  handleBuy, handleSell, handleVolumeChange, handlePriceChange, handlePriceBlur, closeModals, data
}) {
  if (!showBuy && !showSell) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 flex items-center justify-center p-4 z-[100] backdrop-blur-sm animate-in fade-in duration-300">
      {/* MODAL MUA (Tone Đỏ Rose) */}
      {showBuy && (
        <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl border border-rose-100 transform animate-in zoom-in-95 duration-200">
          <h2 className="text-lg font-bold mb-6 uppercase text-rose-600 tracking-tight">Khớp lệnh Mua</h2>
          <form onSubmit={handleBuy} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Mã Chứng Khoán</label>
              <input type="text" required autoFocus className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-black uppercase outline-none focus:ring-4 focus:ring-rose-100 transition-all" value={buyForm.ticker || ""} onChange={(e) => setBuyForm({ ...buyForm, ticker: e.target.value.replace(/[^a-zA-Z0-9]/g, '').toUpperCase() })} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Khối lượng</label>
                <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-rose-100" value={buyForm.volume || ""} onChange={(e) => handleVolumeChange(e, 'buy')} />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Giá đặt mua</label>
                <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-rose-100" value={buyForm.price || ""} onChange={(e) => handlePriceChange(e, 'buy')} onBlur={() => handlePriceBlur('buy')} />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Ngày mua</label>
              <input type="date" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-rose-100 uppercase" value={buyForm.transaction_date || ""} onChange={(e) => setBuyForm({ ...buyForm, transaction_date: e.target.value })} />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Ghi chú lệnh mua</label>
              <textarea className="w-full p-3 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-medium outline-none focus:ring-4 focus:ring-rose-100 min-h-[80px] resize-none" value={buyForm.note || ""} onChange={(e) => setBuyForm({ ...buyForm, note: e.target.value })} />
            </div>
            {/* Sửa lại phần hiển thị Thành tiền trong Modal Mua */}
            <div className="p-4 bg-rose-50/50 rounded-2xl border border-rose-100 text-xl font-medium text-rose-700 text-center">
              Tạm tính: {(() => {
                // Ép kiểu về String trước khi replace để không bao giờ lỗi
                const vol = parseInt(String(buyForm.volume || '0').replace(/,/g, '')) || 0;
                const prc = parseFloat(String(buyForm.price || '0').replace(/,/g, '')) || 0;
                return (vol * prc * (1 + 0.0015)).toLocaleString('en-US');
              })()} <span className="text-xs">VND</span>
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={closeModals} className="flex-1 py-4 bg-slate-100 text-slate-500 font-medium rounded-2xl text-sm uppercase hover:bg-slate-200">Hủy</button>
              <button type="submit" className="flex-1 py-4 bg-rose-500 text-white font-medium rounded-2xl text-sm uppercase shadow-lg shadow-rose-100 active:scale-95 transition-all">Xác nhận</button>
            </div>
          </form>
        </div>
      )}

      {/* MODAL BÁN (Tone Xanh Emerald) */}
      {showSell && (
        <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl border border-emerald-100 transform animate-in zoom-in-95 duration-200">
          <h2 className="text-lg font-bold mb-6 uppercase text-emerald-600 tracking-tight">Khớp lệnh Bán</h2>
          <form onSubmit={handleSell} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Mã Chứng Khoán</label>
              <input type="text" readOnly className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-black uppercase text-slate-500" value={sellForm.ticker || ""} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">SL bán</label>
                <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-emerald-100" value={sellForm.volume || ""} onChange={(e) => handleVolumeChange(e, 'sell')} />
              </div>
              <div>
                <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Giá bán</label>
                <input type="text" required className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-bold outline-none focus:ring-4 focus:ring-emerald-100" value={sellForm.price || ""} onChange={(e) => handlePriceChange(e, 'sell')} onBlur={() => handlePriceBlur('sell')} />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-600 uppercase tracking-widest ml-1 mb-2 block">Ghi chú lệnh bán</label>
              <textarea className="w-full p-3 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-medium outline-none focus:ring-4 focus:ring-emerald-100 min-h-[80px] resize-none" value={sellForm.note || ""} onChange={(e) => setSellForm({ ...sellForm, note: e.target.value })} />
            </div>
            {/* Sửa lại phần hiển thị Thực nhận trong Modal Bán */}
            <div className="p-4 bg-emerald-50/50 rounded-2xl border border-emerald-100 text-xl font-medium text-emerald-700 text-center">
              Thực nhận: {(() => {
                // Ép kiểu về String trước khi replace để không bao giờ lỗi
                const vol = parseInt(String(sellForm.volume || '0').replace(/,/g, '')) || 0;
                const prc = parseFloat(String(sellForm.price || '0').replace(/,/g, '')) || 0;
                return (vol * prc * (1 - 0.0025)).toLocaleString('en-US');
              })()} <span className="text-xs">VND</span>
            </div>
            <div className="flex gap-3 pt-2">
              <button type="button" onClick={closeModals} className="flex-1 py-4 bg-slate-100 text-slate-500 font-medium rounded-2xl text-sm uppercase hover:bg-slate-200">Hủy</button>
              <button type="submit" className="flex-1 py-4 bg-emerald-500 text-white font-medium rounded-2xl text-sm uppercase shadow-lg shadow-emerald-100 active:scale-95 transition-all">Xác Nhận</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}