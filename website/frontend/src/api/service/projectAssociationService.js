/**
 * Service for managing project-user associations
 */
import axiosInstance from '@/api/apiClient';

/**
 * Get all users associated with a project by project ID
 * @param {number} projectId - The project ID
 * @returns {Promise} API response with project users
 */
export const getProjectUsers = async (projectId) => {
  try {
    const response = await axiosInstance.get(
      `/project-associations/projects/${projectId}/users`
    );
    return response;
  } catch (error) {
    console.error('Error fetching project users:', error);
    throw error;
  }
};

export const getAvailableProjectUsers = (projectId) =>
  axiosInstance.get(
    `/project-associations/projects/${projectId}/available-users`
  );

/**
 * Add a user to a project with specified permission by project ID
 * @param {number} projectId - The project ID
 * @param {Object} userData - User data with user_id and permission
 * @returns {Promise} API response
 */
export const addUserToProject = async (projectId, userData) => {
  try {
    const response = await axiosInstance.post(
      `/project-associations/projects/${projectId}/users`,
      userData
    );
    return response;
  } catch (error) {
    console.error('Error adding user to project:', error);
    throw error;
  }
};

/**
 * Update a user's permission in a project by project ID
 * @param {number} projectId - The project ID
 * @param {number} userId - The user ID
 * @param {Object} permissionData - Object with permission field
 * @returns {Promise} API response
 */
export const updateUserPermission = async (
  projectId,
  userId,
  permissionData
) => {
  try {
    const response = await axiosInstance.put(
      `/project-associations/projects/${projectId}/users/${userId}`,
      permissionData
    );
    return response;
  } catch (error) {
    console.error('Error updating user permission:', error);
    throw error;
  }
};

/**
 * Remove a user from a project by project ID
 * @param {number} projectId - The project ID
 * @param {number} userId - The user ID
 * @returns {Promise} API response
 */
export const removeUserFromProject = async (projectId, userId) => {
  try {
    const response = await axiosInstance.delete(
      `/project-associations/projects/${projectId}/users/${userId}`
    );
    return response;
  } catch (error) {
    console.error('Error removing user from project:', error);
    throw error;
  }
};

/** Delegate protocol publication and configuration without granting project admin. */
export const grantProtocolManager = (projectId, userId) =>
  axiosInstance.put(`/projects/${projectId}/protocol-managers/${userId}`);

/** Revoke protocol management without changing normal project access. */
export const revokeProtocolManager = (projectId, userId) =>
  axiosInstance.delete(`/projects/${projectId}/protocol-managers/${userId}`);
