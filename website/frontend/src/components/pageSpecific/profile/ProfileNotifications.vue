<template>
  <div class="profile-overview">
    <!-- Notifications Card -->
    <div class="profile-card notifications-main-card">
      <div class="profile-card-header">
        <div class="card-title-section">
          <div class="card-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M13.73 21a2 2 0 0 1-3.46 0"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
          <h3>{{ t('profile.notifications.title') }}</h3>
        </div>
        <div class="notifications-actions">
          <button
            v-if="unreadCount > 0"
            class="action-button mark-all-btn"
            :disabled="loading"
            @click="markAllAsRead"
          >
            <svg
              v-if="!loading"
              class="action-icon"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M20 6L9 17L4 12"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <div v-else class="action-spinner"></div>
            {{
              loading
                ? t('common.loading')
                : t('profile.notifications.mark_all_read')
            }}
          </button>
          <button
            class="action-button refresh-btn"
            :disabled="loading"
            @click="refreshNotifications"
          >
            <svg
              class="action-icon"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M1 4v6h6"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
              <path
                d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            {{ t('profile.notifications.refresh') }}
          </button>
        </div>
      </div>
      <div class="profile-card-content">
        <!-- Statistics Section -->
        <div class="notifications-stats">
          <div class="stat-item">
            <div class="stat-icon total">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  d="M13.73 21a2 2 0 0 1-3.46 0"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-label">{{
                t('profile.notifications.stats.total')
              }}</span>
              <span class="stat-value">{{ stats.total_notifications }}</span>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon unread">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="2"
                />
                <path
                  d="M12 6v6l4 2"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-label">{{
                t('profile.notifications.stats.unread')
              }}</span>
              <span class="stat-value unread-count">{{
                stats.unread_notifications
              }}</span>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon read">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M20 6L9 17L4 12"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <div class="stat-content">
              <span class="stat-label">{{
                t('profile.notifications.stats.read')
              }}</span>
              <span class="stat-value read-count">{{
                stats.read_notifications
              }}</span>
            </div>
          </div>
        </div>

        <!-- Filter Tabs -->
        <div class="notifications-filters">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            class="filter-tab"
            :class="{ active: currentFilter === tab.key }"
            @click="currentFilter = tab.key"
          >
            {{ tab.label }}
            <span
              v-if="tab.count !== undefined"
              class="filter-count"
              :class="{ active: currentFilter === tab.key }"
            >
              {{ tab.count }}
            </span>
          </button>
        </div>

        <!-- Notifications List Container -->
        <div class="notifications-container">
          <!-- Loading State -->
          <div
            v-if="loading && notifications.length === 0"
            class="loading-state"
          >
            <div class="loading-spinner"></div>
            <p class="loading-text">{{ t('profile.notifications.loading') }}</p>
          </div>

          <!-- Empty State -->
          <div
            v-else-if="filteredNotifications.length === 0"
            class="empty-state"
          >
            <div class="empty-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <path
                  d="M13.73 21a2 2 0 0 1-3.46 0"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
            </div>
            <h3 class="empty-title">
              {{ t('profile.notifications.empty.title') }}
            </h3>
            <p class="empty-description">
              {{
                currentFilter === 'unread'
                  ? t('profile.notifications.empty.unread')
                  : t('profile.notifications.empty.all')
              }}
            </p>
          </div>

          <!-- Notifications Items -->
          <div v-else class="notifications-list">
            <div
              v-for="notification in filteredNotifications"
              :key="notification.notification_id"
              class="notification-item"
              :class="{ unread: !notification.is_read }"
              @click="handleNotificationClick(notification)"
            >
              <div class="notification-content">
                <div class="notification-header">
                  <h4 class="notification-title">{{ notification.title }}</h4>
                  <div class="notification-meta">
                    <span v-if="!notification.is_read" class="unread-badge">{{
                      t('profile.notifications.new')
                    }}</span>
                    <span class="notification-date">{{
                      formatDate(notification.created_at)
                    }}</span>
                  </div>
                </div>
                <p class="notification-message">{{ notification.message }}</p>
              </div>

              <div class="notification-actions" @click.stop>
                <button
                  v-if="notification.action_url"
                  class="notification-action-btn view-btn"
                  :title="t('profile.notifications.view')"
                  @click="handleNotificationAction(notification)"
                >
                  <svg
                    class="action-btn-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <circle
                      cx="12"
                      cy="12"
                      r="3"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  {{ t('profile.notifications.view') }}
                </button>
                <button
                  v-if="!notification.is_read"
                  class="notification-action-btn read-btn"
                  :title="t('profile.notifications.mark_read')"
                  @click="markAsRead(notification.notification_id)"
                >
                  <svg
                    class="action-btn-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M20 6L9 17L4 12"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  {{ t('profile.notifications.mark_read') }}
                </button>
                <button
                  class="notification-action-btn delete-btn"
                  :title="t('profile.notifications.delete')"
                  @click="deleteNotification(notification.notification_id)"
                >
                  <svg
                    class="action-btn-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M3 6h18"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                    <path
                      d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6m3 0V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  {{ t('profile.notifications.delete') }}
                </button>
              </div>
            </div>
          </div>

          <!-- Load More Button -->
          <div v-if="hasMoreNotifications" class="load-more-container">
            <button
              class="load-more-btn"
              :disabled="loading"
              @click="loadMoreNotifications"
            >
              <svg
                v-if="!loading"
                class="load-more-icon"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              <div v-else class="load-more-spinner"></div>
              {{
                loading
                  ? t('common.loading')
                  : t('profile.notifications.load_more')
              }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Preferences Card -->
    <div class="profile-card preferences-card">
      <div class="profile-card-header">
        <div class="card-title-section">
          <div class="card-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                cx="12"
                cy="12"
                r="3"
                stroke="currentColor"
                stroke-width="2"
              />
              <path
                d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
                stroke="currentColor"
                stroke-width="2"
              />
            </svg>
          </div>
          <h3>{{ t('profile.notifications.preferences.title') }}</h3>
        </div>
      </div>
      <div class="profile-card-content">
        <div class="profile-field-group">
          <div class="preference-item">
            <div class="preference-content">
              <div class="preference-info">
                <span class="preference-label">{{
                  t('profile.notifications.preferences.email')
                }}</span>
                <span class="preference-description">{{
                  t('profile.notifications.preferences.email_description')
                }}</span>
              </div>
              <div class="preference-control">
                <div class="toggle-switch" @click="toggleEmailPreference">
                  <input
                    id="email-notifications-toggle"
                    v-model="preferences.email_enabled"
                    type="checkbox"
                    class="toggle-input"
                    @change="updatePreferences"
                  />
                  <span class="toggle-slider"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotificationStore } from '@/stores/notification';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
