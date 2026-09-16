<template>
  <section class="research-step">
    <ResearchStepTitle
      number="1"
      :title="t('researchScopes.prepare.topicStepTitle')"
      :text="t('researchScopes.prepare.topicStepText')"
    />
    <div class="topic-choice-grid">
      <button
        type="button"
        :class="{ 'is-active': selectedTopicId === null }"
        @click="applyTopic(null)"
      >
        <strong>{{ t('researchScopes.prepare.custom') }}</strong>
        <small>{{ t('researchScopes.prepare.customHint') }}</small>
      </button>
      <button
        v-for="topic in topics"
        :key="topic.topic_id"
        type="button"
        :class="{ 'is-active': selectedTopicId === topic.topic_id }"
        @click="applyTopic(topic)"
      >
        <strong>{{ topic.name }}</strong>
        <small>{{
          t('researchScopes.matchingFiles', {
            count: filesCoveringTopic(tierGroups, topic),
          })
        }}</small>
      </button>
    </div>
  </section>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

import { filesCoveringTopic } from '@/utils/tierCoverage';
import ResearchStepTitle from './ResearchStepTitle.vue';
import { useResearchCopyContext } from './researchCopyContext';

const { t } = useI18n();
const { topics, tierGroups, selectedTopicId, applyTopic } =
  useResearchCopyContext();
</script>
