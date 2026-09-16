import axiosInstance from '@api/apiClient.js';

export default {
  async getStandardsByProject(projectId) {
    return axiosInstance.get(`/project-naming-standard/project/${projectId}`);
  },
  async createStandardWithComponents(payload) {
    return axiosInstance.post('/project-naming-standard/create', payload);
  },
  async deleteStandard(standardId) {
    return axiosInstance.delete(`/project-naming-standard/${standardId}`);
  },
  async getProjectNamingStandardsFull(projectId) {
    return axiosInstance.get(
      `/project-naming-standard/project/${projectId}/full`
    );
  },
  async getProjectsWithStandards() {
    return axiosInstance.get(
      '/project-naming-standard/projects-with-standards'
    );
  },
  async importSelectedStandards(payload) {
    return axiosInstance.post('/project-naming-standard/import', payload);
  },
};
