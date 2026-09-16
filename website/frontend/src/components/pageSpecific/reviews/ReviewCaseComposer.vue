<template>
  <form class="case-composer" @submit.prevent="submit">
    <label>
      <span>{{ t('reviewCases.composer.shortTitle') }}</span>
      <input v-model.trim="draft.title" required maxlength="200" />
    </label>
    <fieldset v-if="filenames.length" class="file-task-builder">
      <legend>{{ t('reviewCases.composer.selectFiles') }}</legend>
      <div class="builder-introduction">
        <p class="builder-help">{{ t('reviewCases.composer.help') }}</p>
        <strong>{{
          t('reviewCases.composer.selectedCount', {
            selected: selectedFileCount,
            total: taskDrafts.length,
          })
        }}</strong>
      </div>
      <label v-if="taskDrafts.length > 8" class="file-builder-search">
        <span>{{ t('reviewCases.composer.findFile') }}</span>
        <input
          v-model.trim="fileQuery"
          type="search"
          :placeholder="t('reviewCases.composer.findFilePlaceholder')"
        />
      </label>
      <article
        v-for="task in visibleTaskDrafts"
        :key="task.filename"
        class="file-task-draft"
        :class="{ selected: task.selected }"
      >
        <label class="file-selector">
          <input
            v-model="task.selected"
            type="checkbox"
            @change="selectTask(task)"
          />
          <span class="file-selector-box" aria-hidden="true">
            <font-awesome-icon icon="fa-solid fa-check" />
          </span>
          <span>
            <strong>{{ task.filename }}</strong>
            <small>{{
              task.selected
                ? t(
                    'reviewCases.composer.requestedChanges',
                    task.changes.length
                  )
                : t('reviewCases.composer.noCorrection')
            }}</small>
          </span>
        </label>
        <button
          v-if="task.selected && activeFilename !== task.filename"
          type="button"
          class="edit-file-changes"
          @click="activeFilename = task.filename"
        >
          {{ t('reviewCases.composer.editChanges') }}
        </button>
        <div
          v-if="task.selected && activeFilename === task.filename"
          class="change-request-list"
        >
          <article
            v-for="(change, changeIndex) in task.changes"
            :key="change.id"
            class="change-request-draft"
          >
            <header>
              <strong>{{
                t('reviewCases.composer.changeNumber', {
                  number: changeIndex + 1,
                })
              }}</strong>
              <button
                v-if="task.changes.length > 1"
                type="button"
                class="remove-change"
                :aria-label="
                  t('reviewCases.composer.removeChangeFor', {
                    number: changeIndex + 1,
                    filename: task.filename,
                  })
                "
                @click="removeTaskChange(task, change.id)"
              >
                <font-awesome-icon icon="fa-solid fa-trash" />
                {{ t('reviewCases.composer.remove') }}
              </button>
            </header>
            <label>
              <span>{{ t('reviewCases.composer.whatToCorrect') }}</span>
              <textarea
                v-model.trim="change.instruction"
                required
                maxlength="10000"
                :placeholder="t('reviewCases.composer.instructionPlaceholder')"
              ></textarea>
            </label>
            <div class="change-target-grid">
              <label>
                <span
                  >{{ t('reviewCases.composer.tier') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <input v-model.trim="change.tier_id" maxlength="255" />
              </label>
              <label>
                <span
                  >{{ t('reviewCases.composer.annotationId') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <input v-model.trim="change.annotation_id" maxlength="255" />
              </label>
              <label>
                <span
                  >{{ t('reviewCases.composer.startMs') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <input v-model.number="change.start_ms" type="number" min="0" />
              </label>
              <label>
                <span
                  >{{ t('reviewCases.composer.endMs') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <input v-model.number="change.end_ms" type="number" min="0" />
              </label>
            </div>
            <div class="text-suggestion">
              <label>
                <span
                  >{{ t('reviewCases.composer.currentText') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <textarea
                  v-model.trim="change.current_text"
                  maxlength="10000"
                ></textarea>
              </label>
              <span class="suggestion-arrow" aria-hidden="true">→</span>
              <label>
                <span
                  >{{ t('reviewCases.composer.suggestedReplacement') }}
                  <small>{{ t('reviewCases.composer.optional') }}</small></span
                >
                <textarea
                  v-model.trim="change.suggested_text"
                  maxlength="10000"
                ></textarea>
              </label>
            </div>
          </article>
          <button type="button" class="add-change" @click="addTaskChange(task)">
            <font-awesome-icon icon="fa-solid fa-plus" />
            {{ t('reviewCases.composer.addChange') }}
          </button>
        </div>
      </article>
      <div v-if="filePageCount > 1" class="file-builder-pagination">
        <button type="button" :disabled="filePage === 1" @click="filePage -= 1">
          {{ t('reviewCases.pagination.previous') }}
        </button>
        <span>{{
          t('reviewCases.pagination.pageOf', {
            page: filePage,
            count: filePageCount,
          })
        }}</span>
        <button
          type="button"
          :disabled="filePage === filePageCount"
          @click="filePage += 1"
        >
          {{ t('reviewCases.pagination.next') }}
        </button>
      </div>
    </fieldset>
    <div v-if="!requestChangesOnCreate" class="target-fields">
      <label>
        <span>{{ t('reviewCases.composer.tierOptional') }}</span>
        <input v-model.trim="draft.tier_id" maxlength="255" />
      </label>
      <label>
        <span>{{ t('reviewCases.composer.annotationOptional') }}</span>
        <input v-model.trim="draft.annotation_id" maxlength="255" />
      </label>
    </div>
    <div v-if="!requestChangesOnCreate" class="target-fields">
      <label>
        <span>{{ t('reviewCases.composer.startOptional') }}</span>
        <input v-model.number="draft.start_ms" type="number" min="0" />
      </label>
      <label>
        <span>{{ t('reviewCases.composer.endOptional') }}</span>
        <input v-model.number="draft.end_ms" type="number" min="0" />
      </label>
    </div>
    <label v-if="!requestChangesOnCreate">
      <span>{{
        requestChangesOnCreate
          ? t('reviewCases.composer.explainCorrection')
          : t('reviewCases.composer.explainCheck')
      }}</span>
      <textarea
        v-model.trim="draft.initial_comment"
        required
        maxlength="10000"
      ></textarea>
    </label>
    <div v-if="!requestChangesOnCreate" class="text-suggestion">
      <label>
        <span>{{ t('reviewCases.composer.currentOptional') }}</span>
        <textarea
          v-model.trim="draft.current_text"
          maxlength="10000"
        ></textarea>
      </label>
      <span class="suggestion-arrow" aria-hidden="true">→</span>
      <label>
        <span>{{ t('reviewCases.composer.suggestedOptional') }}</span>
        <textarea
          v-model.trim="draft.suggested_text"
          maxlength="10000"
        ></textarea>
      </label>
    </div>
    <div class="composer-actions">
      <button
        type="submit"
        class="primary"
        :disabled="busy || (requestChangesOnCreate && !hasSelectedTasks)"
      >
        {{
          requestChangesOnCreate
            ? t('reviewCases.composer.send')
            : t('reviewCases.composer.openQuestion')
        }}
      </button>
      <button type="button" @click="emit('cancel')">
        {{ t('reviewCases.composer.cancel') }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

import { useReviewCaseDraft } from '@/composables/useReviewCaseDraft';

const props = defineProps({
  filenames: { type: Array, default: () => [] },
  uploadId: { type: Number, default: null },
  requestChangesOnCreate: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  /** Values to start the draft with, such as an annotation to question. */
  initialTarget: { type: Object, default: () => ({}) },
});
const emit = defineEmits(['submit', 'cancel']);

const { t } = useI18n();
const {
  activeFilename,
  addTaskChange,
  buildPayload,
  draft,
  filePage,
  filePageCount,
  fileQuery,
  hasSelectedTasks,
  removeTaskChange,
  resetDraft,
  selectedFileCount,
  selectTask,
  taskDrafts,
  visibleTaskDrafts,
} = useReviewCaseDraft(props.filenames);

// Start from the target before the first render, so the form opens filled in.
Object.assign(draft, props.initialTarget);

function submit() {
  emit(
    'submit',
    buildPayload({
      uploadId: props.uploadId,
      requestChanges: props.requestChangesOnCreate,
    })
  );
}

defineExpose({ reset: resetDraft });
</script>
