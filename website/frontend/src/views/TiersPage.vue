<template>
  <div class="tiers-page">
    <WorkspaceHeader
      :title="t('researchScopes.title')"
      :context="currentProject?.project_name || ''"
      :description="t('researchScopes.description')"
    />
    <section class="tiers-workspace" :aria-busy="loading">
      <nav
        class="tiers-mode-tabs"
        role="tablist"
        :aria-label="t('researchScopes.workspaceLabel')"
      >
        <button
          v-for="tab in MODE_TABS"
          :id="tab.id"
          :key="tab.mode"
          type="button"
          role="tab"
          :aria-selected="activeMode === tab.mode"
          :aria-controls="tab.panel"
          :tabindex="activeMode === tab.mode ? 0 : -1"
          :class="{ 'is-active': activeMode === tab.mode }"
          @click="activeMode = tab.mode"
          @keydown="onModeTabKeydown"
        >
          {{ t(tab.label) }}
          <span
            v-if="tab.mode === 'topics' && topics.length"
            class="tiers-tab-count"
            >{{ topics.length }}</span
          >
        </button>
      </nav>
      <div v-if="loading" class="tiers-state-panel">
        {{ t('researchScopes.loading') }}
      </div>
      <div
        v-else-if="error"
        class="tiers-state-panel tiers-state-panel--error"
        role="alert"
      >
        {{ error }}
      </div>
      <ResearchCopyWorkspace
        v-else-if="activeMode === 'export'"
        :project-name="currentProject.project_name"
        :topic-load-error="topicLoadError"
      />
      <ResearchTopicsPanel
        v-else
        :project-id="currentProject.project_id"
        :topics="topics"
        :tier-groups="tierGroups"
        :baseline-tiers="baselineTiers"
        :can-manage="canManageTopics"
        :topic-load-error="topicLoadError"
        @changed="reload"
        @baseline-saved="baselineTiers = $event"
        @use-topic="useTopic"
      />
    </section>
  </div>
</template>

<script setup>
import '@/assets/css/tiers.css';
import { computed, onMounted, ref, watch } from 'vue';
import { useHead } from '@unhead/vue';
import { useI18n } from 'vue-i18n';

import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import ResearchCopyWorkspace from '@/components/pageSpecific/tiers/ResearchCopyWorkspace.vue';
import ResearchTopicsPanel from '@/components/pageSpecific/tiers/ResearchTopicsPanel.vue';
import { provideResearchCopyContext } from '@/components/pageSpecific/tiers/researchCopyContext';
import { useResearchCopySelection } from '@/composables/useResearchCopySelection';
import { useResearchScopes } from '@/composables/useResearchScopes';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';

const MODE_TABS = [
  {
    mode: 'export',
    id: 'research-copy-tab',
    panel: 'research-copy-panel',
    label: 'researchScopes.tabs.prepare',
  },
  {
    mode: 'topics',
    id: 'research-topics-tab',
    panel: 'research-topics-panel',
    label: 'researchScopes.tabs.topics',
  },
];

const { t } = useI18n();
const projectStore = useProjectStore();
const userStore = useUserStore();
useHead({ title: t('researchScopes.title') });

const currentProject = computed(() => projectStore.currentProject);
const canManageTopics = computed(
  () =>
    userStore.user?.role === 'admin' ||
    ['admin', 'owner'].includes(projectStore.currentPermission)
);
const activeMode = ref('export');

const {
  tierGroups,
  topics,
  baselineTiers,
  loading,
  error,
  topicLoadError,
  clear,
  load,
} = useResearchScopes({ translate: t });
const selection = useResearchCopySelection({
  tierGroups,
  topics,
  baselineTiers,
});
provideResearchCopyContext({ ...selection, tierGroups, topics });

async function reload() {
  const loaded = await load(currentProject.value?.project_id);
  if (loaded && tierGroups.value.length) {
    selection.selectGroup(tierGroups.value[0]);
  }
}

function useTopic(topic) {
  selection.applyTopic(topic);
  activeMode.value = 'export';
}

function onModeTabKeydown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const tab = MODE_TABS[['ArrowLeft', 'Home'].includes(event.key) ? 0 : 1];
  activeMode.value = tab.mode;
  document.getElementById(tab.id)?.focus();
}

watch(
  () => currentProject.value?.project_id,
  () => {
    clear();
    selection.reset();
    void reload();
  },
  { immediate: true }
);
onMounted(() => projectStore.initBroadcastChannel());
</script>
