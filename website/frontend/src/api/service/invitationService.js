/**
 * invitationService.js
 *
 * Provides invitation-related API calls.
 */

import axiosInstance from '@api/apiClient.js';

/**
 * Send an invitation to a specific project by email.
 * @param {Object} invitationData
 * @param {string} invitationData.receiver_email
 * @param {string} invitationData.project_name
 * @param {string} invitationData.message
 * @param {number} invitationData.expires_in_days
 * @param {string} invitationData.project_permission
 * @param {string} invitationData.language
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function sendInvitation(invitationData) {
  return await axiosInstance.post('/invitation/send', invitationData);
}

/**
 * Validate an invitation code.
 * @param {string} invitationCode
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function validateInvitation(invitationCode) {
  return await axiosInstance.get(`/invitation/validate/${invitationCode}`);
}

/**
 * Get invitations sent by the current admin user.
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function getSentInvitations() {
  return await axiosInstance.get('/invitation/sent');
}

/**
 * Get invitations for a specific project.
 * @param {number} projectId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function getProjectInvitations(projectId) {
  return await axiosInstance.get(`/invitation/project/${projectId}`);
}

/**
 * Accept an invitation (for existing users).
 * @param {number} invitationId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function acceptInvitation(invitationId) {
  return await axiosInstance.post(`/invitation/accept/${invitationId}`);
}

/**
 * Reject an invitation (for existing users).
 * @param {number} invitationId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function rejectInvitation(invitationId) {
  return await axiosInstance.post(`/invitation/reject/${invitationId}`);
}

/**
 * Resend an invitation.
 * @param {number} invitationId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function resendInvitation(invitationId) {
  return await axiosInstance.post(`/invitation/resend/${invitationId}`);
}

/**
 * Cancel an invitation.
 * @param {number} invitationId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function cancelInvitation(invitationId) {
  return await axiosInstance.post(`/invitation/cancel/${invitationId}`);
}

/**
 * Get invitation details for decision page.
 * @param {number} invitationId
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export async function getInvitationDetails(invitationId) {
  return await axiosInstance.get(`/invitation/details/${invitationId}`);
}
