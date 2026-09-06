import axiosInstance from '@/api/apiClient';

export async function fetchProjectTiers(projectName) {
  const response = await axiosInstance.get(
    `/tier/${encodeURIComponent(projectName)}`
  );
  return response.data;
}

export async function fetchSectionsAndGroups(projectId) {
  const response = await axiosInstance.get(`/tier/${projectId}/sections`);
  return response.data;
}

export async function exportTierSubset(projectName, filename, tierNames) {
  const response = await axiosInstance.post(
    `/tier/${encodeURIComponent(projectName)}/export`,
    { filename, tier_names: tierNames },
    { responseType: 'blob' }
  );
  return response;
}

export async function createSection(projectId, name) {
  return axiosInstance.post('/tier/sections/create', {
    project_id: projectId,
    name,
  });
}

export async function renameSection(sectionId, newName) {
  return axiosInstance.post('/tier/sections/rename', {
    section_id: sectionId,
    new_name: newName,
  });
}

export async function deleteSection(sectionId) {
  return axiosInstance.post('/tier/sections/delete', { section_id: sectionId });
}

export async function moveTierGroup(tierGroupId, sectionId) {
  return axiosInstance.post('/tier/tier_group/move', {
    tier_group_id: tierGroupId,
    section_id: sectionId,
  });
}
