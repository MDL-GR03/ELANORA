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
        <i18n-t
          :keypath="'contributionWorkspace.card.collision'"
          :plural="collisionCount"
          tag="p"
        >
          <template #count>{{ collisionCount }}</template>
          <template #contributions>
            <template
              v-for="(collision, index) in upload.annotation_collisions"
              :key="collision.contribution_id"
            >
              <span v-if="index > 0">, </span>
              <button
                type="button"
                @click="$emit('show-contribution', collision.contribution_id)"
              >
                {{
                  t('contributionWorkspace.card.contribution', {
                    id: collision.contribution_id,
                  })
                }}
              </button>
            </template>
          </template>
        </i18n-t>
      </div>
    </div>

    <div v-if="upload.version_history?.length" class="version-history">
      <div class="version-context">
        <font-awesome-icon icon="fa-solid fa-code-branch" />
        <i18n-t :keypath="'contributionWorkspace.card.updated_for'" tag="span">
          <template #request>
            <button
              v-if="upload.review_case"
              type="button"
              class="inline-review-link"
              @click="$emit('discussion')"
            >
              {{
                upload.review_case.title ||
                t('contributionWorkspace.card.correction_request')
              }}
            </button>
            <span v-else>{{
              t('contributionWorkspace.card.correction_request')
            }}</span>
          </template>
        </i18n-t>
      </div>
      <details>
        <summary>
          {{
            t('contributionWorkspace.card.history', {
              count: upload.version_number,
            })
          }}
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
              {{
                t('contributionWorkspace.card.version', {
                  number: index + 1,
                  id: version.upload_id,
                })
              }}
            </button>
            <span>{{ formatDate(version.uploaded_at) }}</span>
          </li>
          <li class="current-version">
            <strong>
              {{
                t('contributionWorkspace.card.version', {
                  number: upload.version_number,
                  id: upload.upload_id,
                })
              }}
            </strong>
            <span
              >{{ formatDate(upload.uploaded_at) }} ·
              {{ t('contributionWorkspace.card.current_version') }}</span
            >
          </li>
        </ol>
      </details>
    </div>

    <div v-if="upload.duplicate_of_upload_id" class="duplicate-notice">
      <font-awesome-icon icon="fa-solid fa-copy" />
      {{
        t('contributionWorkspace.card.duplicate', {
          id: upload.duplicate_of_upload_id,
        })
      }}
    </div>
    <div v-if="upload.superseded_by_upload_id" class="duplicate-notice">
      <font-awesome-icon icon="fa-solid fa-code-branch" />
      {{
        t('contributionWorkspace.card.superseded', {
          id: upload.superseded_by_upload_id,
        })
      }}
    </div>

    <div
      class="quality-checks"
      :aria-label="t('contributionWorkspace.card.quality_checks')"
    >
      <span class="quality-check passed">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        {{ t('contributionWorkspace.card.valid_files') }}
      </span>
      <span class="quality-check passed">
        <font-awesome-icon icon="fa-solid fa-circle-check" />
        {{ t('contributionWorkspace.card.naming_passed') }}
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
      :aria-label="t('contributionWorkspace.card.semantic_summary')"
    >
      <strong>
        {{
          t(
            'contributionWorkspace.card.annotation_changes',
            upload.semantic_summary.annotations
          )
        }}
      </strong>
      <span v-if="upload.semantic_summary.added" class="semantic-count added">
        {{
          t('contributionWorkspace.card.added', {
            count: upload.semantic_summary.added,
          })
        }}
      </span>
      <span
        v-if="upload.semantic_summary.removed"
        class="semantic-count removed"
      >
        {{
          t('contributionWorkspace.card.removed', {
            count: upload.semantic_summary.removed,
          })
        }}
      </span>
      <span
        v-if="upload.semantic_summary.value_changed"
        class="semantic-count changed"
      >
        {{
          t('contributionWorkspace.card.value_changed', {
            count: upload.semantic_summary.value_changed,
          })
        }}
      </span>
      <span
        v-if="upload.semantic_summary.timing_changed"
        class="semantic-count changed"
      >
        {{
          t('contributionWorkspace.card.timing_changed', {
            count: upload.semantic_summary.timing_changed,
          })
        }}
      </span>
      <span
        v-if="upload.semantic_summary.tier_changed"
        class="semantic-count changed"
      >
        {{
          t('contributionWorkspace.card.tier_changed', {
            count: upload.semantic_summary.tier_changed,
          })
        }}
      </span>
      <span
        v-if="upload.semantic_summary.media_changed"
        class="semantic-count media"
      >
        {{ t('contributionWorkspace.card.media_changed') }}
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
  const outcome = protocolOutcome.value;
  return ['passed', 'recheck_required', 'not_configured'].includes(outcome)
    ? t(`contributionWorkspace.card.protocol.${outcome}`)
    : t('contributionWorkspace.card.protocol.not_recorded');
});

function formatDate(dateString) {
  if (!dateString) return t('pendingUploads.unknown');
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString));
}
</script>
