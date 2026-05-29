import axios from 'axios';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

// Attach API key to every request if configured
const API_KEY = import.meta.env.VITE_API_KEY;
if (API_KEY) {
  API.defaults.headers.common['X-API-Key'] = API_KEY;
}

// Dashboard
export const fetchKPIs            = ()         => API.get('/api/dashboard/kpis');
export const fetchMonthlyTrend    = ()         => API.get('/api/dashboard/monthly-trend');
export const fetchDistrictHeatmap = ()         => API.get('/api/dashboard/district-heatmap');
export const fetchFraudTypes      = ()         => API.get('/api/dashboard/fraud-type-breakdown');

// Dealers
export const searchDealers        = (q)        => API.get('/api/dealers/search', { params: { q } });
export const fetchDealers         = (params)   => API.get('/api/dealers', { params });
export const fetchDealer          = (id)       => API.get(`/api/dealers/${id}`);
export const fetchDealerStats     = (id)       => API.get(`/api/dealers/${id}/stats`);

// Transactions
export const fetchTransactions    = (params)   => API.get('/api/transactions', { params });
export const fetchHighRiskTxns    = ()         => API.get('/api/transactions/high-risk/list');
export const fetchSHAP            = (txnId)    => API.get(`/api/transactions/${txnId}/shap`);

// Farmers
export const fetchFarmers         = (params)   => API.get('/api/farmers', { params });
export const fetchFarmer          = (id)       => API.get(`/api/farmers/${id}`);
export const fetchFarmerDistricts = ()         => API.get('/api/farmers/districts');
export const fetchFarmerCrops     = ()         => API.get('/api/farmers/crops');

// Investigations
export const fetchAlerts          = ()         => API.get('/api/investigations/alerts/high-risk');
export const fetchInvestigations  = (params)   => API.get('/api/investigations', { params });
export const updateInvestigation  = (data)     => API.post('/api/investigations/update', data);
export const fetchAuditLogs       = (params)   => API.get('/api/investigations/logs', { params });

// Upload
export const uploadCSV            = (formData) => API.post('/api/upload/csv', formData);
export const triggerRetrain       = ()         => API.post('/api/upload/retrain');
export const fetchUploadLogs      = ()         => API.get('/api/upload/logs');

// Health
export const fetchHealth          = ()         => API.get('/healthz');

export default API;
