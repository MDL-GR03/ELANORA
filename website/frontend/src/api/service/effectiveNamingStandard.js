import axiosInstance from '@api/apiClient.js';

export default {
  async getEffectiveStandardsLocations() {
    return axiosInstance.get('/effective-naming-standard/locations');
  },
  async getEffectiveStandards(projectId, locationId) {
    return axiosInstance.get(
      `/effective-naming-standard/project/${projectId}/location/${locationId}/effective-standards`
    );
  },
  async assignEffectiveStandard(
    projectId,
    projectFileTypeId,
    namingStandardId,
    locationId
  ) {
    return axiosInstance.post(
      `/effective-naming-standard/project/${projectId}/filetype/${projectFileTypeId}/assign`,
      { naming_standard_id: namingStandardId, location_id: locationId }
    );
  },
  async unassignEffectiveStandard(projectId, projectFileTypeId, locationId) {
    return axiosInstance.delete(
      `/effective-naming-standard/project/${projectId}/filetype/${projectFileTypeId}/location/${locationId}/unassign`
    );
  },
};
