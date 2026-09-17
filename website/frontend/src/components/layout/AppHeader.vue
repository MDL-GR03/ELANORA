<template>
  <header>
    <button
      v-if="menuOpen"
      type="button"
      class="mobile-menu-backdrop"
      :aria-label="t('appHeader.navigation.close')"
      tabindex="-1"
      @click="closeMenu(true)"
    ></button>
    <div class="navbar-container">
      <div class="elanora-header-left">
        <router-link
          to="/homePage"
          class="elanora-header-logo-link"
          :aria-label="t('appHeader.navigation.home')"
        >
          <img
            src="@logos/ELANora-logo.png"
            alt=""
            class="elanora-header-logo"
          />
        </router-link>
        <InstanceSection />
        <button
          ref="menuButton"
          class="mobile-menu-button"
          type="button"
          :aria-expanded="menuOpen"
          aria-controls="primary-navigation"
          :aria-label="t('appHeader.navigation.toggle')"
          @click="toggleMenu"
        >
          <span></span><span></span><span></span>
        </button>
        <nav
          id="primary-navigation"
          class="elanora-header-nav"
          :aria-label="t('appHeader.navigation.primary')"
          :class="{ open: menuOpen }"
        >
          <router-link to="/projects" class="elanora-header-menu-link">
            <font-awesome-icon icon="fa-solid fa-folder" />
            {{ t('appHeader.projects') }}
          </router-link>
          <router-link
            v-if="canWriteProject"
            to="/upload"
            class="elanora-header-menu-link"
          >
            <font-awesome-icon icon="fa-solid fa-cloud-arrow-up" />
            {{ t('appHeader.upload') }}
          </router-link>
          <router-link
            v-if="canReadProject"
            to="/contribution"
            class="elanora-header-menu-link"
          >
            <font-awesome-icon icon="fa-solid fa-code-branch" />
            {{ t('appHeader.contribution') }}
          </router-link>
          <router-link
            v-if="canReadProject"
            :to="{ name: 'TiersPage' }"
            class="elanora-header-menu-link"
          >
            <font-awesome-icon icon="fa-solid fa-layer-group" />
            {{ t('appHeader.tiers') || 'Tiers' }}
          </router-link>
          <router-link
            v-if="isAdministrator"
            :to="{ name: 'OperationsPage' }"
            class="elanora-header-menu-link"
          >
            <font-awesome-icon icon="fa-solid fa-heart-pulse" />
            {{ t('appHeader.operations') }}
          </router-link>
          <div class="mobile-nav-footer">
            <ProjectSection />
            <NotificationBell v-if="userStore.isAuthenticated" />
            <div class="mobile-instance-mark">
              <img :src="instanceLogo" :alt="`${instanceName} logo`" />
            </div>
          </div>
        </nav>
      </div>
      <div class="elanora-header-right" :class="{ open: menuOpen }">
        <ProjectSection />
        <!-- User Section with Notifications -->
        <div
          v-if="userStore.isAuthenticated"
          class="elanora-header-user-section"
        >
          <NotificationBell />
        </div>
        <div class="elanora-header-instance-logo-container">
          <img
            :src="instanceLogo"
            :alt="`${instanceName} logo`"
            class="elanora-header-instance-logo"
          />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { useAppInfoStore } from '@/stores/appInfo';
import { useProjectStore } from '@/stores/project';
import { hasProjectPermission } from '@/utils/authorization';
import InstanceSection from '@/components/pageSpecific/appHeader/InstanceSection.vue';
import ProjectSection from '@/components/pageSpecific/appHeader/ProjectSection.vue';
import NotificationBell from '@/components/common/NotificationBell.vue';

const { t } = useI18n();
const userStore = useUserStore();
const appInfoStore = useAppInfoStore();
const projectStore = useProjectStore();
const route = useRoute();
const menuOpen = ref(false);
const menuButton = ref(null);
const instanceName = computed(
  () => appInfoStore.instance?.instance_name || 'Institution'
);
const instanceLogo = computed(
  () =>
    appInfoStore.instance?.logo_url ||
    '/instance/images/logos/instance-logo.png'
);
const canReadProject = computed(() =>
  hasProjectPermission(userStore.user, projectStore.currentProject, 'read')
);
const canWriteProject = computed(() =>
  hasProjectPermission(userStore.user, projectStore.currentProject, 'write')
);
const isAdministrator = computed(() => userStore.user?.role === 'admin');
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false;
  }
);

function closeMenu(restoreFocus = false) {
  menuOpen.value = false;
  if (restoreFocus) menuButton.value?.focus();
}

function toggleMenu() {
  if (menuOpen.value) closeMenu();
  else menuOpen.value = true;
}

function handleWindowKeydown(event) {
  if (event.key === 'Escape' && menuOpen.value) {
    event.preventDefault();
    closeMenu(true);
  }
}

onMounted(() => window.addEventListener('keydown', handleWindowKeydown));
onBeforeUnmount(() =>
  window.removeEventListener('keydown', handleWindowKeydown)
);
</script>

<style scoped>
.navbar-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  width: 100%;
  min-width: 0;
}

.elanora-header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  min-width: 0;
}

.elanora-header-logo {
  height: 3rem;
  width: 3rem;
  object-fit: contain;
}

