import axiosInstance from '@/api/apiClient';

const instanceService = {
  // Fetch this installation's single institution profile.
  async getInstanceInfo() {
    const { data } = await axiosInstance.get('/instance/info');
    return data;
  },
  async updateBranding(payload) {
    const { data } = await axiosInstance.patch('/instance/branding', payload);
    return data;
  },
  async uploadLogo(file) {
    const form = new FormData();
    form.append('logo', file);
    await axiosInstance.put('/instance/logo', form);
  },
};

export default instanceService;
