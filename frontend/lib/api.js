// File: frontend/lib/api.js
import axios from 'axios';

import { toast } from 'sonner'; 

// 1. Khai báo đường dẫn Backend (Sửa lỗi API_URL is not defined)
const API_URL = 'http://localhost:8000';


axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // CHỈ HIỆN TOAST, KHÔNG THROW LỖI LÀM SẬP APP
      toast.error('Máy chủ Backend đang tắt hoặc lỗi mạng!');
    }
    return Promise.reject(error);
  }
);

// ... Các hàm export bên dưới giữ nguyên ...

// Lấy thông tin Portfolio (Danh mục, tiền, NAV)
export const getPortfolio = async () => {
    return axios.get(`${API_URL}/portfolio`);
};

// Lấy lịch sử giao dịch (Audit Log)
export const getAuditLog = async () => {
    return axios.get(`${API_URL}/logs`); // Hoặc endpoint tương ứng bên backend
};

// Lấy hiệu suất (Performance)
export const getPerformance = async () => {
    return axios.get(`${API_URL}/performance`); // Endpoint giả định, check lại backend nếu khác
};

// Tính toán lãi lỗ theo khoảng thời gian
export const getHistorySummary = async (startDate, endDate) => {
    return axios.get(`${API_URL}/history-summary`, { 
        params: { start_date: startDate, end_date: endDate } 
    });
};

// Nạp tiền
export const depositMoney = async (data) => {
    // data = { amount: 100000, description: "..." }
    return axios.post(`${API_URL}/deposit`, data);
};

// Rút tiền
export const withdrawMoney = async (data) => {
    return axios.post(`${API_URL}/withdraw`, data);
};

// Mua cổ phiếu (Sửa lỗi buyStock doesn't exist)
export const buyStock = async (data) => {
    // data = { ticker: 'HPG', volume: 100, price: 20.5 }
    return axios.post(`${API_URL}/buy`, data);
};

// Bán cổ phiếu
export const sellStock = async (data) => {
    return axios.post(`${API_URL}/sell`, data);
};

export const getHistoricalData = async (ticker, period = '1m') => {
  try {
    const res = await axios.get(`${API_URL}/historical`, {
      params: { ticker, period }
    });
    return res.data; 
  } catch (error) {
    // Thay vì console.error, chúng ta bắn thông báo lỗi
    toast.error('Lỗi kết nối bảng giá', { 
      description: `Không thể lấy dữ liệu lịch sử của mã ${ticker}. Vui lòng kiểm tra server.` 
    });
    return null;
  }
};