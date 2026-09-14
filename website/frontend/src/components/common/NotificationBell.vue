<template>
  <div ref="root" class="relative notification-bell">
    <!-- Notification Bell Button -->
    <button
      ref="trigger"
      type="button"
      class="relative p-3 text-gray-600 hover:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-full transition-all duration-200 ease-in-out transform hover:scale-105"
      :class="{
        'text-blue-600 bg-blue-50': hasUnreadNotifications,
        'hover:bg-gray-100': !hasUnreadNotifications,
      }"
      :title="
        unreadCount > 0
          ? t('notificationBell.unread_notifications', { count: unreadCount })
          : t('notificationBell.title')
      "
      :aria-label="triggerLabel"
      aria-haspopup="dialog"
      :aria-expanded="showDropdown"
      :aria-controls="panelId"
      @click="toggleDropdown"
    >
      <!-- Bell Icon -->
      <svg
        class="w-6 h-6 transition-transform duration-200"
        :class="{ 'animate-pulse': hasUnreadNotifications }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

      <!-- Unread Count Badge -->
      <transition name="badge-bounce">
        <span
          v-if="unreadCount > 0"
          class="absolute -top-1 -right-1 bg-gradient-to-br from-red-500 to-red-600 text-white text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center shadow-lg border-2 border-white transform animate-bounce"
          aria-hidden="true"
        >
          {{ unreadCount > 99 ? '99+' : unreadCount }}
        </span>
      </transition>
    </button>

    <!-- Dropdown Panel -->
    <transition name="dropdown-fade">
      <div
        v-if="showDropdown"
        :id="panelId"
        class="notification-dropdown absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-gray-200 z-50"
        role="dialog"
        :aria-labelledby="headingId"
        :aria-describedby="statusId"
        @keydown="handlePanelKeydown"
        @click.stop
      >
        <!-- Dropdown Header -->
        <div
          class="notification-dropdown-header px-4 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <div class="p-2 bg-blue-100 rounded-lg">
                <svg
                  class="w-5 h-5 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
              </div>
              <h3 :id="headingId" class="text-lg font-semibold text-gray-900">
                {{ t('notificationBell.title') }}
              </h3>
            </div>
            <div class="notification-header-actions">
              <button
                v-if="unreadCount > 0"
                class="mark-all-read px-3 py-1.5 text-sm text-blue-600 hover:text-blue-800 font-medium bg-white rounded-lg border border-blue-200 hover:bg-blue-50 transition-colors duration-200"
                :disabled="loading"
                @click="markAllAsRead"
              >
                <span class="flex items-center space-x-1">
                  <svg
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span>{{ t('notificationBell.mark_all_read') }}</span>
                </span>
              </button>
              <button
                ref="closeButton"
                type="button"
                class="notification-close"
                :aria-label="t('notificationBell.close')"
                @click="closeDropdown(true)"
              >
                <span aria-hidden="true">×</span>
              </button>
            </div>
          </div>
          <div class="flex items-center justify-between mt-2">
            <p :id="statusId" class="text-sm text-gray-600" aria-live="polite">
              <span
                class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {{ t('notificationBell.unread_badge', { count: unreadCount }) }}
              </span>
            </p>
          </div>
        </div>

        <!-- Notifications List -->
        <div class="notification-list max-h-96 overflow-y-auto">
          <div v-if="loading" class="p-8 text-center" role="status">
            <div
              class="inline-flex items-center justify-center w-12 h-12 bg-blue-100 rounded-full mb-4"
            >
              <div
                class="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent"
              ></div>
            </div>
            <p class="text-sm text-gray-600 font-medium">
              {{ t('notificationBell.loading_notifications') }}
            </p>
          </div>

          <div v-else-if="notifications.length === 0" class="p-8 text-center">
            <div
              class="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4"
            >
              <svg
                class="w-8 h-8 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            </div>
            <p class="text-gray-500 font-medium">
              {{ t('notificationBell.no_notifications') }}
            </p>
            <p class="text-xs text-gray-400 mt-1">
              {{ t('notificationBell.up_to_date') }}
            </p>
          </div>

          <div v-else class="divide-y divide-gray-100">
            <article
              v-for="notification in notifications"
              :key="notification.notification_id"
              class="px-4 py-4 hover:bg-gray-50 transition-all duration-200 group"
              :class="{
                'bg-gradient-to-r from-blue-50 to-transparent border-l-4 border-blue-400':
                  !notification.is_read,
                'hover:transform hover:scale-[1.01]': true,
              }"
            >
              <div class="flex items-start space-x-3">
                <!-- Notification Icon -->
                <div class="flex-shrink-0 mt-1">
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center"
                    :class="
                      !notification.is_read
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-gray-100 text-gray-500'
                    "
                  >
                    <svg
                      class="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                </div>

                <!-- Notification Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-start justify-between">
                    <h4 class="text-sm font-semibold text-gray-900">
                      <button
                        type="button"
                        class="notification-open-button group-hover:text-blue-700"
                        @click="handleNotificationClick(notification)"
                      >
                        {{ notification.title }}
                      </button>
                    </h4>
                    <!-- Unread indicator -->
                    <div v-if="!notification.is_read" class="ml-2 mt-1">
                      <div
                        class="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse"
                      ></div>
                    </div>
                  </div>
                  <p
                    class="text-sm text-gray-600 mt-1 line-clamp-2 leading-relaxed"
                  >
                    {{ notification.message }}
                  </p>
                  <div class="flex items-center justify-between mt-2">
                    <p
                      class="text-xs text-gray-500 flex items-center space-x-1"
                    >
                      <svg
                        class="w-3 h-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <span>{{ formatDate(notification.created_at) }}</span>
                    </p>

                    <!-- Action Buttons -->
                    <div class="notification-item-actions">
                      <button
                        v-if="!notification.is_read"
                        class="p-1.5 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded-full transition-all duration-200"
                        :title="t('notificationBell.mark_as_read')"
                        :aria-label="t('notificationBell.mark_as_read')"
                        @click.stop="markAsRead(notification.notification_id)"
                      >
                        <svg
                          class="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M5 13l4 4L19 7"
                          />
                        </svg>
                      </button>
                      <button
                        class="p-1.5 text-red-600 hover:text-red-800 hover:bg-red-100 rounded-full transition-all duration-200"
                        :title="t('notificationBell.delete')"
                        :aria-label="t('notificationBell.delete')"
                        @click.stop="
                          deleteNotification(notification.notification_id)
                        "
                      >
                        <svg
                          class="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>

        <!-- Dropdown Footer -->
        <div class="px-4 py-4 bg-gray-50 border-t border-gray-200">
          <router-link
            to="/profile?tab=notifications"
            class="flex items-center justify-center space-x-2 w-full px-4 py-2 text-sm text-blue-600 hover:text-blue-800 font-medium bg-white hover:bg-blue-50 border border-blue-200 rounded-lg transition-all duration-200 transform hover:scale-105"
            @click="closeDropdown"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              />
            </svg>
            <span>{{ t('notificationBell.view_all_notifications') }}</span>
          </router-link>
        </div>
      </div>
    </transition>

    <!-- Overlay to close dropdown -->
    <div
      v-if="showDropdown"
      class="fixed inset-0 z-40"
      aria-hidden="true"
      @click="closeDropdown(true)"
    ></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, useId } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useNotificationStore } from '@/stores/notification';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
