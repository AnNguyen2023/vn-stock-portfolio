"use client";
import { List, PlusCircle, MinusCircle } from 'lucide-react';
import StatusBadge from '../components/StatusBadge'; // 1. Đã import

export default function StockTable({ data, buyForm, setBuyForm, setSellForm, setShowBuy, setShowSell }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden mb-10">
      <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-white">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-50 rounded-lg text-slate-600"><List size={20} /></div>
          <h2 className="text-slate-800 font-bold text-lg uppercase tracking-tight">Danh mục cổ phiếu</h2>
          <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-bold rounded-full">{data?.holdings?.length || 0} mã</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50/50 text-slate-500 text-[13px] uppercase font-bold tracking-[0.12em] border-b border-slate-100">
            <tr>
              <th className="p-4 pl-6">Mã CK</th><th className="p-4 text-right">SL</th><th className="p-4 text-right">Giá TB</th><th className="p-4 text-right">Giá TT</th><th className="p-4 text-right">Giá trị</th><th className="p-4 text-right">Lãi/Lỗ</th><th className="p-4 text-center w-32">Tỷ trọng</th><th className="p-4 text-right">Hôm nay</th><th className="p-4 text-center">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data?.holdings.map((s) => {
              const isProfit = s.profit_loss >= 0;
              const allocation = data.total_stock_value > 0 ? (s.current_value / data.total_stock_value) * 100 : 0;
              return (
                <tr key={s.ticker} className="hover:bg-slate-50/80 transition-colors group">
                  <td className="p-4 pl-6 relative">
                    <div className={`absolute left-0 top-3 bottom-3 w-1.5 rounded-r-full ${isProfit ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                    <div>
                      <div className="font-extrabold text-slate-700 text-sm tracking-tight">{s.ticker}</div>
                      <div className="text-[10px] text-slate-400 font-medium truncate max-w-[120px]">Công ty cổ phần {s.ticker}</div>
                    </div>
                  </td>
                  <td className="p-4 text-right font-bold text-slate-700 text-sm">{s.volume.toLocaleString()}</td>
                  <td className="p-4 text-right text-sm font-medium text-slate-500">{(s.avg_price * 1000).toLocaleString()}</td>
                  <td className="p-4 text-right"><div className={`text-sm font-bold ${isProfit ? 'text-emerald-600' : 'text-rose-500'}`}>{(s.current_price * 1000).toLocaleString()}</div></td>
                  <td className="p-4 text-right text-sm font-bold text-slate-700">{Math.floor(s.current_value).toLocaleString()}</td>
                  
                  {/* CỘT LÃI LỖ: CHỖ ANH ZON VỪA HỎI NÈ */}
                  <td className="p-4 text-right">
                    <div className="flex flex-col items-end">
                        {/* Dòng 1: Tiền lãi tuyệt đối */}
                      <span className={`text-sm font-bold ${isProfit ? 'text-emerald-600' : 'text-rose-500'}`}>
                        {isProfit ? '↗' : '↘'} {Math.abs(Math.floor(s.profit_loss)).toLocaleString()}
                      </span>
                      {/* Dòng 2: Phần trăm dùng StatusBadge */}
                      <StatusBadge value={s.profit_percent.toFixed(2)} showIcon={false} />
                    </div>
                  </td>
                    {/* CỘT TỶ TRỌNG: BIỂU ĐỒ THANH VÀ % */}
                  <td className="p-4 text-center">
                    <div className="bg-slate-100 w-16 h-1.5 rounded-full mx-auto overflow-hidden"><div className="bg-orange-500 h-full transition-all duration-500" style={{ width: `${allocation}%` }}></div></div>
                    <span className="text-[15px] font-medium text-slate-600">{allocation.toFixed(1)}%</span>
                  </td>
                  {/* CỘT HÔM NAY: CŨNG DÙNG STATUS BADGE CHO GỌN */}
                  <td className="p-4 text-right">
                    <StatusBadge value={(Math.random() * 3).toFixed(2)} />
                  </td>

                  <td className="p-4">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => {setBuyForm({...buyForm, ticker: s.ticker}); setShowBuy(true)}} className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg hover:bg-emerald-600 hover:text-white transition-all shadow-sm"><PlusCircle size={18}/></button>
                      <button onClick={() => {setSellForm({ticker: s.ticker, volume: s.volume, price: '', available: s.available}); setShowSell(true)}} className="p-1.5 bg-rose-50 text-rose-500 rounded-lg hover:bg-rose-500 hover:text-white transition-all shadow-sm"><MinusCircle size={18}/></button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="bg-white p-5 flex justify-between items-center border-t border-slate-200">
        <span className="text-slate-600 text-[15px] font-normal ml-2">Tổng giá trị danh mục</span>
        <div className="flex items-baseline gap-1.5 mr-4"><span className="text-xl font-bold text-slate-900 tracking-tight">{Math.floor(data?.total_stock_value || 0).toLocaleString('en-US')}</span><span className="text-base font-semibold text-slate-500 lowercase">vnd</span></div>
      </div>
    </div>
  );
}