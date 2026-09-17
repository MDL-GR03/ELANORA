<template>
  <div class="contribution-context-fields">
    <div v-if="detectedScope" class="detected-research-scope" role="status">
      <font-awesome-icon icon="fa-solid fa-layer-group" />
      <div>
        <strong>{{ t('uploadPage.context.copyDetected') }}</strong>
        <span>
          {{ detectedScope.topicName || t('uploadPage.context.customScope') }}
          ·
          {{
            t('uploadPage.context.editableTiers', {
              count: detectedScope.tiers.length,
            })
          }}
        </span>
        <small>{{ t('uploadPage.context.scopeCheckHint') }}</small>
      </div>
    </div>

    <label
      v-else
      class="contribution-context-field"
      for="upload-research-topic"
    >
      <span>{{ t('uploadPage.context.topic') }}</span>
      <AppSelect
        id="upload-research-topic"
        v-model="topicChoice"
        :disabled="topicsLoading || busy"
        :placeholder="t('uploadPage.context.topicPlaceholder')"
        :options="topicOptions"
      />
      <small>{{ t('uploadPage.context.topicHint') }}</small>
    </label>

    <label v-if="proposing" class="contribution-context-field">
      <span>{{ t('uploadPage.context.suggestedName') }}</span>
      <input
        v-model.trim="proposedName"
        maxlength="100"
        :placeholder="t('uploadPage.context.suggestedNamePlaceholder')"
      />
      <small>{{ t('uploadPage.context.suggestedNameHint') }}</small>
    </label>

    <div v-if="similarTopic" class="research-topic-suggestion" role="status">
      <div>
        <strong>{{ t('uploadPage.context.similarTopic') }}</strong>
        <span>
          {{
            t('uploadPage.context.similarTopicMessage', {
              proposed: proposedName,
              existing: similarTopic.name,
            })
          }}
        </span>
      </div>
      <button
        type="button"
        class="secondary-button"
        @click="acceptSimilarTopic"
      >
        {{ t('uploadPage.context.useTopic', { topic: similarTopic.name }) }}
      </button>
    </div>

    <label class="contribution-context-field">
      <span>{{ t('uploadPage.context.summary') }}</span>
      <strong class="required-field-label">{{
        t('uploadPage.context.required')
      }}</strong>
      <textarea
        v-model.trim="summary"
        rows="3"
        maxlength="1000"
        :placeholder="t('uploadPage.context.summaryPlaceholder')"
      ></textarea>
      <small>{{ t('uploadPage.context.summaryHint') }}</small>
    </label>

    <slot />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';
import {
  GENERAL_TOPIC,
  PROPOSED_TOPIC,
} from '@/composables/useContributionContext';

/** `context` is the page's useContributionContext; this step edits it. */
const props = defineProps({
  context: { type: Object, required: true },
  topics: { type: Array, required: true },
  topicsLoading: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});

const { t } = useI18n();
const {
  topicChoice,
  proposedName,
  summary,
  detectedScope,
  proposing,
  similarTopic,
  acceptSimilarTopic,
} = props.context;

const topicOptions = computed(() => [
  ...props.topics.map((topic) => ({
    value: String(topic.topic_id),
    label: topic.name,
  })),
  { value: GENERAL_TOPIC, label: t('uploadPage.topics.general') },
  { value: PROPOSED_TOPIC, label: t('uploadPage.topics.propose') },
]);
</script>