import { reportClientError } from '@/utils/errorDiagnostics';

const router = useRouter();
const notificationStore = useNotificationStore();
const { t } = useI18n();

// Local state
const showDropdown = ref(false);
const root = ref(null);
const trigger = ref(null);
const closeButton = ref(null);
const generatedId = useId();
const panelId = `notifications-panel-${generatedId}`;
const headingId = `notifications-heading-${generatedId}`;
const statusId = `notifications-status-${generatedId}`;

// Computed properties
const notifications = computed(() => notificationStore.unreadNotifications);
const unreadCount = computed(() => notificationStore.unreadCount);
const hasUnreadNotifications = computed(
  () => notificationStore.hasUnreadNotifications
);
const loading = computed(() => notificationStore.loading);
const triggerLabel = computed(() =>
  unreadCount.value > 0
    ? t('notificationBell.unread_notifications', { count: unreadCount.value })
    : t('notificationBell.title')
);

// Methods
const toggleDropdown = async () => {
  if (showDropdown.value) {
    closeDropdown(true);
    return;
  }
  showDropdown.value = true;
  await nextTick();
  closeButton.value?.focus();

  try {
    await notificationStore.fetchUnreadNotifications({ limit: 10 });
    await notificationStore.fetchNotificationStats();
  } catch (error) {
    reportClientError('Failed to fetch notifications for dropdown', error);
  }
};

const closeDropdown = (restoreFocus = false) => {
  showDropdown.value = false;
  if (restoreFocus) void nextTick(() => trigger.value?.focus());
};

const handlePanelKeydown = (event) => {
  if (event.key !== 'Escape') return;
  event.preventDefault();
  event.stopPropagation();
  closeDropdown(true);
};

const markAsRead = async (notificationId) => {
  try {
    await notificationStore.markNotificationAsRead(notificationId);
  } catch (error) {
    reportClientError('Failed to mark notification as read', error);
  }
};

const markAllAsRead = async () => {
  try {
    await notificationStore.markAllNotificationsAsRead();
  } catch (error) {
    reportClientError('Failed to mark all notifications as read', error);
  }
};

const deleteNotification = async (notificationId) => {
  try {
    await notificationStore.deleteNotification(notificationId);
  } catch (error) {
    reportClientError('Failed to delete notification', error);
  }
};

