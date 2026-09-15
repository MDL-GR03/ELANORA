<template>
  <div class="upload-summary">
    <slot name="research-context" />

    <div
      v-if="upload.annotation_collisions?.length"
      class="annotation-collision-notice"
    >
      <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
      <div>
        <strong>{{ t('contributionWorkspace.collision.title') }}</strong>
        <p>
          {{ collisionCount }}
          {{ collisionCount === 1 ? 'annotation' : 'annotations' }} also has a
          different proposal in
          <template
            v-for="(collision, index) in upload.annotation_collisions"
            :key="collision.contribution_id"
          >
            <span v-if="index > 0">, </span>
            <button
              type="button"
              @click="$emit('show-contribution', collision.contribution_id)"
            >
              contribution #{{ collision.contribution_id }}
            </button></template
          >. Review both before accepting either one.
        </p>
      </div>
    </div>

    <div v-if="upload.version_history?.length" class="version-history">
      <div class="version-context">
        <font-awesome-icon icon="fa-solid fa-code-branch" />
        <span>
          This contribution was updated in response to
          <button
            v-if="upload.review_case"
            type="button"
            class="inline-review-link"
            @click="$emit('discussion')"
          >
            {{ upload.review_case.title || 'a correction request' }}
          </button>
          <span v-else>a correction request</span>.
        </span>
      </div>
      <details>
        <summary>
          Contribution history · {{ upload.version_number }} versions
        </summary>
        <ol>
          <li
            v-for="(version, index) in upload.version_history"
            :key="version.upload_id"
          >
            <button
              type="button"
              @click="$emit('view-version', version, $event)"
            >
              Version {{ index + 1 }} · contribution #{{ version.upload_id }}
            </button>
            <span>{{ formatDate(version.uploaded_at) }}</span>
          </li>
          <li class="current-version">
            <strong>
              Version {{ upload.version_number }} · contribution #{{
                upload.upload_id
              }}
            </strong>
            <span>{{ formatDate(upload.uploaded_at) }} · Current version</span>
          </li>
        </ol>
      </details>
    </div>

    <div v-if="upload.duplicate_of_upload_id" class="duplicate-notice">
      <font-awesome-icon icon="fa-solid fa-copy" />
      Same submitted content as contribution #{{
        upload.duplicate_of_upload_id
      }}. Only the original can be accepted.
    </div>
    <div v-if="upload.superseded_by_upload_id" class="duplicate-notice">
      <font-awesome-icon icon="fa-solid fa-code-branch" />
      Superseded by contribution #{{ upload.superseded_by_upload_id }}. This
      version is retained as history and cannot be accepted.
    </div>

    <div class="quality-checks" aria-label="Submission quality checks">
      <span class="quality-check passed">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        Valid ELAN files
      </span>
      <span class="quality-check passed">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        Naming rules passed
      </span>
      <span class="quality-check" :class="protocolCheckClass">
        <font-awesome-icon :icon="protocolCheckIcon" />
        {{ protocolCheckLabel }}
      </span>
    </div>

    <details v-if="protocolWarnings.length" class="protocol-warnings">
      <summary>
        <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
        {{
          t(
            'contributionWorkspace.protocolWarnings.summary',
            protocolWarnings.length
          )
        }}
      </summary>
      <p>{{ t('contributionWorkspace.protocolWarnings.intro') }}</p>
      <ul>
        <li
          v-for="(warning, index) in protocolWarnings"
          :key="`${warning.filename}-${warning.code}-${index}`"
        >
          <strong>{{ warning.filename }}</strong>
          <span>{{ warning.message }}</span>
        </li>
      </ul>
    </details>

    <div class="file-counts">
      <span v-if="upload.file_counts?.new > 0" class="file-count new">
        +{{ upload.file_counts.new }} {{ t('pendingUploads.fileTypes.new') }}
      </span>
      <span v-if="upload.file_counts?.modified > 0" class="file-count modified">
        ~{{ upload.file_counts.modified }}
        {{ t('pendingUploads.fileTypes.modified') }}
      </span>
      <span v-if="upload.file_counts?.deleted > 0" class="file-count deleted">
        -{{ upload.file_counts.deleted }}
        {{ t('pendingUploads.fileTypes.deleted') }}
      </span>
    </div>

    <div
      v-if="upload.semantic_summary?.files"
      class="semantic-recap"
      aria-label="Semantic annotation summary"
    >
      <strong>
        {{ upload.semantic_summary.annotations }} annotation
        {{ upload.semantic_summary.annotations === 1 ? 'change' : 'changes' }}
      </strong>
      <span v-if="upload.semantic_summary.added" class="semantic-count added">
        +{{ upload.semantic_summary.added }} added
      </span>
      <span
        v-if="upload.semantic_summary.removed"
        class="semantic-count removed"
      >
        −{{ upload.semantic_summary.removed }} removed
      </span>
      <span
        v-if="upload.semantic_summary.value_changed"
        class="semantic-count changed"
      >
        {{ upload.semantic_summary.value_changed }} value changed
      </span>
      <span
        v-if="upload.semantic_summary.timing_changed"
        class="semantic-count changed"
      >
        {{ upload.semantic_summary.timing_changed }} timing changed
      </span>
      <span
        v-if="upload.semantic_summary.tier_changed"
        class="semantic-count changed"
      >
        {{ upload.semantic_summary.tier_changed }} tier changed
      </span>
      <span
        v-if="upload.semantic_summary.media_changed"
        class="semantic-count media"
      >
        Linked media changed
      </span>
    </div>
  </div>

  <div v-if="upload.conflicted_files?.length" class="conflicts-section">
    <h4>{{ t('pendingUploads.conflictedFiles') }}:</h4>
    <ul class="conflict-files">
      <li
        v-for="file in upload.conflicted_files"
        :key="file"
        class="conflict-file"
      >
        {{ file }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

import { countAnnotationCollisions } from '@/utils/contributionThreads';

const props = defineProps({
  upload: { type: Object, required: true },
});

defineEmits(['show-contribution', 'discussion', 'view-version']);

const { t } = useI18n();
const collisionCount = computed(() => countAnnotationCollisions(props.upload));
const protocolOutcome = computed(() => props.upload.quality_checks?.protocol);
const protocolWarnings = computed(() => props.upload.protocol_warnings || []);
const protocolCheckClass = computed(() => {
  if (protocolOutcome.value === 'passed') return 'passed';
  if (protocolOutcome.value === 'recheck_required') return 'recheck-required';
  return 'not-configured';
});
const protocolCheckIcon = computed(() => {
  if (protocolOutcome.value === 'passed') return 'fa-solid fa-circle-check';
  if (protocolOutcome.value === 'recheck_required') {
    return 'fa-solid fa-triangle-exclamation';
  }
  return 'fa-solid fa-circle-info';
});
const protocolCheckLabel = computed(() => {
  if (protocolOutcome.value === 'passed') return 'Project protocol passed';
  if (protocolOutcome.value === 'recheck_required') {
    return 'Protocol changed — acceptance will recheck this contribution';
  }
  if (protocolOutcome.value === 'not_configured') {
    return 'No project protocol configured';
  }
  return 'Protocol check not recorded for this older contribution';
});

function formatDate(dateString) {
  if (!dateString) return t('pendingUploads.unknown');
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString));
}
</script>
