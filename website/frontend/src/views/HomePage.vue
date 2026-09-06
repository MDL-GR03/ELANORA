<template>
  <div class="workspace-home">
    <section class="welcome-panel">
      <div class="welcome-copy">
        <p class="eyebrow">Research workspace</p>
        <h1>
          Welcome back<span v-if="firstName">, {{ firstName }}</span
          >.
        </h1>
        <p>
          Coordinate ELAN annotation, preserve revision history, and apply your
          institution’s research protocols from one workspace.
        </p>
        <div class="welcome-actions">
          <router-link class="primary-action" to="/projects"
            >Open projects</router-link
          ><router-link class="secondary-action" to="/upload"
            >Submit annotations</router-link
          >
        </div>
      </div>
      <div class="workspace-summary" aria-label="Workspace summary">
        <span class="summary-value">{{ projectCount }}</span
        ><span class="summary-label">Accessible projects</span
        ><span class="summary-rule"></span
        ><span class="summary-institution">{{ institutionName }}</span>
      </div>
    </section>
    <section class="work-grid" aria-labelledby="continue-title">
      <div class="section-heading">
        <p class="eyebrow">Workspace</p>
        <h2 id="continue-title">Continue your work</h2>
      </div>
      <div class="action-grid">
        <router-link
          v-for="item in actions"
          :key="item.title"
          :to="item.to"
          class="action-card"
          ><span class="action-icon" aria-hidden="true">{{ item.icon }}</span
          ><span
            ><strong>{{ item.title }}</strong
            ><small>{{ item.description }}</small></span
          ><span class="action-arrow" aria-hidden="true">→</span></router-link
        >
      </div>
    </section>
    <section class="research-principles">
      <div>
        <p class="eyebrow">Built for accountable research</p>
        <h2>Evidence stays connected to decisions.</h2>
      </div>
      <ul>
        <li>Versioned ELAN annotation history</li>
        <li>Protocol-aware validation</li>
        <li>Explicit review and conflict resolution</li>
        <li>Institution-controlled data and identity</li>
      </ul>
    </section>
  </div>
</template>
<script setup>
import { computed } from 'vue';
import { useHead } from '@unhead/vue';
import { useAppInfoStore } from '@/stores/appInfo';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
useHead({ title: 'Workspace · ELANORA' });
const appInfo = useAppInfoStore();
const projects = useProjectStore();
const user = useUserStore();
const firstName = computed(() => user.user?.first_name || '');
const projectCount = computed(() => projects.projects.length);
const institutionName = computed(
  () => appInfo.instance?.institution_name || 'Your institution'
);
const actions = [
  {
    title: 'Projects',
    description: 'Browse corpora, files, history, and collaborators.',
    to: '/projects',
    icon: '▱',
  },
  {
    title: 'Upload annotations',
    description: 'Validate and submit an ELAN contribution.',
    to: '/upload',
    icon: '↑',
  },
  {
    title: 'Review contributions',
    description: 'Inspect pending changes and resolve conflicts.',
    to: '/contribution',
    icon: '✓',
  },
  {
    title: 'Tier catalogue',
    description: 'Explore the annotation structure used by projects.',
    to: '/tiers',
    icon: '≡',
  },
];
</script>
<style scoped src="@/assets/css/home-page.css"></style>