import { reportClientError } from '@/utils/errorDiagnostics';

const { t } = useI18n();
const router = useRouter();
const notificationStore = useNotificationStore();

// Local state
const currentFilter = ref('all');
const currentPage = ref(0);
const pageSize = 20;

// Computed properties
const notifications = computed(() => notificationStore.notifications);
const stats = computed(() => notificationStore.stats);
const preferences = computed(() => notificationStore.preferences);
const loading = computed(() => notificationStore.loading);
const unreadCount = computed(() => notificationStore.unreadCount);

const filterTabs = computed(() => [
  {
    key: 'all',
    label: t('profile.notifications.filters.all'),
    count: stats.value.total_notifications,
  },
  {
    key: 'unread',
    label: t('profile.notifications.filters.unread'),
    count: stats.value.unread_notifications,
  },
  {
    key: 'read',
    label: t('profile.notifications.filters.read'),
    count: stats.value.read_notifications,
  },
]);

const filteredNotifications = computed(() => {
  if (currentFilter.value === 'unread') {
    return notifications.value.filter((n) => !n.is_read);
  }
  if (currentFilter.value === 'read') {
    return notifications.value.filter((n) => n.is_read);
  }
  return notifications.value;
});

const hasMoreNotifications = computed(() => {
  const currentCount = notifications.value.length;
  return (
    currentCount > 0 &&
    currentCount % pageSize === 0 &&
    currentCount < stats.value.total_notifications
  );
});

// Methods
const refreshNotifications = async () => {
  currentPage.value = 0;
  await Promise.all([
    notificationStore.fetchNotifications({ skip: 0, limit: pageSize }),
    notificationStore.fetchNotificationStats(),
  ]);
};

const loadMoreNotifications = async () => {
  currentPage.value += 1;
  const skip = currentPage.value * pageSize;
  const newNotifications = await notificationStore.fetchNotifications({
    skip,
    limit: pageSize,
  });

  // Add new notifications to existing ones
  if (newNotifications && newNotifications.length > 0) {
    notificationStore.notifications.push(...newNotifications);
  }
};

const markAsRead = async (notificationId) => {
  await notificationStore.markNotificationAsRead(notificationId);
};

const markAllAsRead = async () => {
  await notificationStore.markAllNotificationsAsRead();
};

const deleteNotification = async (notificationId) => {
  await notificationStore.deleteNotification(notificationId);
};

const handleNotificationClick = async (notification) => {
  // if notification is unread, mark it as read
  if (!notification.is_read) {
    await markAsRead(notification.notification_id);
  }
};

const handleNotificationAction = async (notification) => {
  // this handles notification actions
  // Mark as read if not already read
  if (!notification.is_read) {
    await markAsRead(notification.notification_id);
  }

  // Navigate to action URL
  if (notification.action_url) {
    router.push(notification.action_url);
  }
};

const updatePreferences = async () => {
  try {
    const preferencesData = {
      email_enabled: Boolean(preferences.value.email_enabled),
    };
    await notificationStore.updateNotificationPreferences(preferencesData);
  } catch (error) {
    reportClientError('Error updating notification preferences', error);
  }
};

const toggleEmailPreference = () => {
  preferences.value.email_enabled = !preferences.value.email_enabled;
  updatePreferences();
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return formatDistanceToNow(date, {
    addSuffix: true,
    locale: fr,
  });
};

// Watchers
watch(currentFilter, () => {
  // Reset pagination when filter changes
  currentPage.value = 0;
});

// Lifecycle
onMounted(async () => {
  await Promise.all([
    refreshNotifications(),
    notificationStore.fetchNotificationPreferences(),
  ]);
});
</script>

<style scoped>
@import url('../../../assets/css/profile-notifications.css');
</style>
