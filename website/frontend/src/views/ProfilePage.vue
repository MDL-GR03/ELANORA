<template>
  <div class="profile-page">
    <div class="profile-bg-gradient"></div>
    <div class="profile-container">
      <!-- Sidebar menu -->
      <aside class="profile-sidebar">
        <div class="profile-sidebar-header">
          <div class="profile-avatar">
            <span>{{ userProfile?.first_name?.[0] || '👤' }}</span>
          </div>
          <h2>{{ t('profile.title') }}</h2>
        </div>
        <nav class="profile-menu">
          <button
            v-for="item in menuItems"
            :key="item.id"
            class="profile-menu-item"
            :class="{ active: currentSection === item.id }"
            @click="currentSection = item.id"
          >
            <span class="profile-menu-icon">{{ item.icon }}</span>
            <span class="profile-menu-label">{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <!-- Main content area -->
      <main class="profile-content">
        <div class="profile-content-header">
          <div class="profile-header-flex">
            <div>
              <h1>{{ currentMenuItem?.title }}</h1>
              <p
                v-if="currentMenuItem?.description"
                class="profile-content-subtitle"
              >
                {{ currentMenuItem.description }}
              </p>
            </div>
          </div>
        </div>

        <div class="profile-main-card">
          <!-- Profile Overview Section -->
          <ProfileOverview
            v-if="currentSection === 'overview'"
            :user-profile="userProfile"
            :loading="loading"
            :error="error"
            @profile-updated="loadUserProfile"
            @show-message="handleMessage"
          />

          <!-- Settings Section -->
          <ProfileSettings
            v-else-if="currentSection === 'settings'"
            @show-message="handleMessage"
          />

          <!-- Security Section (placeholder) -->
          <ProfileSecurity
            v-else-if="currentSection === 'security'"
            @show-message="handleMessage"
          />

          <!-- Notifications Section -->
          <ProfileNotifications
            v-else-if="currentSection === 'notifications'"
          />
          <InstanceBranding
            v-else-if="currentSection === 'institution'"
            @show-message="handleMessage"
          />
          <InstitutionAccounts
            v-else-if="currentSection === 'accounts'"
            @show-message="handleMessage"
          />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useEventMessageStore } from '@/stores/eventMessage.js';
import { fetchUserProfile } from '@/api/service/userService.js';
import { reportClientError } from '@/utils/errorDiagnostics';

const ProfileOverview = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/ProfileOverview.vue')
);
const ProfileSettings = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/ProfileSettings.vue')
);
const ProfileSecurity = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/ProfileSecurity.vue')
);
const ProfileNotifications = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/ProfileNotifications.vue')
);
const InstanceBranding = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/InstanceBranding.vue')
);
const InstitutionAccounts = defineAsyncComponent(
  () => import('@/components/pageSpecific/profile/InstitutionAccounts.vue')
);

const { t } = useI18n();
const route = useRoute();
const eventMessageStore = useEventMessageStore();
import { useUserStore } from '@/stores/user';
const userStore = useUserStore();

// State
const currentSection = ref('overview');
const userProfile = ref(null);
const loading = ref(true);
const error = ref('');

// Initialize section from route query
onMounted(() => {
  if (
    route.query.tab &&
    [
      'overview',
      'settings',
      'security',
      'notifications',
      'institution',
      'accounts',
    ].includes(route.query.tab)
  ) {
    currentSection.value = route.query.tab;
  }
  loadUserProfile();
});

// Menu configuration
const menuItems = computed(() => [
  {
    id: 'overview',
    label: t('profile.menu.overview'),
    title: t('profile.overview.title'),
    description: t('profile.overview.description'),
    icon: '👤',
  },
  {
    id: 'settings',
    label: t('profile.menu.settings'),
    title: t('profile.settings.title'),
    description: t('profile.settings.description'),
    icon: '⚙️',
  },
  {
    id: 'security',
    label: t('profile.menu.security'),
    title: t('profile.security.title'),
    description: t('profile.security.description'),
    icon: '🔒',
  },
  {
    id: 'notifications',
    label: t('profile.menu.notifications'),
    title: t('profile.notifications.title'),
    description: t('profile.notifications.description'),
    icon: '🔔',
  },
  ...(userStore.user?.role === 'admin'
    ? [
        {
          id: 'institution',
          label: 'Institution',
          title: 'Institution identity',
          description:
            'Manage the workspace name, research identity, colors, and logo.',
          icon: '🏛️',
        },
        {
          id: 'accounts',
          label: t('profile.accounts.menu'),
          title: t('profile.accounts.title'),
          description: t('profile.accounts.description'),
          icon: '👥',
        },
      ]
    : []),
]);

const currentMenuItem = computed(() =>
  menuItems.value.find((item) => item.id === currentSection.value)
);

// Methods
function handleMessage(message) {
  eventMessageStore.addMessage(message.text, message.type);
}

async function loadUserProfile() {
  try {
    loading.value = true;
    error.value = '';
    const response = await fetchUserProfile();
    userProfile.value = response.data;
  } catch (err) {
    reportClientError('Error loading user profile', err);
    error.value = t('profile.errors.load_failed');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
@import url('../assets/css/profile-page.css');
</style>
