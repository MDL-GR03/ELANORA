<template>
  <div class="instance-section-root">
    <span class="instance-section-name">{{ instanceName }}</span>
    <div class="instance-section-user">
      <button
        v-if="isAuthenticated"
        class="instance-section-user-trigger"
        :data-tooltip="fullIdentity"
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
          <li class="instance-section-identity">
            <span class="instance-section-identity-avatar">{{
              userInitial
            }}</span>
            <span>
              <strong>{{ fullIdentity }}</strong>
              <small v-if="userEmail">{{ userEmail }}</small>
            </span>
          </li>
          <li
            v-for="(option, idx) in localizedOptions"
            :key="idx"
            class="instance-section-menuitem"
          >
            <button
              v-if="option.action"
              class="instance-section-action"
              :type="option.type || 'button'"
              @click="handleAction(option)"
            >
              <font-awesome-icon
                :icon="
                  option.action === 'logout'
                    ? 'fa-solid fa-arrow-right-from-bracket'
                    : 'fa-solid fa-user'
                "
              />
              {{ option.label }}
            </button>
            <router-link
              v-else-if="option.to"
              :to="option.to"
              class="instance-section-link"
              @click="closeDropdown"
            >
              <font-awesome-icon icon="fa-solid fa-user" />
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

const props = defineProps({
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
const fullIdentity = computed(() => {
  const fullName = [userStore.user?.first_name, userStore.user?.last_name]
    .filter(Boolean)
    .join(' ');
  return fullName || username.value;
});
const userEmail = computed(() => userStore.user?.email || '');
const userInitial = computed(() =>
  (fullIdentity.value || username.value || '?').charAt(0).toUpperCase()
);
const localizedOptions = computed(() =>
  props.options.map((option) => ({
    ...option,
    label:
      option.action === 'logout'
        ? t('appHeader.logout')
        : option.to === '/profile'
          ? t('appHeader.profile')
          : option.label,
  }))
);
const userLabel = computed(() =>
  fullIdentity.value ? `User menu for ${fullIdentity.value}` : 'User menu'
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
  gap: 0.75rem;
  min-width: 0;
  padding: 0;
}

.instance-section-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a73e8;
  background: #e8f0fe;
  border-radius: 0.65rem;
  padding: 0.48rem 0.9rem;
  white-space: nowrap;
}

.instance-section-user {
  margin-left: 0;
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
  border: 1px solid #eadcff;
  border-radius: 0.65rem;
  padding: 0.48rem 0.75rem;
  font-size: 0.95rem;
  font-weight: 650;
  cursor: pointer;
  transition:
    background 0.18s,
    color 0.18s;
  box-shadow: 0 1px 2px rgb(76 29 149 / 5%);
}

.instance-section-user-trigger:hover,
.instance-section-user-trigger:focus-visible,
.instance-section-login:hover,
.instance-section-login:focus-visible {
  background: #ede9fe;
  color: #5b21b6;
  border-color: #c4b5fd;
  outline: none;
  box-shadow: 0 0 0 3px rgb(124 58 237 / 12%);
}

.instance-section-user-trigger::after {
  content: attr(data-tooltip);
  position: absolute;
  z-index: 120;
  top: calc(100% + 0.55rem);
  left: 50%;
  max-width: min(20rem, 80vw);
  padding: 0.42rem 0.65rem;
  border-radius: 0.45rem;
  background: #17243a;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 500;
  line-height: 1.3;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translate(-50%, -0.25rem);
  transition:
    opacity 120ms ease,
    transform 120ms ease;
}

.instance-section-user-trigger:hover::after,
.instance-section-user-trigger:focus-visible::after {
  opacity: 1;
  transform: translate(-50%, 0);
}

.instance-section-user-trigger[aria-expanded='true']::after {
  display: none;
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
  top: calc(100% + 0.55rem);
  min-width: 15rem;
  max-width: min(21rem, 88vw);
  background: #fff;
  color: #4b5563;
  border-radius: 0.75rem;
  box-shadow: 0 16px 36px rgb(15 23 42 / 16%);
  padding: 0.4rem;
  z-index: 100;
  display: flex;
  flex-direction: column;
  animation: instance-section-slide 0.18s;
  border: 1px solid #dbe3ef;
}

.instance-section-identity {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.35rem;
  padding: 0.65rem 0.7rem 0.75rem;
  border-bottom: 1px solid #e5eaf2;
}

.instance-section-identity-avatar {
  width: 2rem;
  height: 2rem;
  display: grid;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: #ede9fe;
  color: #6d28d9;
  font-weight: 750;
}

.instance-section-identity > span:last-child {
  display: grid;
  min-width: 0;
}

.instance-section-identity strong,
.instance-section-identity small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.instance-section-identity strong {
  color: #1e293b;
  font-size: 0.9rem;
}

.instance-section-identity small {
  color: #64748b;
  font-size: 0.77rem;
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
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.65rem 0.75rem;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.7rem;
  transition:
    background 0.16s,
    color 0.16s;
  border-radius: 0.5rem;
  text-decoration: none;
  min-height: 44px;
  box-sizing: border-box;
}

.instance-section-action:hover,
.instance-section-link:hover,
.instance-section-action:focus,
.instance-section-link:focus {
  background: #f1f5ff;
  color: #7c3aed;
  outline: none;
}

.instance-section-action:last-child {
  color: #b42318;
}
</style>
