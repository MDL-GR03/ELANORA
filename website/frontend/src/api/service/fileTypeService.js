import axiosInstance from '@api/apiClient.js';

export default {
  async addProjectFileType(projectId, payload) {
    return axiosInstance.post(`/file-type/project/${projectId}/add`, payload);
  },
  async getProjectFileTypes(projectId) {
    return axiosInstance.get(`/file-type/project/${projectId}`);
  },
  async deleteProjectFileType(projectId, fileTypeId) {
    return axiosInstance.delete(
      `/file-type/project/${projectId}/file_type/${fileTypeId}`
    );
  },
  async importSelected(sourceProjectId, targetProjectId, fileTypeNames) {
    return axiosInstance.post(
      `/file-type/import_selected/?source_project_id=${sourceProjectId}&target_project_id=${targetProjectId}`,
      { file_type_names: fileTypeNames }
    );
  },
  async updateProjectFileType(projectId, fileTypeId, payload) {
    return axiosInstance.put(
      `/file-type/project/${projectId}/file_type/${fileTypeId}`,
      payload
    );
  },
};
