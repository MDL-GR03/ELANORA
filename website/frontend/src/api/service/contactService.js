/**
 * contactService.js
 *
 * API service for contact form functionality.
 * Provides methods for sending contact messages to administrators.
 */

import axiosInstance from '@api/apiClient.js';

/**
 * Send a contact message to administrators
 * @param {Object} contactData - The contact form data
 * @param {string} contactData.email - The sender's email address
 * @param {string} contactData.request_type - The type of request
 * @param {string} contactData.message - The message content
 * @returns {Promise<import('axios').AxiosResponse>}
 */
export const sendContactMessage = async (contactData) => {
  return await axiosInstance.post('/contact/send', contactData);
};

export const contactService = {
  sendContactMessage,
};
