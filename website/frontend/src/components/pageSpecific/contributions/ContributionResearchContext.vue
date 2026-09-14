<template>
  <section
    class="research-context-review"
    :class="`research-context-review--${context.scope_status || 'missing_context'}`"
    :aria-label="t('contributionWorkspace.context.aria')"
  >
    <div class="research-context-review__heading">
      <div>
        <strong>
          {{
            context.declared_topic_name ||
            context.proposed_topic_name ||
            t('contributionWorkspace.context.general')
          }}
        </strong>
        <span class="research-context-summary-text">
          {{ context.summary || t('contributionWorkspace.context.noSummary') }}
        </span>
      </div>
      <span class="research-context-status">{{ statusLabel }}</span>
    </div>
    <dl>
      <div>
        <dt>{{ t('contributionWorkspace.context.detectedTiers') }}</dt>
        <dd class="research-tier-list">
          <span
            v-for="tier in context.changed_tiers || []"
            :key="tier"
            :class="tierClasses(tier)"
            :title="tierTitle(tier)"
          >
            {{ tier }}
          </span>
          <em v-if="!context.changed_tiers?.length">
            {{ t('contributionWorkspace.context.noTierChanges') }}
          </em>
        </dd>
      </div>
    </dl>
    <button
      v-if="context.scope_status === 'topic_review_needed'"
      type="button"
      class="research-topic-review-toggle"
      :aria-expanded="expanded"
      @click="$emit('toggle')"
    >
      {{
        expanded
          ? t('contributionWorkspace.context.hideDecision')
          : t('contributionWorkspace.context.reviewSuggestion')
      }}
      <font-awesome-icon
        :icon="expanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"
      />
    </button>
    <p
      v-if="context.scope_status === 'outside_scope'"
      class="research-context-exception"
    >
      {{ t('contributionWorkspace.context.outsideExplanation') }}
    </p>
    <p
      v-else-if="context.scope_status === 'topic_review_needed' && expanded"
      class="research-context-exception"
    >
      {{ t('contributionWorkspace.context.suggestionExplanation') }}
    </p>
    <div
      v-if="
        canAdminister &&
        context.scope_status === 'topic_review_needed' &&
        expanded
      "
      class="research-topic-decision"
    >
      <label>
        <span>{{ t('contributionWorkspace.context.useExisting') }}</span>
        <AppSelect
          :model-value="topicDecision"
          :placeholder="t('contributionWorkspace.context.chooseTopic')"
          :options="topicOptions"
          @update:model-value="$emit('update:topicDecision', $event)"
        />
      </label>
      <button
        type="button"
        class="action-btn view-btn"
        :disabled="!topicDecision || busy"
        @click="$emit('assign')"
      >
        {{ t('contributionWorkspace.context.assignTopic') }}
      </button>
      <label>
        <span>{{ t('contributionWorkspace.context.approveName') }}</span>
        <input
          :value="suggestionName"
          maxlength="100"
          :placeholder="
            context.proposed_topic_name ||
            t('contributionWorkspace.context.newTopicName')
          "
          @input="$emit('update:suggestionName', $event.target.value)"
        />
      </label>
      <button
        type="button"
        class="action-btn review-btn"
        :disabled="!suggestionName.trim() || busy"
        @click="$emit('create')"
      >
        {{ t('contributionWorkspace.context.createTopic') }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  context: { type: Object, default: () => ({}) },
  topicOptions: { type: Array, default: () => [] },
  topicDecision: { type: [String, Number], default: '' },
  suggestionName: { type: String, default: '' },
  canAdminister: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
});

defineEmits([
  'toggle',
  'assign',
  'create',
  'update:topicDecision',
  'update:suggestionName',
]);

const { t } = useI18n();
const statusLabel = computed(
  () =>
    ({
      aligned: t('contributionWorkspace.context.statusAligned'),
      outside_scope: t('contributionWorkspace.context.statusOutside'),
      topic_review_needed: t('contributionWorkspace.context.statusDecision'),
      declared_general: t('contributionWorkspace.context.general'),
      missing_context: t('contributionWorkspace.context.statusMissing'),
    })[props.context.scope_status] ||
    t('contributionWorkspace.context.statusMissing')
);

function tierClasses(tier) {
  return {
    'is-baseline': props.context.baseline_changed_tiers?.includes(tier),
    'is-baseline-correction':
      props.context.declared_baseline_correction_tiers?.includes(tier),
    'is-outside-scope': props.context.outside_scope_tiers?.includes(tier),
  };
}

function tierTitle(tier) {
  if (props.context.outside_scope_tiers?.includes(tier)) {
    return t('contributionDetails.tiers.outside');
  }
  if (props.context.declared_baseline_correction_tiers?.includes(tier)) {
    return t('contributionDetails.tiers.correction');
  }
  if (props.context.baseline_changed_tiers?.includes(tier)) {
    return t('contributionDetails.tiers.baseline');
  }
  return t('contributionDetails.tiers.topic');
}
</script>
