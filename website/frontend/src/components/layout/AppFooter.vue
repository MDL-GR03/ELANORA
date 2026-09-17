<template>
  <footer>
    <div class="footer-container">
      <div class="footer-content">
        <div class="footer-section footer-intro">
          <h4>ELANORA</h4>
          <p>{{ t('appFooter.platform_description') }}</p>
        </div>

        <div class="footer-section">
          <h4>{{ t('home.workspace') }}</h4>
          <ul class="footer-links">
            <li>
              <router-link to="/projects">{{
                t('appHeader.projects')
              }}</router-link>
            </li>
            <li>
              <router-link to="/upload">{{
                t('appHeader.upload')
              }}</router-link>
            </li>
            <li>
              <router-link to="/tiers">{{ t('appHeader.tiers') }}</router-link>
            </li>
          </ul>
        </div>

        <div class="footer-section">
          <h4>{{ t('appFooter.resources') }}</h4>
          <ul class="footer-links">
            <li>
              <router-link to="/contact">{{
                t('appFooter.contact')
              }}</router-link>
            </li>
          </ul>
        </div>
      </div>

      <div class="footer-bottom">
        <div class="footer-copyright">
          <p>
            &copy; {{ currentYear }} ELANORA.
            {{ t('appFooter.all_rights_reserved') }}
          </p>
        </div>
        <div class="footer-info">
          <span class="version">v{{ version }}</span>
          <span class="separator">•</span>
          <span class="instance">{{ instanceName || 'Default Instance' }}</span>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue';
import { useAppInfoStore } from '@/stores/appInfo';
import { useI18n } from 'vue-i18n';

const appInfo = useAppInfoStore();
const instanceName = computed(() => appInfo.instanceName);
const version = computed(() => appInfo.version);
const currentYear = computed(() => new Date().getFullYear());
const { t } = useI18n();
</script>

<style scoped>
.footer-content {
  display: grid;
  grid-template-columns: minmax(16rem, 2fr) repeat(2, minmax(9rem, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.footer-intro {
  max-width: 34rem;
}

.footer-section h4 {
  color: var(--color-gray-blue-500);
  font-size: 0.82rem;
  margin-bottom: 1rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.footer-section p {
  color: var(--color-gray-blue-200);
  line-height: 1.6;
  margin-bottom: 1rem;
}

.footer-links {
  list-style: none;
  padding: 0;
}

.footer-links li {
  margin-bottom: 0.5rem;
}

.footer-links a {
  color: var(--color-gray-blue-200);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: var(--color-gray-blue-400);
}

.footer-bottom {
  border-top: 1px solid var(--color-gray-blue-300);
  padding-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.footer-copyright p {
  color: var(--color-gray-blue-200);
  font-size: 0.9rem;
  margin: 0;
}

.footer-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--color-gray-blue-200);
}

.version {
  background: var(--color-gray-blue-300);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
}

.separator {
  color: var(--color-gray-blue-100);
}

.instance {
  color: var(--color-gray-blue-500);
  font-weight: 500;
}

@media (width <= 768px) {
  .footer-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }

  .footer-bottom {
    flex-direction: column;
    text-align: center;
  }
}
</style>
