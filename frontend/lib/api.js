// File: frontend/lib/api.js
import axios from 'axios';
import { toast } from 'sonner';

// 1. Cấu hình địa chỉ Backend
export const API_BASE_URL = 'http://localhost:8000';
const API_URL = API_BASE_URL;

// 2. Cấu hình Interceptor (Người gác cổng)
axios.interceptors.response.use(
    (response) => {
        // Tự động giải nén (unwrap) nếu Backend trả về format { success: true, data: ... }
        if (response.data && typeof response.data === 'object' && response.data.success === true) {
            if (Object.prototype.hasOwnProperty.call(response.data, 'data')) {
                // Ghi đè response.data bằng field data bên trong để giữ tương thích với UI cũ
                response.data = response.data.data;
            }
        }
        return response;
    },
    (error) => {
        // Trường hợp Backend chưa bật hoặc lỗi mạng
        if (!error.response) {
            toast.error('Lỗi kết nối hệ thống', {
                description: 'Máy chủ Backend (Python) đang tắt hoặc lỗi mạng. Vui lòng kiểm tra Terminal.',
            });
        } else {
            // Chuẩn hóa lỗi từ format mới: { success: false, error: { message, detail } }
            const apiError = error.response.data?.error;
            if (apiError) {
                // Gán ngược lại để các component dùng error.response.data.detail vẫn chạy được
                error.response.data.detail = apiError.detail || apiError.message;
            }
        }
        return Promise.reject(error);
    }
);

// --- CÁC HÀM GỌI API ---

// [NEW] Siêu API gộp: Lấy toàn bộ dữ liệu khởi tạo Dashboard trong 1 lần gọi
export const getDashboardInit = async () => {
    return axios.get(`${API_URL}/dashboard-init`);
};

// Lấy thông tin Portfolio (Danh mục, tiền, NAV)
export const getPortfolio = async () => {
    return axios.get(`${API_URL}/portfolio`);
};

// Lấy lịch sử giao dịch tổng hợp (Timeline)
export const getAuditLog = async () => {
    return axios.get(`${API_URL}/logs`);
};

// Lấy hiệu suất tăng trưởng (1D, 1M, 1Y, YTD)
export const getPerformance = async () => {
    return axios.get(`${API_URL}/performance`);
};

// Tra cứu lãi lỗ thực nhận theo khoảng thời gian
export const getHistorySummary = async (startDate, endDate) => {
    return axios.get(`${API_URL}/history-summary`, {
        params: { start_date: startDate, end_date: endDate }
    });
};

// --- API GIAO DỊCH (POST) ---

// Nạp tiền vào vốn đầu tư
export const depositMoney = async (data) => {
    return axios.post(`${API_URL}/deposit`, data);
};

// Rút tiền khỏi tài khoản
export const withdrawMoney = async (data) => {
    return axios.post(`${API_URL}/withdraw`, data);
};

// Khớp lệnh mua cổ phiếu
export const buyStock = async (data) => {
    return axios.post(`${API_URL}/buy`, data);
};

// Khớp lệnh bán cổ phiếu
export const sellStock = async (data) => {
    return axios.post(`${API_URL}/sell`, data);
};

// Đăng ký cổ tức (Tiền, Cổ phiếu, Quyền mua)
export const registerDividend = async (data) => {
    return axios.post(`${API_URL}/register-dividend`, data);
};

export const updateTransactionNote = (id, note) => axios.put(`${API_URL}/logs/${id}/note`, { note });

// --- WATCHLIST API ---
export const getWatchlists = () => axios.get(`${API_URL}/watchlists/`);
export const createWatchlist = (name) => axios.post(`${API_URL}/watchlists/`, { name });
export const deleteWatchlist = (id) => axios.delete(`${API_URL}/watchlists/${id}`);
export const renameWatchlist = (id, name) => axios.put(`${API_URL}/watchlists/${id}`, { name });
export const addTickerToWatchlist = (id, ticker) => axios.post(`${API_URL}/watchlists/${id}/tickers`, { ticker });
export const removeTickerFromWatchlist = (watchlistId, tickerId) => axios.delete(`${API_URL}/watchlists/${watchlistId}/tickers/${tickerId}`);
export const getWatchlistDetail = (id) => axios.get(`${API_URL}/watchlists/${id}/detail`);

// [NEW] Hoàn tác (Undo) lệnh mua gần nhất
export const undoLastBuy = async () => {
    return axios.post(`${API_URL}/undo-last-buy`);
};

// --- API DỮ LIỆU THỊ TRƯỜNG ---

// Lấy dữ liệu lịch sử vẽ biểu đồ (Crawler VPS)
export const getHistoricalData = async (ticker, period = '1m') => {
    try {
        const res = await axios.get(`${API_URL}/historical`, {
            params: { ticker, period }
        });
        return res.data;
    } catch (error) {
        // Lỗi này không làm sập app, chỉ log ra console
        console.error(`Lỗi lấy lịch sử ${ticker}:`, error);
        return null;
    }
};

export const getNavHistory = async (startDate = null, endDate = null, limit = 30) => {
    return axios.get(`${API_URL}/nav-history`, {
        params: {
            start_date: startDate,
            end_date: endDate,
            limit
        }
    });
};
// Chart Growth: lấy series tăng trưởng của DANH MỤC (PORTFOLIO)
export const getChartGrowth = (period = "1m") =>
    axios.get(`${API_URL}/chart-growth`, {
        params: { period },
    });


// API Reset dữ liệu (Dùng khi cần dọn sạch hệ thống)
export const resetData = async () => {
    return axios.post(`${API_URL}/reset-data`);
};
// --- TITAN ADAPTIVE SCANNER API ---
export const getTitanStatus = () => axios.get(`${API_URL}/titan/status`);
export const triggerTitanScan = (settings) => axios.post(`${API_URL}/titan/scan`, settings);
export const stopTitanScan = () => axios.post(`${API_URL}/titan/stop`);
export const getTitanResults = () => axios.get(`${API_URL}/titan/results`);
export const getTitanInspect = (symbol) => axios.get(`${API_URL}/titan/inspect/${symbol}`);

// --- MARKET SUMMARY API ---
export const getMarketSummary = () => axios.get(`${API_URL}/market-summary`);

// Lấy chỉ báo xu hướng 5 phiên của mã chứng khoán
export const getTrending = (ticker) => axios.get(`${API_URL}/trending/${ticker}`);

// [NEW] Lấy dữ giá Live từ VPS (Direct)
export const getVpsLive = (symbols = "") => axios.get(`${API_URL}/vps-live`, { params: { symbols } });

/**
 * Chuẩn hóa phản hồi trending từ API để các component dùng chung.
 * Hỗ trợ cả format mới {success, data} và format cũ/trực tiếp.
 */
export function parseTrendingResponse(res, fallback = { trend: 'sideways', change_pct: 0 }) {
    if (!res) return fallback;

    // Support both full Axios response and the data object itself
    const data = res.data || res;

    // Check if the data has the required fields
    if (data.trend && typeof data.change_pct === 'number') {
        return data;
    }

    // Fallback for raw success/data wrap if interceptor didn't catch it
    if (data.success && data.data) return data.data;
    if (data.success === false) return fallback;

    return (data.trend) ? data : fallback;
}
