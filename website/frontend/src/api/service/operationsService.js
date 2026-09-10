import axiosInstance from '@/api/apiClient';

const operationsService = {
  async getStatus() {
    const { data } = await axiosInstance.get('/operations/status');
    return data;
  },
  async checkStorage() {
    const { data } = await axiosInstance.post('/operations/storage-check');
    return data;
  },
};

export default operationsService;