const handleNotificationClick = async (notification) => {
  try {
    // Mark as read if not already read
    if (!notification.is_read) {
      await markAsRead(notification.notification_id);
    }

    // Navigate to action URL if available
    if (notification.action_url) {
      closeDropdown();
      router.push(notification.action_url);
    }
  } catch (error) {
    reportClientError('Failed to handle notification click', error);
  }
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return formatDistanceToNow(date, {
    addSuffix: true,
    locale: fr,
  });
};

let notificationInterval;

// Lifecycle
onMounted(async () => {
  try {
    // Fetch initial notification stats
    await notificationStore.fetchNotificationStats();

    // Set up polling for new notifications every 60 seconds
    notificationInterval = setInterval(async () => {
      if (document.visibilityState !== 'visible') return;
      try {
        await notificationStore.fetchNotificationStats();
      } catch {
        console.warn('Failed to fetch notification stats in interval');
      }
    }, 60000);

    // Store interval ID for cleanup
  } catch (error) {
    reportClientError('Failed to initialize notification bell', error);
  }
});

onUnmounted(() => {
  if (notificationInterval) {
    clearInterval(notificationInterval);
  }
});

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (showDropdown.value && !root.value?.contains(event.target)) {
    closeDropdown(true);
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.notification-dropdown {
  max-width: calc(100vw - 2rem);
  overflow: visible;
}

.notification-header-actions,
.notification-item-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.notification-close {
  width: 2.75rem;
  height: 2.75rem;
  display: grid;
  flex: none;
  place-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 0.65rem;
  background: #fff;
  color: #475569;
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
}

.notification-close:hover,
.notification-close:focus-visible {
  border-color: #93b4f5;
  background: #eff6ff;
  color: #1d4ed8;
  outline: none;
  box-shadow: 0 0 0 3px rgb(37 99 235 / 14%);
}

.notification-open-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.notification-open-button:focus-visible {
  border-radius: 0.25rem;
  outline: 2px solid #2563eb;
  outline-offset: 3px;
}

.notification-item-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

article:hover .notification-item-actions,
article:focus-within .notification-item-actions {
  opacity: 1;
}

.notification-dropdown::before {
  position: absolute;
  z-index: 1;
  top: -0.45rem;
  right: 1rem;
  width: 0.8rem;
  height: 0.8rem;
  border-top: 1px solid #e5e7eb;
  border-left: 1px solid #e5e7eb;
  background: #eff6ff;
  content: '';
  transform: rotate(45deg);
}

.notification-dropdown-header {
  border-radius: 0.75rem 0.75rem 0 0;
}

@media (width <= 1024px) {
  .notification-dropdown {
    position: absolute;
    top: 100%;
    right: auto;
    left: 50%;
    width: min(20rem, calc(100vw - 2rem));
    max-height: calc(100dvh - 7rem);
    margin-top: 0.65rem;
    transform: translateX(-50%);
  }

  .notification-list {
    max-height: calc(100dvh - 19rem);
  }

  .notification-item-actions {
    opacity: 1;
  }

  .notification-dropdown::before {
    right: auto;
    left: 50%;
    transform: translateX(-50%) rotate(45deg);
  }

  .notification-dropdown-header > div:first-child {
    align-items: flex-start;
    gap: 0.6rem;
  }

  .mark-all-read {
    padding-inline: 0.65rem;
    font-size: 0.78rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .notification-bell *,
  .notification-bell *::before,
  .notification-bell *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media (width <= 420px) {
  .notification-dropdown {
    right: auto;
    left: 50%;
    width: calc(100vw - 1rem);
    max-width: none;
    transform: translateX(-50%);
  }

  .notification-dropdown-header > div:first-child {
    flex-wrap: wrap;
  }

  .mark-all-read {
    width: 100%;
  }

  .mark-all-read > span {
    justify-content: center;
  }
}

.mark-all-read {
  min-height: 2.25rem;
  flex: none;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* transition animations */
.badge-bounce-enter-active,
.badge-bounce-leave-active {
  transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.badge-bounce-enter-from,
.badge-bounce-leave-to {
  opacity: 0;
  transform: scale(0.5) rotate(180deg);
}

.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

/* Custom scrollbar for notifications list */
.max-h-96::-webkit-scrollbar {
  width: 6px;
}

.max-h-96::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.max-h-96::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.max-h-96::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* Smooth hover animations */
.group:hover .opacity-0 {
  opacity: 1;
}

/* Focus states */
button:focus {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 2px rgb(59 130 246 / 50%);
}

/* Loading animation */
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}

/* Pulse animation for unread indicators */
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* Bounce animation for notification badge */
@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
    animation-timing-function: cubic-bezier(0.8, 0, 1, 1);
  }

  50% {
    transform: translateY(-25%);
    animation-timing-function: cubic-bezier(0, 0, 0.2, 1);
  }
}

.animate-bounce {
  animation: bounce 1s infinite;
}
</style>
