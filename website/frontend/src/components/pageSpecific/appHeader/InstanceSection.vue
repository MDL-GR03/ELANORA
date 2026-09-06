<template>
  <div class="instance-section-root">
    <span class="instance-section-name">{{ instanceName }}</span>
    <div class="instance-section-user">
      <button
        v-if="isAuthenticated"
        class="instance-section-user-trigger"
        :aria-label="userLabel"
        :aria-expanded="dropdownOpen"
        @click="toggleDropdown"
      >
        <svg
          class="instance-section-usericon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            fill="currentColor"
            d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0H5Z"
          />
        </svg>
        <span class="instance-section-username">{{ username }}</span>
        <svg
          class="instance-section-chevron"
          width="16"
          height="16"
          viewBox="0 0 20 20"
        >
          <path
            fill="currentColor"
            d="M5.23 7.21a1 1 0 0 1 1.41.02L10 10.67l3.36-3.44a1 1 0 1 1 1.42 1.4l-4.07 4.17a1 1 0 0 1-1.42 0L5.21 8.63a1 1 0 0 1 .02-1.42z"
          />
        </svg>
      </button>
      <transition name="instance-section-fade">
        <ul
          v-if="dropdownOpen && isAuthenticated"
          class="instance-section-menu"
          @click.stop
        >
          <li
            v-for="(option, idx) in options"
            :key="idx"
            class="instance-section-menuitem"
          >
            <button
              v-if="option.action"
              class="instance-section-action"
              :type="option.type || 'button'"
              @click="handleAction(option)"
            >
              {{ option.label }}
            </button>
            <router-link
              v-else-if="option.to"
              :to="option.to"
              class="instance-section-link"
              @click="closeDropdown"
            >
              {{ option.label }}
            </router-link>
          </li>
        </ul>
      </transition>
      <button
        v-if="!isAuthenticated"
        class="instance-section-login"
        @click="login"
      >
        <svg
          class="instance-section-usericon"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            fill="currentColor"
            d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0H5Z"
          />
        </svg>
        {{ t('common.login') || 'Login' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/user';
import { useAppInfoStore } from '@/stores/appInfo';

defineProps({
  options: {
    type: Array,
    default: () => [
      {
        label: 'Profile',
        to: '/profile',
      },
      {
        label: 'Logout',
        action: 'logout',
      },
    ],
  },
});

const appInfoStore = useAppInfoStore();
const instanceName = computed(() => appInfoStore.instance?.instance_name || '');

const userStore = useUserStore();
const router = useRouter();
const { t } = useI18n();

const isAuthenticated = computed(
  () => userStore.user && userStore.user.username
);
const username = computed(
  () => userStore.user?.username || userStore.user?.login || ''
);
const userLabel = computed(() =>
  username.value ? `User menu for ${username.value}` : 'User menu'
);

const dropdownOpen = ref(false);

function toggleDropdown() {
  dropdownOpen.value = !dropdownOpen.value;
}
function closeDropdown() {
  dropdownOpen.value = false;
}
function handleAction(option) {
  if (option.action === 'logout') {
    userStore.logout().then(() => {
      closeDropdown();
      router.push('/');
    });
  } else if (typeof option.action === 'function') {
    option.action();
    closeDropdown();
  }
}

function login() {
  router.push({ name: 'LoginPage' });
}

function handleClickOutside(event) {
  if (!event.target.closest('.instance-section-root')) {
    closeDropdown();
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.instance-section-root {
  display: flex;
  align-items: center;
  background: #fff;
  padding: 0.5rem 1.5rem 0.5rem 1rem;
  box-shadow: 0 1px 8px 0 #e8f0fe;
}

.instance-section-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a73e8;
  background: #e8f0fe;
  border-radius: 12px;
  padding: 0.3rem 1rem;
  margin-left: 0.5rem;
}

.instance-section-user {
  margin-left: 1.5rem;
  position: relative;
  display: flex;
  align-items: center;
}

.instance-section-user-trigger,
.instance-section-login {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f3e8ff;
  color: #7c3aed;
  border: none;
  border-radius: 20px;
  padding: 0.4rem 1.1rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition:
    background 0.18s,
    color 0.18s;
  box-shadow: 0 1px 4px 0 #e0e7ef;
  backdrop-filter: blur(2px);
}

.instance-section-user-trigger:hover,
.instance-section-login:hover {
  background: #c7d2fe;
  color: #5b21b6;
}

.instance-section-usericon {
  width: 1.2rem;
  height: 1.2rem;
}

.instance-section-username {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.instance-section-chevron {
  margin-left: 0.2rem;
  transition: transform 0.2s;
  fill: #a78bfa;
}

.instance-section-user-trigger[aria-expanded='true'] .instance-section-chevron {
  transform: rotate(180deg);
}

.instance-section-fade-enter-active,
.instance-section-fade-leave-active {
  transition: opacity 0.18s;
}

.instance-section-fade-enter-from,
.instance-section-fade-leave-to {
  opacity: 0;
}

.instance-section-fade-enter-to,
.instance-section-fade-leave-from {
  opacity: 1;
}

.instance-section-menu {
  position: absolute;
  left: 0;
  top: 110%;
  min-width: 180px;
  background: rgb(255 255 255 / 96%);
  color: #4b5563;
  border-radius: 16px;
  box-shadow: 0 8px 32px 0 rgb(60 60 100 / 12%);
  padding: 0.5rem 0;
  z-index: 100;
  display: flex;
  flex-direction: column;
  animation: instance-section-slide 0.18s;
  backdrop-filter: blur(8px);
  border: 1px solid #e0e7ef;
}

@keyframes instance-section-slide {
  0% {
    transform: translateY(-10px);
    opacity: 0;
  }

  100% {
    transform: translateY(0);
    opacity: 1;
  }
}

.instance-section-menuitem {
  width: 100%;
}

.instance-section-action,
.instance-section-link {
  width: 100%;
  background: none;
  border: none;
  color: inherit;
  font-size: 1rem;
  padding: 0.85rem 1.2rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  transition:
    background 0.16s,
    color 0.16s;
  border-radius: 10px;
  text-decoration: none;
  min-height: 44px;
  box-sizing: border-box;
}

.instance-section-action:hover,
.instance-section-link:hover,
.instance-section-action:focus,
.instance-section-link:focus {
  background: #e6eaff;
  color: #7c3aed;
  outline: none;
}

.instance-section-menuicon {
  font-size: 1.1em;
  color: #a78bfa;
}
</style>
