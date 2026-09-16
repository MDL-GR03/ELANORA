<template>
  <article class="topic-card">
    <div class="topic-card__summary">
      <div class="topic-card__icon">
        <font-awesome-icon icon="fa-solid fa-layer-group" />
      </div>
      <div class="topic-card__content">
        <h3>
          {{ topic.name }}
          <span v-if="topic.allow_new_tiers" class="topic-policy-badge">{{
            t('researchScopes.topics.newTiersAllowed')
          }}</span>
        </h3>
        <p>{{ topic.description || t('researchScopes.noDescription') }}</p>
        <div class="topic-card__metrics">
          <i18n-t
            keypath="researchScopes.topics.tierCount"
            :plural="topic.tier_names.length"
            tag="span"
          >
            <template #count>
              <strong>{{ topic.tier_names.length }}</strong>
            </template>
          </i18n-t>
          <i18n-t
            keypath="researchScopes.topics.fileCount"
            :plural="matchingFiles"
            tag="span"
          >
            <template #count>
              <strong>{{ matchingFiles }}</strong>
            </template>
          </i18n-t>
          <i18n-t keypath="researchScopes.topics.coverage" tag="span">
            <template #count>
              <strong>{{ matchingFiles }}</strong>
            </template>
            <template #total>{{ tierGroups.length }}</template>
          </i18n-t>
        </div>
      </div>
      <div class="topic-card__actions">
        <button type="button" class="topic-use-button" @click="emit('use')">
          {{ t('researchScopes.topics.prepareCopy') }}
        </button>
        <template v-if="canManage">
          <button
            type="button"
            class="topic-action-button"
            :title="t('researchScopes.topics.edit')"
            :aria-label="t('researchScopes.topics.edit')"
            @click="emit('edit')"
          >
            <font-awesome-icon icon="fa-regular fa-pen-to-square" />
          </button>
          <button
            type="button"
            class="topic-action-button is-danger"
            :title="t('researchScopes.topics.delete')"
            :aria-label="t('researchScopes.topics.delete')"
            @click="emit('remove')"
          >
            <font-awesome-icon icon="trash" />
          </button>
        </template>
      </div>
    </div>
    <button
      type="button"
      class="topic-coverage-toggle"
      :aria-expanded="expanded"
      @click="emit('toggle-coverage')"
    >
      <span>{{
        expanded
          ? t('researchScopes.topics.hideCoverage')
          : t('researchScopes.topics.viewCoverage')
      }}</span>
      <font-awesome-icon
        :icon="expanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"
      />
    </button>
    <TopicCoveragePanel
      v-if="expanded"
      :topic="topic"
      :tier-groups="tierGroups"
    />
  </article>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { filesCoveringTopic } from '@/utils/tierCoverage';
import TopicCoveragePanel from './TopicCoveragePanel.vue';

const props = defineProps({
  topic: { type: Object, required: true },
  tierGroups: { type: Array, required: true },
  canManage: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
});
const emit = defineEmits(['use', 'edit', 'remove', 'toggle-coverage']);

const { t } = useI18n();
const matchingFiles = computed(() =>
  filesCoveringTopic(props.tierGroups, props.topic)
);
</script>
