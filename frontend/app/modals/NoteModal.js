"use client";
import { Book } from 'lucide-react';

export default function NoteModal({ showNoteModal, setShowNoteModal, editingNote, setEditingNote, handleUpdateNote }) {
  if (!showNoteModal) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-[120] backdrop-blur-sm">
      <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl border border-blue-100 animate-in zoom-in-95">
        <div className="flex items-center gap-4 mb-6">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl"><Book size={24} /></div>
          <h3 className="text-lg font-bold text-slate-700 uppercase">Ghi chú đầu tư</h3>
        </div>

        <textarea
          className="w-full p-4 bg-slate-50 border border-slate-100 rounded-2xl text-sm font-medium outline-none focus:ring-4 focus:ring-blue-100 min-h-[120px] resize-none"
          placeholder="Anh Zon viết gì đó cho lệnh này nhé..."
          value={editingNote.content}
          onChange={(e) => setEditingNote({ ...editingNote, content: e.target.value })}
        />

        <div className="flex gap-3 mt-6">
          <button onClick={() => setShowNoteModal(false)} className="flex-1 py-4 bg-slate-100 text-slate-500 font-black rounded-2xl text-xs uppercase">Đóng</button>
          <button onClick={handleUpdateNote} className="flex-1 py-4 bg-blue-600 text-white font-black rounded-2xl text-xs uppercase shadow-lg shadow-blue-100 active:scale-95 transition-all">Lưu ghi chú</button>
        </div>
      </div>
    </div>
  );
}