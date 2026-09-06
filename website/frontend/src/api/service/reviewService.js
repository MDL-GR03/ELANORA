import axiosInstance from '@/api/apiClient';

const reviewService = {
  async list(projectId, uploadId = null) {
    const { data } = await axiosInstance.get(
      `/review/projects/${encodeURIComponent(projectId)}/cases`,
      { params: uploadId == null ? {} : { upload_id: uploadId } }
    );
    return data;
  },

  async create(projectId, reviewCase) {
    const { data } = await axiosInstance.post(
      `/review/projects/${encodeURIComponent(projectId)}/cases`,
      reviewCase
    );
    return data;
  },

  async comment(projectId, caseId, body) {
    const { data } = await axiosInstance.post(
      `/review/projects/${encodeURIComponent(projectId)}/cases/${encodeURIComponent(caseId)}/comments`,
      { body }
    );
    return data;
  },

  async transition(projectId, caseId, state, changes = {}) {
    const { data } = await axiosInstance.patch(
      `/review/projects/${encodeURIComponent(projectId)}/cases/${encodeURIComponent(caseId)}`,
      { state, ...changes }
    );
    return data;
  },

  async resubmit(projectId, caseId, uploadId) {
    const { data } = await axiosInstance.post(
      `/review/projects/${encodeURIComponent(projectId)}/cases/${encodeURIComponent(caseId)}/resubmission`,
      { upload_id: uploadId }
    );
    return data;
  },
};

export default reviewService;
