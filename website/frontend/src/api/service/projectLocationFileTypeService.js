import axiosInstance from '@api/apiClient.js';

export default {
  async getFileTypesForLocation(projectId, locationId) {
    return axiosInstance.get(
      `project-location-file-type/project/${projectId}/location/${locationId}/filetypes`
    );
  },
  async addFileTypeToLocation(projectId, locationId, fileTypeId) {
    return axiosInstance.post(
      `project-location-file-type/project/${projectId}/location/${locationId}/filetype/${fileTypeId}/add`
    );
  },
  async removeFileTypeFromLocation(projectId, locationId, fileTypeId) {
    return axiosInstance.delete(
      `project-location-file-type/project/${projectId}/location/${locationId}/filetype/${fileTypeId}/remove`
    );
  },
};
