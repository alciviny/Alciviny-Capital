/**
 * AlcivinyEdger - Configurações Globais do Frontend
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ENDPOINTS = {
    CATALOG: `${API_BASE_URL}/catalog`,
    INDICATORS_CONFIG: `${API_BASE_URL}/api/config/indicators`,
    DATA: (symbol, timeframe) => `${API_BASE_URL}/data/${symbol}/${timeframe}`,
};
