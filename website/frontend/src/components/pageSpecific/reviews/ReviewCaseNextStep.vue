<template>
  <div
    v-if="showNextStep(item)"
    class="case-next-step"
    :class="[
      `next-${item.state}`,
      { 'feedback-open': revisionFeedbackCaseId === item.case_id },
    ]"
  >
    <div class="next-step-copy">
      <font-awesome-icon :icon="nextStepIcon(item.state)" />
      <div>
        <strong>{{ nextStepTitle(item.state, item) }}</strong>
        <span>{{ nextStepDescription(item.state, item) }}</span>
        <button
          v-if="isFinished(item.state)"
          type="button"
          class="next-step-link"
          @click="openReviewArchive"
        >
          {{ t('reviewCases.nextStep.openArchive') }}
        </button>
      </div>
    </div>
    <div
      v-if="
        canManage &&
        item.state === 'resubmitted' &&
        revisionFeedbackCaseId === item.case_id
      "
      class="revision-feedback"
    >
      <section
        v-if="revisionTargets[item.case_id]?.length"
        class="revision-targets"
        :aria-label="t('reviewCases.revision.selectedAnnotations')"
      >
        <div class="revision-targets-heading">
          <strong>{{ t('reviewCases.revision.selectedCorrections') }}</strong>
          <span>{{ revisionTargets[item.case_id].length }}</span>
        </div>
        <article
          v-for="target in revisionTargets[item.case_id]"
          :key="`${target.task_id}:${target.annotation_id}`"
          class="revision-target"
        >
          <div class="revision-target-identity">
            <div>
              <strong>{{ target.annotation_id }}</strong>
              <span>{{
                target.tier_id || t('reviewCases.revision.unknownTier')
              }}</span>
            </div>
            <button
              type="button"
              :aria-label="t('reviewCases.revision.removeTarget')"
              @click="removeRevisionTarget(item, target)"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>
          <span class="revision-target-location">
            {{ revisionTargetSummary(target) }}
          </span>
          <label>
            <span>{{ t('reviewCases.revision.instruction') }}</span>
            <input
              v-model.trim="target.comment"
              maxlength="1000"
              :placeholder="t('reviewCases.revision.instructionPlaceholder')"
            />
          </label>
        </article>
      </section>
      <label class="revision-general-note">
        <span>
          {{
            revisionTargets[item.case_id]?.length
              ? t('reviewCases.revision.wholeNote')
              : t('reviewCases.revision.instructions')
          }}
        </span>
        <textarea
          v-model.trim="replies[item.case_id]"
          maxlength="10000"
          :required="!revisionTargets[item.case_id]?.length"
          :placeholder="t('reviewCases.revision.notePlaceholder')"
        ></textarea>
      </label>
    </div>
    <div v-if="canManage && !isFinished(item.state)" class="case-actions">
      <router-link
        v-if="item.state === 'changes_requested' && canActAsContributor(item)"
        class="correct-upload-link"
        :to="{
          name: 'UploadPage',
          query: { project: projectId, correction: item.case_id },
        }"
      >
        <font-awesome-icon icon="fa-solid fa-cloud-arrow-up" />
        {{ t('reviewCases.actions.uploadCorrected') }}
      </router-link>
      <button
        v-if="item.state === 'open'"
        type="button"
        :disabled="busy || !item.assigned_to"
        @click="transition(item, 'changes_requested')"
      >
        {{ t('reviewCases.actions.requestFirst') }}
      </button>
      <button
        v-if="
          item.state === 'resubmitted' &&
          selectedRevisionTaskIds(item).length > 0
        "
        type="button"
        class="request-another-revision"
        :disabled="
          busy ||
          !item.assigned_to ||
          (revisionFeedbackCaseId === item.case_id &&
            !hasRevisionFeedback(item))
        "
        @click="beginOrRequestAnotherRevision(item)"
      >
        <font-awesome-icon icon="fa-solid fa-rotate-left" />
        {{
          revisionFeedbackCaseId === item.case_id
            ? t('reviewCases.actions.sendRequest', {
                count: revisionRequestCount(item),
              })
            : t('reviewCases.actions.addFeedback')
        }}
      </button>
      <button
        v-if="item.state === 'resubmitted' && unresolvedTaskCount(item) === 0"
        class="resolve-case"
        type="button"
        :disabled="busy || !item.assigned_to"
        @click="transition(item, 'resolved')"
      >
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        {{ t('reviewCases.actions.approveAndClose') }}
      </button>
      <button
        v-if="item.state === 'open'"
        class="resolve-case"
        type="button"
        :disabled="busy || !item.assigned_to"
        @click="transition(item, 'resolved')"
      >
        {{ t('reviewCases.actions.closeWithoutChanges') }}
      </button>
    </div>
    <button
      v-else-if="canManage && isFinished(item.state)"
      type="button"
      class="reopen-case"
      :disabled="busy"
      @click="transition(item, 'open')"
    >
      <font-awesome-icon icon="fa-solid fa-rotate-left" />
      {{ t('reviewCases.actions.reopen') }}
    </button>
    <router-link
      v-else-if="
        canComment &&
        canActAsContributor(item) &&
        !resubmissionUploadId &&
        item.state === 'changes_requested'
      "
      class="correct-upload-link"
      :to="{
        name: 'UploadPage',
        query: { project: projectId, correction: item.case_id },
      }"
    >
      <font-awesome-icon icon="fa-solid fa-cloud-arrow-up" />
      {{ t('reviewCases.actions.uploadCorrected') }}
    </router-link>
    <button
      v-else-if="
        canComment &&
        canActAsContributor(item) &&
        resubmissionUploadId &&
        item.state === 'changes_requested'
      "
      type="button"
      class="resubmit-case"
      :disabled="busy"
      @click="linkResubmission(item)"
    >
      {{ t('reviewCases.actions.linkUpload') }}
    </button>
  </div>
</template>

<script setup>
import { useReviewCaseContext } from './reviewCaseContext';

defineProps({
  item: { type: Object, required: true },
});

const {
  beginOrRequestAnotherRevision,
  busy,
  canActAsContributor,
  canComment,
  canManage,
  hasRevisionFeedback,
  isFinished,
  linkResubmission,
  nextStepDescription,
  nextStepIcon,
  nextStepTitle,
  openReviewArchive,
  projectId,
  removeRevisionTarget,
  replies,
  resubmissionUploadId,
  revisionFeedbackCaseId,
  revisionRequestCount,
  revisionTargetSummary,
  revisionTargets,
  selectedRevisionTaskIds,
  showNextStep,
  t,
  transition,
  unresolvedTaskCount,
} = useReviewCaseContext();
</script>
