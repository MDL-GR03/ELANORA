<template>
  <section class="automation-settings" aria-labelledby="automation-title">
    <div class="policy-card">
      <div>
        <span class="policy-eyebrow">{{
          t('contributionAutomation.eyebrow')
        }}</span>
        <h3 id="automation-title">{{ t('contributionAutomation.title') }}</h3>
        <p>{{ t('contributionAutomation.description') }}</p>
      </div>
      <button
        type="button"
        class="policy-toggle"
        role="switch"
        :aria-checked="enabled"
        :disabled="saving"
        @click="save(!enabled)"
      >
        <span aria-hidden="true"></span>
        {{
          enabled
            ? t('contributionAutomation.enabled')
            : t('contributionAutomation.disabled')
        }}
      </button>
    </div>

    <div class="policy-boundary">
      <font-awesome-icon icon="fa-solid fa-shield-halved" />
      <i18n-t :keypath="'contributionAutomation.boundary'" tag="p">
        <template #corrections>
          <router-link :to="correctionsRoute">{{
            t('contributionAutomation.corrections')
          }}</router-link>
        </template>
        <template #incoming>
          <router-link :to="incomingWorkRoute">{{
            t('contributionAutomation.incoming')
          }}</router-link>
        </template>
      </i18n-t>
    </div>

    <p
      v-if="message"
      class="policy-message"
      :class="{ error }"
      aria-live="polite"
    >
      {{ message }}
    </p>
  </section>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { useI18n } from 'vue-i18n';
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import gitService from '@/api/service/gitService';
import { useProjectStore } from '@/stores/project';

const { t } = useI18n();

const route = useRoute();
const projectStore = useProjectStore();
const saving = ref(false);
const message = ref('');
const error = ref(false);

const projectId = computed(() => Number(route.params.projectId));
const project = computed(() =>
  projectStore.projects.find((item) => item.project_id === projectId.value)
);
const enabled = computed(() => Boolean(project.value?.auto_accept_new_files));
const incomingWorkRoute = computed(() => ({
  path: '/contribution',
  query: { project: projectId.value, view: 'queue' },
}));
const correctionsRoute = computed(() => ({
  path: '/contribution',
  query: { project: projectId.value, view: 'reviews' },
}));

async function save(value) {
  saving.value = true;
  message.value = '';
  error.value = false;
  try {
    await gitService.updateContributionPolicy(projectId.value, value);
    const projects = projectStore.projects.map((item) =>
      item.project_id === projectId.value
        ? { ...item, auto_accept_new_files: value }
        : item
    );
    projectStore.setProjects(projects);
    const updated = projects.find(
      (item) => item.project_id === projectId.value
    );
    if (
      projectStore.currentProject?.project_id === projectId.value &&
      updated
    ) {
      projectStore.setCurrentProject(updated);
    }
    message.value = value
      ? t('contributionAutomation.saved_enabled')
      : t('contributionAutomation.saved_disabled');
  } catch (requestError) {
    error.value = true;
    message.value = apiErrorMessage(
      requestError,
      t,
      t('contributionAutomation.save_failed')
    );
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.automation-settings {
  display: grid;
  gap: 1rem;
}

.policy-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1.25rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  background: white;
}

.policy-card h3,
.policy-card p,
.policy-boundary p,
.policy-message {
  margin: 0;
}

.policy-card h3 {
  margin: 0.25rem 0 0.45rem;
}

.policy-card p,
.policy-boundary {
  color: #64748b;
  line-height: 1.55;
}

.policy-eyebrow {
  color: #2563eb;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.policy-toggle {
  display: inline-flex;
  align-items: center;
  flex: none;
  gap: 0.55rem;
  min-width: 7rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid #94a3b8;
  border-radius: 999px;
  color: #475569;
  background: #f8fafc;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.policy-toggle span {
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: #94a3b8;
}

.policy-toggle[aria-checked='true'] {
  border-color: #15803d;
  color: #166534;
  background: #f0fdf4;
}

.policy-toggle[aria-checked='true'] span {
  background: #16a34a;
}

.policy-toggle:disabled {
  cursor: wait;
  opacity: 0.6;
}

.policy-boundary {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  padding: 0.9rem 1rem;
  border-radius: 0.6rem;
  background: #f1f5f9;
}

.policy-boundary svg {
  flex: none;
  margin-top: 0.2rem;
  color: #2563eb;
}

.policy-boundary a {
  color: #1d4ed8;
  font-weight: 700;
}

.policy-boundary a:hover {
  text-decoration-thickness: 2px;
}

.policy-message {
  color: #166534;
  font-weight: 700;
}

.policy-message.error {
  color: #b91c1c;
}

@media (width <= 700px) {
  .policy-card {
    align-items: stretch;
    flex-direction: column;
    gap: 1rem;
  }

  .policy-toggle {
    justify-content: center;
    width: 100%;
  }
}
</style>
