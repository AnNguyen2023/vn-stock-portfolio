"use client";
import { useState } from 'react';
import { depositMoney, withdrawMoney, buyStock, sellStock, undoLastBuy, updateTransactionNote } from '@/lib/api';
import { toast } from 'sonner';

export default function useTradeActions(fetchAllData) {
    // MODALS
    const [showDeposit, setShowDeposit] = useState(false);
    const [showWithdraw, setShowWithdraw] = useState(false);
    const [showBuy, setShowBuy] = useState(false);
    const [showSell, setShowSell] = useState(false);
    const [showUndoConfirm, setShowUndoConfirm] = useState(false);

    // Note Modal
    const [editingNote, setEditingNote] = useState({ id: null, content: "" });
    const [showNoteModal, setShowNoteModal] = useState(false);

    // FORMS
    const [amount, setAmount] = useState("");
    const [description, setDescription] = useState("");

    const [buyForm, setBuyForm] = useState({
        ticker: "",
        volume: "",
        price: "",
        fee_rate: 0.0015,
        note: "",
    });

    const [sellForm, setSellForm] = useState({
        ticker: "",
        volume: "",
        price: "",
        available: 0,
        note: "",
    });

    // ACTIONS
    const closeModals = () => {
        setShowDeposit(false);
        setShowWithdraw(false);
        setShowBuy(false);
        setShowSell(false);

        setAmount("");
        setDescription("");

        setBuyForm({ ticker: "", volume: "", price: "", fee_rate: 0.0015, note: "" });
        setSellForm({ ticker: "", volume: "", price: "", available: 0, note: "" });
    };

    const handleAmountChange = (e) => {
        const rawValue = e.target.value.replace(/[^0-9]/g, "");
        if (!rawValue) {
            setAmount("");
            return;
        }
        setAmount(new Intl.NumberFormat("en-US").format(rawValue));
    };

    const handleVolumeChange = (e, type) => {
        const raw = e.target.value.replace(/[^0-9]/g, "");
        const formatted = raw ? new Intl.NumberFormat("en-US").format(raw) : "";
        if (type === "buy") setBuyForm({ ...buyForm, volume: formatted });
        else setSellForm({ ...sellForm, volume: formatted });
    };

    const handlePriceChange = (e, type) => {
        const val = e.target.value;
        if (/^[\d,.]*$/.test(val)) {
            if (type === "buy") setBuyForm({ ...buyForm, price: val });
            else setSellForm({ ...sellForm, price: val });
        }
    };

    const handlePriceBlur = (type) => {
        const form = type === "buy" ? buyForm : sellForm;
        let valStr = (form.price || "").toString().replace(/,/g, "");
        let val = parseFloat(valStr);
        if (!val) return;
        if (val < 1000) val = val * 1000;
        const formatted = new Intl.NumberFormat("en-US").format(val);
        if (type === "buy") setBuyForm({ ...buyForm, price: formatted });
        else setSellForm({ ...sellForm, price: formatted });
    };

    const handleUndo = () => setShowUndoConfirm(true);

    const confirmUndo = async () => {
        setShowUndoConfirm(false);
        try {
            const res = await undoLastBuy();
            fetchAllData();
            toast.success("Hoàn tác thành công", { description: res.data.message });
        } catch (error) {
            toast.error("Không thể hoàn tác", {
                description: error.response?.data?.detail || "Lỗi hệ thống.",
            });
        }
    };

    const handleDeposit = async (e) => {
        e.preventDefault();
        if (!amount) return;
        try {
            const cleanAmount = parseFloat(amount.replace(/,/g, ""));
            await depositMoney({ amount: cleanAmount, description });
            closeModals();
            fetchAllData();
            toast.success("Nạp tiền thành công", {
                description: `Đã cộng ${amount} VND vào tài khoản.`,
            });
        } catch (error) {
            toast.error("Lỗi nạp tiền", { description: error.response?.data?.detail });
        }
    };

    const handleWithdraw = async (e) => {
        e.preventDefault();
        if (!amount) return;
        try {
            const cleanAmount = parseFloat(amount.replace(/,/g, ""));
            await withdrawMoney({ amount: cleanAmount, description });
            closeModals();
            fetchAllData();
            toast.success("Rút vốn thành công", {
                description: `Đã trừ ${amount} VND khỏi tài khoản.`,
            });
        } catch (error) {
            toast.error("Rút vốn thất bại", {
                description: error.response?.data?.detail || "Vui lòng kiểm tra lại số dư.",
            });
        }
    };

    const handleBuy = async (e) => {
        e.preventDefault();
        try {
            const cleanPrice = parseFloat(buyForm.price.toString().replace(/,/g, ""));
            const cleanVolume = parseInt(buyForm.volume.toString().replace(/,/g, ""), 10);

            await buyStock({ ...buyForm, volume: cleanVolume, price: cleanPrice });
            closeModals();
            fetchAllData();
            toast.success("Khớp lệnh MUA thành công", {
                description: `Mua ${cleanVolume.toLocaleString()} ${buyForm.ticker} giá ${cleanPrice.toLocaleString()}.`,
            });
        } catch (error) {
            toast.error("Lệnh mua bị từ chối", {
                description: error.response?.data?.detail || "Vui lòng kiểm tra số dư tiền mặt.",
            });
        }
    };

    const handleSell = async (e) => {
        e.preventDefault();
        try {
            const cleanPrice = parseFloat(sellForm.price.toString().replace(/,/g, ""));
            const cleanVolume = parseInt(sellForm.volume.toString().replace(/,/g, ""), 10);

            await sellStock({ ...sellForm, volume: cleanVolume, price: cleanPrice });
            closeModals();
            fetchAllData();
            toast.success("Khớp lệnh BÁN thành công", {
                description: `Bán ${cleanVolume.toLocaleString()} ${sellForm.ticker} giá ${cleanPrice.toLocaleString()}.`,
            });
        } catch (error) {
            toast.error("Lệnh bán bị từ chối", {
                description: error.response?.data?.detail || "Không đủ số lượng cổ phiếu.",
            });
        }
    };

    const handleUpdateNote = async () => {
        try {
            await updateTransactionNote(editingNote.id, editingNote.content);
            setShowNoteModal(false);
            fetchAllData();
            toast.success("Đã lưu ghi chú");
        } catch (error) {
            toast.error("Không thể lưu ghi chú");
        }
    };

    return {
        showDeposit, setShowDeposit, showWithdraw, setShowWithdraw,
        showBuy, setShowBuy, showSell, setShowSell, showUndoConfirm, setShowUndoConfirm,
        amount, setAmount, description, setDescription,
        buyForm, setBuyForm, sellForm, setSellForm,
        editingNote, setEditingNote, showNoteModal, setShowNoteModal,
        closeModals, handleAmountChange, handleVolumeChange, handlePriceChange, handlePriceBlur,
        handleUndo, confirmUndo, handleDeposit, handleWithdraw, handleBuy, handleSell, handleUpdateNote
    };
}
