import axios from 'axios';
import type { SearchResponse } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchApi = {
  search: async (query: string, page: number = 1, size: number = 10): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/search', {
      params: { q: query, page, size },
    });
    return response.data;
  },
};
