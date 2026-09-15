import axiosInstance from '@/api/apiClient';

export const getDataGovernance = (projectId) =>
  axiosInstance.get(`/projects/${projectId}/data-governance`);

export const saveDataGovernance = (projectId, payload) =>
  axiosInstance.put(`/projects/${projectId}/data-governance`, payload);
