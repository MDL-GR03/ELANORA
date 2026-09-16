<template>
  <div
    id="research-topics-panel"
    class="topics-workspace"
    role="tabpanel"
    aria-labelledby="research-topics-tab"
  >
    <div v-if="topicLoadError" class="tiers-operation-error" role="alert">
      {{ topicLoadError }}
    </div>
    <header class="topics-intro">
      <div>
        <span class="tier-export-eyebrow">{{
          t('researchScopes.topics.eyebrow')
        }}</span>
        <h2>{{ t('researchScopes.topics.title') }}</h2>
        <p>{{ t('researchScopes.topics.description') }}</p>
      </div>
      <button
        v-if="canManage && !editing"
        class="tiers-primary-button"
        type="button"
        @click="openEditor(null)"
      >
        <font-awesome-icon icon="fa-solid fa-plus" />
        {{ t('researchScopes.topics.create') }}
      </button>
    </header>
    <BaselineTiersCard
      :project-id="projectId"
      :baseline-tiers="baselineTiers"
      :tier-groups="tierGroups"
      :can-manage="canManage"
      @saved="emit('baseline-saved', $event)"
    />
    <div v-if="error" class="tiers-operation-error" role="alert">
      {{ error }}
    </div>
    <ResearchTopicEditor
      v-if="editing"
      :key="editedTopic?.topic_id ?? 'new'"
      :topic="editedTopic"
      :tier-groups="tierGroups"
      :pending="pending"
      @save="saveTopic"
      @cancel="closeEditor"
    />
    <div v-else-if="!topics.length" class="topics-empty">
      <font-awesome-icon icon="fa-solid fa-layer-group" />
      <h3>{{ t('researchScopes.topics.emptyTitle') }}</h3>
      <p>{{ t('researchScopes.topics.emptyText') }}</p>
    </div>
    <div v-else class="topic-card-grid">
      <ResearchTopicCard
        v-for="topic in topics"
        :key="topic.topic_id"
        :topic="topic"
        :tier-groups="tierGroups"
        :can-manage="canManage"
        :expanded="expandedTopicId === topic.topic_id"
        @use="emit('use-topic', topic)"
        @edit="openEditor(topic)"
        @remove="removeTopic(topic)"
        @toggle-coverage="toggleCoverage(topic)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import {
  createResearchTopic,
  deleteResearchTopic,
  updateResearchTopic,
} from '@/api/service/tierService';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage';
import { apiErrorMessage } from '@/utils/apiError';
import BaselineTiersCard from './BaselineTiersCard.vue';
import ResearchTopicCard from './ResearchTopicCard.vue';
import ResearchTopicEditor from './ResearchTopicEditor.vue';

const props = defineProps({
  projectId: { type: Number, required: true },
  topics: { type: Array, required: true },
  tierGroups: { type: Array, required: true },
  baselineTiers: { type: Array, required: true },
  canManage: { type: Boolean, default: false },
  topicLoadError: { type: String, default: '' },
});
const emit = defineEmits(['changed', 'baseline-saved', 'use-topic']);

const { t } = useI18n();
const messages = useEventMessageStore();
const confirmAction = useUserConfirm();
const editing = ref(false);
const editedTopic = ref(null);
const pending = ref(false);
const error = ref('');
const expandedTopicId = ref(null);

function openEditor(topic) {
  editedTopic.value = topic;
  editing.value = true;
  error.value = '';
}

function closeEditor() {
  editing.value = false;
  editedTopic.value = null;
}

function toggleCoverage(topic) {
  expandedTopicId.value =
    expandedTopicId.value === topic.topic_id ? null : topic.topic_id;
}

async function saveTopic(payload) {
  pending.value = true;
  error.value = '';
  try {
    if (editedTopic.value) {
      await updateResearchTopic(
        props.projectId,
        editedTopic.value.topic_id,
        payload
      );
    } else {
      await createResearchTopic(props.projectId, payload);
    }
    closeEditor();
    emit('changed');
    messages.addMessage(t('researchScopes.messages.topicSaved'), 'success');
  } catch (e) {
    error.value = apiErrorMessage(
      e,
      t,
      t('researchScopes.messages.topicSaveFailed')
    );
  } finally {
    pending.value = false;
  }
}

async function removeTopic(topic) {
  const confirmed = await confirmAction({
    title: t('researchScopes.messages.deleteTitle', { topic: topic.name }),
    message: t('researchScopes.messages.deleteText'),
    confirmText: t('researchScopes.topics.delete'),
    cancelText: t('common.cancel'),
    tone: 'danger',
  });
  if (!confirmed) return;
  error.value = '';
  try {
    await deleteResearchTopic(props.projectId, topic.topic_id);
    emit('changed');
    messages.addMessage(t('researchScopes.messages.topicDeleted'), 'success');
  } catch (e) {
    error.value = apiErrorMessage(
      e,
      t,
      t('researchScopes.messages.topicDeleteFailed')
    );
  }
}
</script>
