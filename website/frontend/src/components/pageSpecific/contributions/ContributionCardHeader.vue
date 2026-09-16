<template>
  <div class="upload-header">
    <div class="upload-info">
      <h3 class="upload-branch">
        {{ t('contributionWorkspace.contribution', { id: upload.upload_id }) }}
      </h3>
      <div class="upload-meta">
        <span v-if="upload.version_number > 1" class="version-badge">
          {{
            t('contributionWorkspace.updatedVersion', {
              version: upload.version_number,
            })
          }}
        </span>
        <span class="upload-type">{{ formatUploadType(upload) }}</span>
        <span class="upload-date">{{ formatDate(upload.uploaded_at) }}</span>
        <span class="upload-user">
          {{
            t('pendingUploads.uploadedBy', {
              user: upload.uploaded_by || t('pendingUploads.unknown'),
            })
          }}
        </span>
      </div>
    </div>

    <div class="upload-status-section">
      <div class="upload-status">
        <span class="status-badge" :class="statusClass(upload.merge_status)">
          {{ formatStatus(upload.merge_status) }}
        </span>
      </div>

      <div class="upload-actions">
        <button
          type="button"
          class="action-btn view-btn"
          :disabled="actionBusy"
          @click="$emit('view', $event)"
        >
          <font-awesome-icon icon="fa-solid fa-eye" />
          {{ t('pendingUploads.actions.viewDetails') }}
        </button>
        <button
          v-if="upload.review_case"
          type="button"
          class="action-btn review-link-btn"
          :disabled="actionBusy"
          @click="$emit('discussion')"
        >
          <font-awesome-icon icon="fa-solid fa-comments" />
          {{ t('contributionWorkspace.actions.discussion') }}
        </button>
        <button
          v-if="canRequestCorrection"
          type="button"
          class="action-btn review-btn"
          :disabled="actionBusy"
          @click="$emit('request-correction', $event)"
        >
          <font-awesome-icon icon="fa-solid fa-comment-dots" />
          {{ t('contributionWorkspace.actions.requestCorrection') }}
        </button>
        <button
          v-if="canAdminister && upload.merge_status === 'duplicate'"
          type="button"
          class="action-btn dismiss-btn"
          :disabled="actionBusy"
          @click="$emit('dismiss')"
        >
          <font-awesome-icon icon="fa-solid fa-box-archive" />
          {{ t('contributionWorkspace.actions.dismissDuplicate') }}
        </button>
        <button
          v-if="canAdminister && upload.merge_status === 'ready_to_merge'"
          class="action-btn merge-btn"
          type="button"
          :disabled="actionBusy"
          @click="$emit('merge')"
        >
          <font-awesome-icon icon="fa-solid fa-code-merge" />
          {{
            merging
              ? t('pendingUploads.actions.merging')
              : t('pendingUploads.actions.mergeNow')
          }}
        </button>
        <button
          v-if="canAdminister && upload.merge_status === 'needs_resolution'"
          class="action-btn resolve-btn"
          type="button"
          :disabled="actionBusy"
          @click="$emit('resolve', $event)"
        >
          <font-awesome-icon icon="fa-solid fa-screwdriver-wrench" />
          {{ t('pendingUploads.actions.resolveConflicts') }}
        </button>
        <details v-if="showMoreActions" class="contribution-more-actions">
          <summary>{{ t('contributionWorkspace.actions.more') }}</summary>
          <div>
            <button
              type="button"
              class="action-btn test-btn"
              :disabled="actionBusy"
              @click="$emit('test')"
            >
              <font-awesome-icon icon="fa-solid fa-shield-halved" />
              {{
                testing
                  ? t('pendingUploads.actions.testing')
                  : t('pendingUploads.actions.testMerge')
              }}
            </button>
            <button
              type="button"
              class="action-btn decline-btn"
              :disabled="actionBusy"
              @click="$emit('decline', $event)"
            >
              <font-awesome-icon icon="fa-solid fa-ban" />
              {{ t('contributionWorkspace.actions.decline') }}
            </button>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps({
  upload: { type: Object, required: true },
  canAdminister: { type: Boolean, default: false },
  actionBusy: { type: Boolean, default: false },
  merging: { type: Boolean, default: false },
  testing: { type: Boolean, default: false },
});

defineEmits([
  'view',
  'discussion',
  'request-correction',
  'dismiss',
  'merge',
  'resolve',
  'test',
  'decline',
]);

const { t } = useI18n();
const terminalStatuses = ['duplicate', 'superseded'];
const activeReview = computed(
  () =>
    props.upload.review_case &&
    !['resolved', 'closed'].includes(props.upload.review_case.state)
);
const canRequestCorrection = computed(
  () =>
    props.canAdminister &&
    !activeReview.value &&
    !terminalStatuses.includes(props.upload.merge_status)
);
const showMoreActions = computed(
  () =>
    props.canAdminister && !terminalStatuses.includes(props.upload.merge_status)
);

function statusClass(status) {
  return (
    {
      ready_to_merge: 'ready',
      needs_resolution: 'conflicts',
      error: 'error',
      pending_admin_approval: 'pending',
      under_review: 'pending',
      changes_requested: 'conflicts',
      review_required: 'pending',
      duplicate: 'duplicate',
      superseded: 'superseded',
    }[status] || 'pending'
  );
}

function formatStatus(status) {
  return (
    {
      ready_to_merge: t('pendingUploads.status.readyToMerge'),
      needs_resolution: t('pendingUploads.status.needsResolution'),
      error: t('pendingUploads.status.error'),
      pending_admin_approval: t('pendingUploads.status.pendingReview'),
      under_review: t('pendingUploads.status.underReview'),
      changes_requested: t('pendingUploads.status.changesRequested'),
      review_required: t('pendingUploads.status.reviewRequired'),
      duplicate: t('pendingUploads.status.duplicate'),
      superseded: t('pendingUploads.status.superseded'),
    }[status] || status
  );
}

function formatUploadType(upload) {
  const kinds = ['new', 'modified', 'deleted'].filter(
    (kind) => upload.files?.[kind]?.length
  );
  if (kinds.length > 1) return t('pendingUploads.uploadTypes.mixed');
  if (kinds.length === 1) return t(`pendingUploads.uploadTypes.${kinds[0]}`);
  return (
    {
      pending_upload: t('pendingUploads.uploadTypes.newFiles'),
      upload_with_modifications: t(
        'pendingUploads.uploadTypes.withModifications'
      ),
      upload_with_deletions: t('pendingUploads.uploadTypes.withDeletions'),
    }[upload.upload_type] || upload.upload_type
  );
}

function formatDate(dateString) {
  if (!dateString) return t('pendingUploads.unknown');
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString));
}
</script>
