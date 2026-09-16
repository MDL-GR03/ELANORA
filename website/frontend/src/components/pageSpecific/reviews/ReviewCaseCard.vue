<template>
  <article
    :id="`review-${item.case_id}`"
    class="case-card"
    :class="{ highlighted: item.case_id === highlightedCaseId }"
  >
    <div class="case-heading">
      <div class="case-identity">
        <div class="case-flags">
          <span class="state-badge" :class="`state-${item.state}`">
            {{ formatState(item.state) }}
          </span>
          <span v-if="item.unread" class="activity-badge">
            <font-awesome-icon icon="fa-solid fa-circle" />
            {{ t('reviewCases.card.unread') }}
          </span>
        </div>
        <h5>{{ item.title }}</h5>
        <p v-if="item.filename" class="target">
          {{ item.filename
          }}<template v-if="item.tier_id"> · {{ item.tier_id }}</template>
          <template v-if="item.annotation_id">
            · {{ item.annotation_id }}</template
          >
        </p>
        <div class="contribution-lineage">
          <span>
            <small>{{ t('reviewCases.card.originallyReviewed') }}</small>
            {{ t('reviewCases.card.contribution', { id: item.upload_id }) }}
          </span>
          <template v-if="item.resubmitted_upload_id">
            <font-awesome-icon icon="fa-solid fa-arrow-right" />
            <span class="current-contribution">
              <small>{{ t('reviewCases.card.correctedToReview') }}</small>
              {{
                t('reviewCases.card.contribution', {
                  id: item.resubmitted_upload_id,
                })
              }}
            </span>
          </template>
        </div>
      </div>
      <label
        v-if="canManage && !isFinished(item.state)"
        class="reviewer-field"
        :for="`review-lead-${item.case_id}`"
      >
        <span>{{ t('reviewCases.card.reviewLead') }}</span>
        <AppSelect
          :id="`review-lead-${item.case_id}`"
          :model-value="item.assigned_to || ''"
          :aria-label="t('reviewCases.card.chooseLead', { title: item.title })"
          :title="t('reviewCases.card.leadHelp')"
          :disabled="busy || membersLoading"
          :placeholder="t('reviewCases.card.selectLead')"
          :options="reviewLeadOptions"
          @change="assign(item, $event)"
        />
      </label>
    </div>

    <div
      v-if="item.current_text || item.suggested_text"
      class="suggestion-diff"
      :aria-label="t('reviewCases.card.replacement')"
    >
      <div v-if="item.current_text" class="diff-before">
        <span>{{ t('reviewCases.card.current') }}</span>
        <p>{{ item.current_text }}</p>
      </div>
      <div v-if="item.suggested_text" class="diff-after">
        <span>{{ t('reviewCases.card.suggested') }}</span>
        <p>{{ item.suggested_text }}</p>
      </div>
    </div>

    <ReviewCaseTaskList :item="item" />

    <ReviewCaseNextStep :item="item" />

    <ReviewCaseDiscussion :item="item" />
  </article>
</template>

<script setup>
import AppSelect from '@/components/common/AppSelect.vue';
import ReviewCaseDiscussion from './ReviewCaseDiscussion.vue';
import ReviewCaseNextStep from './ReviewCaseNextStep.vue';
import ReviewCaseTaskList from './ReviewCaseTaskList.vue';
import { useReviewCaseContext } from './reviewCaseContext';

defineProps({
  item: { type: Object, required: true },
});

const {
  assign,
  busy,
  canManage,
  formatState,
  highlightedCaseId,
  isFinished,
  membersLoading,
  reviewLeadOptions,
  t,
} = useReviewCaseContext();
</script>
