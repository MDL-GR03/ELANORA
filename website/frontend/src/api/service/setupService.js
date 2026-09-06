import axiosInstance from '@/api/apiClient';

const setupService = {
  async getStatus() {
    const { data } = await axiosInstance.get('/setup/status');
    return data;
  },

  async initialize(payload, setupToken) {
    const { data } = await axiosInstance.post('/setup/initialize', payload, {
      headers: { 'X-ELANORA-Setup-Token': setupToken },
    });
    return data;
  },
};

export default setupService;
