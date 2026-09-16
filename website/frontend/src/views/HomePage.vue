<template>
  <div class="workspace-home">
    <section class="welcome-panel">
      <div class="welcome-copy">
        <p class="eyebrow">{{ t('home.eyebrow') }}</p>
        <h1>
          {{
            firstName
              ? t('home.welcome_named', { name: firstName })
              : t('home.welcome')
          }}
        </h1>
        <p>{{ t('home.introduction') }}</p>
        <div class="welcome-actions">
          <router-link class="primary-action" to="/projects">{{
            t('home.open_projects')
          }}</router-link
          ><router-link class="secondary-action" to="/upload">{{
            t('home.submit_annotations')
          }}</router-link>
        </div>
      </div>
      <div class="workspace-summary" :aria-label="t('home.summary')">
        <span class="summary-value">{{ projectCount }}</span
        ><span class="summary-label">{{ t('home.accessible_projects') }}</span
        ><span class="summary-rule"></span
        ><span class="summary-institution">{{ institutionName }}</span>
      </div>
    </section>
    <section class="work-grid" aria-labelledby="continue-title">
      <div class="section-heading">
        <p class="eyebrow">{{ t('home.workspace') }}</p>
        <h2 id="continue-title">{{ t('home.continue') }}</h2>
      </div>
      <div class="action-grid">
        <router-link
          v-for="item in actions"
          :key="item.key"
          :to="item.to"
          class="action-card"
          ><span class="action-icon" aria-hidden="true">{{ item.icon }}</span
          ><span
            ><strong>{{ t(`home.actions.${item.key}.title`) }}</strong
            ><small>{{
              t(`home.actions.${item.key}.description`)
            }}</small></span
          ><span class="action-arrow" aria-hidden="true">→</span></router-link
        >
      </div>
    </section>
    <section class="research-principles">
      <div>
        <p class="eyebrow">{{ t('home.principles.eyebrow') }}</p>
        <h2>{{ t('home.principles.title') }}</h2>
      </div>
      <ul>
        <li v-for="principle in PRINCIPLES" :key="principle">
          {{ t(`home.principles.${principle}`) }}
        </li>
      </ul>
    </section>
  </div>
</template>
<script setup>
import { useI18n } from 'vue-i18n';
import { computed } from 'vue';
import { useHead } from '@unhead/vue';
import { useAppInfoStore } from '@/stores/appInfo';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';

const { t } = useI18n();
useHead({ title: () => `${t('home.workspace')} · ELANORA` });
const appInfo = useAppInfoStore();
const projects = useProjectStore();
const user = useUserStore();
const firstName = computed(() => user.user?.first_name || '');
const projectCount = computed(() => projects.projects.length);
const institutionName = computed(
  () => appInfo.instance?.institution_name || t('setup.preview.institution')
);
const PRINCIPLES = ['history', 'validation', 'review', 'ownership'];
const actions = [
  {
    key: 'projects',
    to: '/projects',
    icon: '▱',
  },
  {
    key: 'upload',
    to: '/upload',
    icon: '↑',
  },
  {
    key: 'review',
    to: '/contribution',
    icon: '✓',
  },
  {
    key: 'tiers',
    to: '/tiers',
    icon: '≡',
  },
];
</script>
<style scoped src="@/assets/css/home-page.css"></style>
