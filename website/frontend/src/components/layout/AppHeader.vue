<template>
  <header>
    <button
      v-if="menuOpen"
      type="button"
      class="mobile-menu-backdrop"
      aria-label="Close navigation"
      @click="menuOpen = false"
    ></button>
    <div class="navbar-container">
      <div class="elanora-header-left">
        <router-link to="/homePage" class="elanora-header-logo-link">
          <img
            src="@logos/ELANora-logo.png"
            alt=""
            class="elanora-header-logo"
          />
        </router-link>
        <InstanceSection />
        <button
          class="mobile-menu-button"
          type="button"
          :aria-expanded="menuOpen"
          aria-controls="primary-navigation"
          aria-label="Toggle navigation"
          @click="menuOpen = !menuOpen"
        >
          <span></span><span></span><span></span>
        </button>
        <nav
          id="primary-navigation"
          class="elanora-header-nav"
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
import { computed, ref, watch } from 'vue';
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
  color: #334155;
  font-weight: 600;
  text-decoration: none;
  padding: 0.55rem 0.9rem;
  border-radius: 0.55rem;
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
  background: #e5eaf2;
  content: '';
}

.elanora-header-menu-link svg {
  width: 0.9rem;
  color: #64748b;
  transition: color 0.18s ease;
}

.elanora-header-menu-link:hover,
.elanora-header-menu-link:focus-visible {
  background: #e8f0fe;
  color: #1d4ed8;
  outline: none;
}

.elanora-header-menu-link:focus-visible {
  box-shadow: 0 0 0 3px rgb(37 99 235 / 16%);
}

.elanora-header-menu-link.router-link-active {
  color: #1d4ed8;
  background: #edf4ff;
}

.elanora-header-menu-link:hover svg,
.elanora-header-menu-link:focus-visible svg,
.elanora-header-menu-link.router-link-active svg {
  color: #2563eb;
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

.elanora-header-project-label {
  background: #f3e8ff;
  color: #7c3aed;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 1rem;
  font-weight: 600;
}

/* User Section Styles */
.elanora-header-user-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.elanora-header-user-menu {
  position: relative;
}

.elanora-header-user-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #374151;
  font-size: 0.875rem;
}

.elanora-header-user-button:hover {
  background: #f9fafb;
  border-color: #d1d5db;
}

.elanora-header-user-avatar {
  width: 2rem;
  height: 2rem;
  background: #e5e7eb;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
}

.elanora-header-username {
  font-weight: 500;
  color: #374151;
}

.elanora-header-user-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 0.5rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow:
    0 10px 15px -3px rgb(0 0 0 / 10%),
    0 4px 6px -2px rgb(0 0 0 / 5%);
  min-width: 12rem;
  z-index: 50;
  overflow: hidden;
}

.elanora-header-user-menu-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.75rem 1rem;
  text-decoration: none;
  color: #374151;
  font-size: 0.875rem;
  transition: background-color 0.2s ease;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
}

.elanora-header-user-menu-item:hover {
  background: #f9fafb;
}

.elanora-header-logout {
  color: #dc2626;
  border-top: 1px solid #e5e7eb;
}

.elanora-header-logout:hover {
  background: #fef2f2;
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
    border: 1px solid #cbd5e1;
    border-radius: 0.65rem;
    background: #fff;
  }

  .mobile-menu-button span {
    width: 1.25rem;
    height: 2px;
    background: #334155;
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
    border: 1px solid #e2e8f0;
    background: #fff;
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
    border-bottom: 1px solid #edf1f6;
    border-radius: 0;
    color: #334155;
    font-size: 0.92rem;
    font-weight: 600;
  }

  .elanora-header-menu-link + .elanora-header-menu-link::before {
    display: none;
  }

  .elanora-header-menu-link:first-child {
    border-radius: 0.5rem 0.5rem 0 0;
  }

  .elanora-header-menu-link:last-of-type {
    border-bottom-color: transparent;
    border-radius: 0 0 0.5rem 0.5rem;
  }

  .elanora-header-menu-link svg {
    display: block;
    width: 1rem;
    color: #64748b;
  }

  .elanora-header-menu-link:hover {
    background: #f8fafc;
    color: #1d4ed8;
  }

  .elanora-header-menu-link.router-link-active {
    border-bottom-color: #dbeafe;
    background: #eff6ff;
    color: #1d4ed8;
    box-shadow: inset 3px 0 #2563eb;
  }

  .elanora-header-menu-link.router-link-active svg {
    color: #2563eb;
  }

  .mobile-nav-footer {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin: 0.35rem -0.5rem -0.5rem;
    padding: 0.65rem 0.75rem;
    border-top: 1px solid #e5eaf2;
    background: #f8fafc;
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