.elanora-header-logo-link {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.elanora-header-nav {
  display: flex;
  align-items: stretch;
}

.mobile-nav-footer {
  display: none;
}

.mobile-menu-button {
  display: none;
}

.mobile-menu-backdrop {
  display: none;
}

.elanora-header-menu-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.75rem;
  color: var(--color-gray-800);
  font-weight: 600;
  text-decoration: none;
  padding: 0.55rem 0.9rem;
  border-radius: var(--radius-md);
  transition:
    color 0.18s ease,
    background 0.18s ease;
}

.elanora-header-menu-link + .elanora-header-menu-link::before {
  position: absolute;
  top: 25%;
  bottom: 25%;
  left: 0;
  width: 1px;
  background: var(--color-border-subtle);
  content: '';
}

.elanora-header-menu-link svg {
  width: 0.9rem;
  color: var(--color-text-muted);
  transition: color 0.18s ease;
}

.elanora-header-menu-link:hover,
.elanora-header-menu-link:focus-visible {
  background: var(--color-primary-subtle);
  color: var(--color-primary-dark);
  outline: none;
}

.elanora-header-menu-link:focus-visible {
  box-shadow: 0 0 0 3px rgb(37 99 235 / 16%);
}

.elanora-header-menu-link.router-link-active {
  color: var(--color-primary-dark);
  background: var(--color-primary-bg);
}

.elanora-header-menu-link:hover svg,
.elanora-header-menu-link:focus-visible svg,
.elanora-header-menu-link.router-link-active svg {
  color: var(--color-primary);
}

.elanora-header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: auto;
  min-width: 0;
  max-width: 40vw;
  flex-shrink: 1;
}

.elanora-header-instance-logo-container {
  height: 3rem;
  width: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  overflow: hidden;
}

.elanora-header-instance-logo {
  max-height: 90%;
  max-width: 90%;
  object-fit: contain;
  display: block;
}

/* User Section Styles */
.elanora-header-user-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

@media (width <= 1024px) {
  .mobile-menu-backdrop {
    position: fixed;
    z-index: 30;
    inset: 0;
    display: block;
    padding: 0;
    border: 0;
    background: transparent;
  }

  .navbar-container {
    position: relative;
    z-index: 31;
    min-height: 4rem;
    gap: 0.75rem;
    width: 100%;
    padding-inline: 0.75rem;
  }

  .elanora-header-logo,
  .elanora-header-instance-logo-container {
    width: 3.5rem;
    height: 3.5rem;
  }

  .mobile-menu-button {
    display: grid;
    width: 2.75rem;
    height: 2.75rem;
    margin-left: auto;
    place-content: center;
    gap: 0.3rem;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-md);
    background: var(--color-surface);
  }

  .mobile-menu-button span {
    width: 1.25rem;
    height: 2px;
    background: var(--color-gray-800);
  }

  .elanora-header-nav,
  .elanora-header-right {
    display: none;
    position: absolute;
    z-index: 40;
    right: auto;
    left: 0.75rem;
    width: min(26rem, calc(100% - 1.5rem));
    padding: 0.5rem;
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    box-shadow: 0 1rem 2rem rgb(15 23 42 / 16%);
  }

  .elanora-header-nav.open {
    top: calc(100% + 0.5rem);
    display: grid;
    gap: 0;
    border-radius: 0.75rem;
  }

  .elanora-header-right.open {
    display: none;
  }

  .elanora-header-menu-link {
    min-height: 2.75rem;
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.6rem 0.7rem;
    border: 0;
    border-bottom: 1px solid var(--color-border-strong);
    border-radius: 0;
    color: var(--color-gray-800);
    font-size: 0.92rem;
    font-weight: 600;
  }

  .elanora-header-menu-link + .elanora-header-menu-link::before {
    display: none;
  }

  .elanora-header-menu-link:first-child {
    border-radius: var(--radius-md) var(--radius-md) 0 0;
  }

  .elanora-header-menu-link:last-of-type {
    border-bottom-color: transparent;
    border-radius: 0 0 var(--radius-md) var(--radius-md);
  }

  .elanora-header-menu-link svg {
    display: block;
    width: 1rem;
    color: var(--color-text-muted);
  }

  .elanora-header-menu-link:hover {
    background: var(--color-surface-subtle);
    color: var(--color-primary-dark);
  }

  .elanora-header-menu-link.router-link-active {
    border-bottom-color: var(--color-info-bg);
    background: var(--color-primary-subtle);
    color: var(--color-primary-dark);
    box-shadow: inset 3px 0 var(--color-primary);
  }

  .elanora-header-menu-link.router-link-active svg {
    color: var(--color-primary);
  }

  .mobile-nav-footer {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin: 0.35rem -0.5rem -0.5rem;
    padding: 0.65rem 0.75rem;
    border-top: 1px solid var(--color-border);
    background: var(--color-surface-subtle);
  }

  .mobile-nav-footer :deep(.project-section-root) {
    max-width: min(13rem, 60vw);
  }

  .mobile-nav-footer :deep(.project-section-trigger) {
    max-width: 100%;
  }

  .mobile-instance-mark {
    width: 2.35rem;
    height: 2.35rem;
    display: grid;
    margin-left: auto;
    place-items: center;
    overflow: hidden;
    border: 0;
    background: transparent;
  }

  .mobile-instance-mark img {
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
  }

  .elanora-header-instance-logo-container {
    margin-left: auto;
  }
}

@media (width <= 560px) {
  .elanora-header-left {
    width: 100%;
    gap: 0.75rem;
  }

  .elanora-header-logo {
    width: 3rem;
    height: 3rem;
  }

  .elanora-header-nav,
  .elanora-header-right {
    left: 0.5rem;
    width: calc(100% - 1rem);
  }
}
</style>
