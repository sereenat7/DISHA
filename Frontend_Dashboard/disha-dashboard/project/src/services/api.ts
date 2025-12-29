import axios from 'axios';
import { TriggerDisasterRequest, NewsResponse } from '../types';

const API_BASE_URL = 'https://disha-9gu7.onrender.com';

export const api = {
  triggerDisaster: async (data: TriggerDisasterRequest) => {
    const response = await axios.post(`${API_BASE_URL}/disaster/trigger`, data, {
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return response.data;
  },

  getDisasterNews: async (): Promise<NewsResponse> => {
    const response = await axios.get(`${API_BASE_URL}/news/disasters`);
    return response.data;
  },
};
