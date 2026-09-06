import axiosInstance from '@/api/apiClient';

export const listProtocols = (projectId) =>
  axiosInstance.get(`/projects/${projectId}/protocols`);

export const suggestProtocolFromCorpus = (projectId) =>
  axiosInstance.get(`/projects/${projectId}/protocol-suggestions`);

export const createProtocol = (projectId, payload) =>
  axiosInstance.post(`/projects/${projectId}/protocols`, payload);

export const createProtocolVersion = (projectId, protocolId, payload) =>
  axiosInstance.post(
    `/projects/${projectId}/protocols/${protocolId}/versions`,
    payload
  );

export const updateProtocolDraft = (projectId, versionId, payload) =>
  axiosInstance.put(
    `/projects/${projectId}/protocol-versions/${versionId}`,
    payload
  );

export const deleteProtocolDraft = (projectId, versionId) =>
  axiosInstance.delete(`/projects/${projectId}/protocol-versions/${versionId}`);

export const archiveProtocolVersion = (projectId, versionId, reason = null) =>
  axiosInstance.post(
    `/projects/${projectId}/protocol-versions/${versionId}/archive`,
    { reason }
  );

export const purgeProtocolVersion = (projectId, versionId) =>
  axiosInstance.delete(
    `/projects/${projectId}/protocol-versions/${versionId}/purge`
  );

export const publishProtocolVersion = (projectId, versionId) =>
  axiosInstance.post(
    `/projects/${projectId}/protocol-versions/${versionId}/publish`
  );

export const pinProtocolVersion = (projectId, versionId) =>
  axiosInstance.put(`/projects/${projectId}/protocol-version/${versionId}`);

export const listComplianceScans = (projectId) =>
  axiosInstance.get(`/projects/${projectId}/compliance-scans`);

export const runComplianceScan = (projectId, versionId, preview = true) =>
  axiosInstance.post(
    `/projects/${projectId}/protocol-versions/${versionId}/compliance-scans`,
    null,
    { params: { preview } }
  );
