<template>
  <section v-if="item.tasks?.length" class="file-task-list">
    <div class="file-task-heading">
      <div>
        <span>{{ t('reviewCases.tasks.requiredWork') }}</span>
        <h6>
          {{
            isFinished(item.state)
              ? t('reviewCases.tasks.filesIncluded')
              : item.state === 'resubmitted'
                ? t('reviewCases.tasks.editsToReview')
                : t('reviewCases.tasks.filesMarked')
          }}
        </h6>
      </div>
      <strong>
        {{
          isFinished(item.state)
            ? t('reviewCases.tasks.reviewClosed')
            : item.state === 'resubmitted'
              ? canManage
                ? t(
                    'reviewCases.tasks.decisionsRemaining',
                    unresolvedTaskCount(item)
                  )
                : t('reviewCases.tasks.awaitingDecision')
              : t('reviewCases.tasks.remaining', {
                  count: unresolvedTaskCount(item),
                })
        }}
      </strong>
    </div>
    <div v-if="item.tasks.length > 5" class="file-task-filters">
      <input
        v-model.trim="taskQuery"
        type="search"
        :placeholder="t('reviewCases.tasks.filterPlaceholder')"
        :aria-label="t('reviewCases.tasks.filterFiles')"
      />
      <AppSelect
        id="correction-task-status-filter"
        v-model="taskStatus"
        size="small"
        :aria-label="t('reviewCases.tasks.filterStatus')"
        :options="taskStatusOptions"
      />
    </div>
    <article
      v-for="task in visibleTasks(item)"
      :key="task.task_id"
      class="file-task"
    >
      <div>
        <strong>{{ task.filename }}</strong>
        <span
          v-if="
            !(
              item.state === 'resubmitted' &&
              !canManage &&
              task.status !== 'accepted'
            )
          "
          class="task-status"
          :class="`task-${task.status}`"
        >
          {{ formatTaskStatus(task.status, item) }}
        </span>
      </div>
      <p>{{ task.instruction }}</p>
      <div
        v-if="
          task.tier_id ||
          task.annotation_id ||
          task.start_ms != null ||
          task.end_ms != null
        "
        class="task-targets"
        :aria-label="t('reviewCases.tasks.location')"
      >
        <span v-if="task.tier_id">{{
          t('reviewCases.tasks.tierOf', { tier: task.tier_id })
        }}</span>
        <span v-if="task.annotation_id">{{
          t('reviewCases.tasks.annotationOf', {
            id: task.annotation_id,
          })
        }}</span>
        <span v-if="task.start_ms != null || task.end_ms != null">
          {{
            t('reviewCases.tasks.timeOf', {
              start: task.start_ms ?? t('reviewCases.tasks.start'),
              end: task.end_ms ?? t('reviewCases.tasks.end'),
            })
          }}
        </span>
      </div>
      <div
        v-if="task.current_text || task.suggested_text"
        class="task-text-suggestion"
      >
        <div v-if="task.current_text">
          <span>{{ t('reviewCases.tasks.currentText') }}</span>
          <p>{{ task.current_text }}</p>
        </div>
        <font-awesome-icon
          v-if="task.current_text && task.suggested_text"
          icon="fa-solid fa-arrow-right"
        />
        <div v-if="task.suggested_text">
          <span>{{ t('reviewCases.tasks.suggestedReplacement') }}</span>
          <p>{{ task.suggested_text }}</p>
        </div>
      </div>
      <button
        v-if="
          canComment &&
          projectName &&
          item.response_branch &&
          task.filename.endsWith('.eaf')
        "
        type="button"
        class="comparison-disclosure"
        :class="{ active: activeDiff === task.task_id }"
        :aria-expanded="activeDiff === task.task_id"
        :disabled="busy"
        @click="activeDiff = activeDiff === task.task_id ? '' : task.task_id"
      >
        <span class="comparison-disclosure-icon">
          <font-awesome-icon icon="fa-solid fa-eye" />
        </span>
        <span>
          <strong>{{
            activeDiff === task.task_id
              ? t('reviewCases.tasks.closeComparison')
              : t('reviewCases.tasks.reviewChanges')
          }}</strong>
          <small>{{ t('reviewCases.tasks.compareHelp') }}</small>
        </span>
        <font-awesome-icon
          class="comparison-chevron"
          :icon="
            activeDiff === task.task_id
              ? 'fa-solid fa-chevron-up'
              : 'fa-solid fa-chevron-down'
          "
        />
      </button>
      <ConflictMergeView
        v-if="activeDiff === task.task_id"
        :project-name="projectName"
        :branch-name="item.response_branch"
        :filename="task.filename"
        :allow-open-review="canManage && item.state === 'resubmitted'"
        :selected-annotation-ids="selectedAnnotationIds(item, task)"
        :review-action-label="t('reviewCases.tasks.addToRequest')"
        @open-review="selectRevisionTarget(item, task, $event)"
      />
      <div
        v-if="canComment && canManage && item.state === 'resubmitted'"
        class="task-decision"
      >
        <span>
          {{
            isTaskSelectedForRevision(item, task)
              ? t('reviewCases.tasks.requestDrafted')
              : t('reviewCases.tasks.decisionForFile')
          }}
        </span>
        <div class="task-actions">
          <button
            v-if="
              canManage &&
              task.status !== 'accepted' &&
              !isTaskSelectedForRevision(item, task)
            "
            type="button"
            class="task-action accept-action"
            :disabled="busy"
            @click="approveTask(item, task)"
          >
            <font-awesome-icon icon="fa-solid fa-circle-check" />
            {{ taskBusyLabel(task, 'accepted', approveTaskLabel(item)) }}
          </button>
          <button
            v-if="
              canManage &&
              ['addressed', 'accepted', 'reopened'].includes(task.status)
            "
            type="button"
            class="task-action reopen-action"
            :class="{
              selected: isTaskSelectedForRevision(item, task),
            }"
            :disabled="busy"
            @click="toggleTaskForRevision(item, task)"
          >
            <font-awesome-icon
              :icon="
                isTaskSelectedForRevision(item, task)
                  ? 'fa-solid fa-check'
                  : 'fa-solid fa-rotate-left'
              "
            />
            {{
              isTaskSelectedForRevision(item, task)
                ? t('reviewCases.tasks.cancelRequest')
                : t('reviewCases.tasks.requestAnother')
            }}
          </button>
        </div>
        <small
          v-if="
            unresolvedTaskCount(item) === 1 &&
            !isTaskSelectedForRevision(item, task)
          "
          class="task-decision-note"
        >
          {{ t('reviewCases.tasks.finalNote') }}
        </small>
      </div>
    </article>
    <button
      v-if="filteredTasks(item).length > visibleTaskLimit"
      type="button"
      class="load-more-tasks"
      @click="visibleTaskLimit += 20"
    >
      {{ t('reviewCases.tasks.showMore') }}
    </button>
  </section>
</template>

<script setup>
import AppSelect from '@/components/common/AppSelect.vue';
import ConflictMergeView from '@/components/common/ConflictMergeView.vue';
import { useReviewCaseContext } from './reviewCaseContext';

defineProps({
  item: { type: Object, required: true },
});

const {
  activeDiff,
  approveTask,
  approveTaskLabel,
  busy,
  canComment,
  canManage,
  filteredTasks,
  formatTaskStatus,
  isFinished,
  isTaskSelectedForRevision,
  projectName,
  selectRevisionTarget,
  selectedAnnotationIds,
  t,
  taskBusyLabel,
  taskQuery,
  taskStatus,
  taskStatusOptions,
  toggleTaskForRevision,
  unresolvedTaskCount,
  visibleTaskLimit,
  visibleTasks,
} = useReviewCaseContext();
</script>
