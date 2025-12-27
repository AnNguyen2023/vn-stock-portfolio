import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const getPortfolio = () => api.get('/portfolio');
export const depositMoney = (data) => api.post('/deposit', data);
export const buyStock = (data) => api.post('/buy', data);
export const sellStock = (data) => api.post('/sell', data); // Kiểm tra dòng này
export const getHistory = () => api.get('/history');       // VÀ DÒNG NÀY
export const withdrawMoney = (data) => api.post('/withdraw', data);
export const getAuditLog = () => api.get('/audit-log');
export const getHistorySummary = (start, end) => api.get(`/history-summary?start_date=${start}&end_date=${end}`);
export const getPerformance = () => api.get('/performance');
