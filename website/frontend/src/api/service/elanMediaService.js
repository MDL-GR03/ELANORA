import apiClient from '@/api/apiClient';

const elanMediaService = {
  /**
   * Get project files with their associated media for rename suggestions
   */
  async getProjectFilesWithMedia(projectId) {
    const response = await apiClient.get(
      `/elan-file-media/projects/${projectId}/files-with-media`
    );
    return response.data;
  },
};

export default elanMediaService;
