import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import notificationService from '@/api/service/notificationService';
import { reportClientError } from '@/utils/errorDiagnostics';

export const useNotificationStore = defineStore('notification', () => {
  // State
  const notifications = ref([]);
  const stats = ref({
    total_notifications: 0,
    unread_notifications: 0,
    read_notifications: 0,
  });
  const preferences = ref({
    email_enabled: true,
  });
  const loading = ref(false);
  const error = ref(null);

  // Getters
  const unreadNotifications = computed(() =>
    notifications.value.filter((notification) => !notification.is_read)
  );

  const unreadCount = computed(() => stats.value.unread_notifications || 0);

  const hasUnreadNotifications = computed(() => unreadCount.value > 0);

  // Actions
  const fetchNotifications = async (params = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const data = await notificationService.getNotifications(params);
      notifications.value = data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch notifications';
      reportClientError('Error fetching notifications', err);
    } finally {
      loading.value = false;
    }
  };

  const fetchUnreadNotifications = async (params = {}) => {
    loading.value = true;
    error.value = null;
    try {
      const data = await notificationService.getNotifications({
        ...params,
        unread_only: true,
      });
      // Update existing notifications with unread ones
      const existingIds = new Set(
        notifications.value.map((n) => n.notification_id)
      );
      const newNotifications = data.filter(
        (n) => !existingIds.has(n.notification_id)
      );
      notifications.value = [...notifications.value, ...newNotifications];
    } catch (err) {
      error.value = err.message || 'Failed to fetch unread notifications';
      reportClientError('Error fetching unread notifications', err);
    } finally {
      loading.value = false;
    }
  };

  const fetchNotificationStats = async () => {
    try {
      const data = await notificationService.getNotificationStats();
      stats.value = data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch notification stats';
      reportClientError('Error fetching notification stats', err);
    }
  };

  const markNotificationAsRead = async (notificationId) => {
    try {
      const updatedNotification =
        await notificationService.markNotificationAsRead(notificationId);
      const index = notifications.value.findIndex(
        (n) => n.notification_id === notificationId
      );
      if (index !== -1) {
        notifications.value[index] = updatedNotification;
      }
      // Update stats
      await fetchNotificationStats();
    } catch (err) {
      error.value = err.message || 'Failed to mark notification as read';
      reportClientError('Error marking notification as read', err);
    }
  };

  const markAllNotificationsAsRead = async () => {
    try {
      await notificationService.markAllNotificationsAsRead();
      // Mark all notifications as read in the store
      notifications.value.forEach((notification) => {
        notification.is_read = true;
      });
      // Update stats
      await fetchNotificationStats();
    } catch (err) {
      error.value = err.message || 'Failed to mark all notifications as read';
      reportClientError('Error marking all notifications as read', err);
    }
  };

  const deleteNotification = async (notificationId) => {
    try {
      await notificationService.deleteNotification(notificationId);
      notifications.value = notifications.value.filter(
        (n) => n.notification_id !== notificationId
      );
      // Update stats
      await fetchNotificationStats();
    } catch (err) {
      error.value = err.message || 'Failed to delete notification';
      reportClientError('Error deleting notification', err);
    }
  };

  const fetchNotificationPreferences = async () => {
    try {
      const data = await notificationService.getNotificationPreferences();
      preferences.value = data;
    } catch (err) {
      error.value = err.message || 'Failed to fetch notification preferences';
      reportClientError('Error fetching notification preferences', err);
    }
  };

  const updateNotificationPreferences = async (newPreferences) => {
    try {
      const data =
        await notificationService.updateNotificationPreferences(newPreferences);
      preferences.value = data;
      error.value = null; // Clear any previous errors
    } catch (err) {
      error.value = err.message || 'Failed to update notification preferences';
      reportClientError('Error updating notification preferences', err);
      throw err; // Re-throw to allow component to handle if needed
    }
  };

  return {
    // State
    notifications,
    stats,
    preferences,
    loading,
    error,

    // Getters
    unreadNotifications,
    unreadCount,
    hasUnreadNotifications,

    // Actions
    fetchNotifications,
    fetchUnreadNotifications,
    fetchNotificationStats,
    markNotificationAsRead,
    markAllNotificationsAsRead,
    deleteNotification,
    fetchNotificationPreferences,
    updateNotificationPreferences,
  };
});
