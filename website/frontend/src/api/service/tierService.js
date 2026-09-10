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

export async function exportTierSubset(
  projectName,
  filename,
  tierNames,
  topicId = null,
  contextTierNames = null,
  editableBaselineTierNames = []
) {
  const response = await axiosInstance.post(
    `/tier/${encodeURIComponent(projectName)}/export`,
    {
      filename,
      tier_names: tierNames,
      topic_id: topicId,
      context_tier_names: contextTierNames,
      editable_baseline_tier_names: editableBaselineTierNames,
    },
    { responseType: 'blob' }
  );
  return response;
}

export async function fetchResearchTopics(projectId) {
  const response = await axiosInstance.get(`/tier/${projectId}/topics`);
  return response.data;
}

export async function fetchProjectBaselineTiers(projectId) {
  const response = await axiosInstance.get(`/tier/${projectId}/baseline-tiers`);
  return response.data;
}

export async function updateProjectBaselineTiers(projectId, tierNames) {
  const response = await axiosInstance.put(
    `/tier/${projectId}/baseline-tiers`,
    {
      tier_names: tierNames,
    }
  );
  return response.data;
}

export async function createResearchTopic(projectId, topic) {
  const response = await axiosInstance.post(`/tier/${projectId}/topics`, topic);
  return response.data;
}

export async function updateResearchTopic(projectId, topicId, topic) {
  const response = await axiosInstance.put(
    `/tier/${projectId}/topics/${topicId}`,
    topic
  );
  return response.data;
}

export async function deleteResearchTopic(projectId, topicId) {
  return axiosInstance.delete(`/tier/${projectId}/topics/${topicId}`);
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
