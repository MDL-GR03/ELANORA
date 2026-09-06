import apiClient from '../apiClient';

const notificationService = {
  /**
   * Get notifications for the current user
   * @param {Object} params - Query parameters
   * @param {number} params.skip - Number of notifications to skip
   * @param {number} params.limit - Maximum number of notifications to return
   * @param {boolean} params.unread_only - If true, only return unread notifications
   * @returns {Promise} Promise that resolves to the notifications
   */
  async getNotifications(params = {}) {
    const response = await apiClient.get('/notifications/', { params });
    return response.data;
  },

  /**
   * Get notification statistics for the current user
   * @returns {Promise} Promise that resolves to the notification stats
   */
  async getNotificationStats() {
    const response = await apiClient.get('/notifications/stats');
    return response.data;
  },

  /**
   * Create a new notification
   * @param {Object} notificationData - The notification data
   * @param {number} notificationData.user_id - The ID of the user receiving the notification
   * @param {string} notificationData.title - The title of the notification
   * @param {string} notificationData.message - The message content of the notification
   * @param {string} notificationData.action_url - Optional URL for the notification action
   * @returns {Promise} Promise that resolves to the created notification
   */
  async createNotification(notificationData) {
    const response = await apiClient.post('/notifications/', notificationData);
    return response.data;
  },

  /**
   * Mark a notification as read
   * @param {number} notificationId - The ID of the notification to mark as read
   * @returns {Promise} Promise that resolves to the updated notification
   */
  async markNotificationAsRead(notificationId) {
    const response = await apiClient.put(`/notifications/${notificationId}`, {
      is_read: true,
    });
    return response.data;
  },

  /**
   * Delete a notification
   * @param {number} notificationId - The ID of the notification to delete
   * @returns {Promise} Promise that resolves when the notification is deleted
   */
  async deleteNotification(notificationId) {
    await apiClient.delete(`/notifications/${notificationId}`);
  },

  /**
   * Mark all notifications as read for the current user
   * @returns {Promise} Promise that resolves to the result
   */
  async markAllNotificationsAsRead() {
    const response = await apiClient.post('/notifications/mark-all-read');
    return response.data;
  },

  /**
   * Get notification preferences for the current user
   * @returns {Promise} Promise that resolves to the notification preferences
   */
  async getNotificationPreferences() {
    const response = await apiClient.get('/notifications/preferences');
    return response.data;
  },

  /**
   * Update notification preferences for the current user
   * @param {Object} preferences - The notification preferences
   * @param {boolean} preferences.email_enabled - Whether email notifications are enabled
   * @returns {Promise} Promise that resolves to the updated preferences
   */
  async updateNotificationPreferences(preferences) {
    // Ensure email_enabled is a boolean
    const formattedPreferences = {
      email_enabled: Boolean(preferences.email_enabled),
    };

    try {
      const response = await apiClient.put(
        '/notifications/preferences',
        formattedPreferences
      );
      return response.data;
    } catch (error) {
      console.error('Service: Error details:', {
        message: error.message,
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        headers: error.response?.headers,
      });
      throw error;
    }
  },
};

export default notificationService;
