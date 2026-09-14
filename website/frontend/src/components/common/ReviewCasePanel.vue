<template>
  <section
    class="review-panel"
    :class="{ 'composer-only': composerOnly }"
    aria-labelledby="review-cases-title"
  >
    <header>
      <div>
        <span class="eyebrow">{{
          composerOnly ? 'New request' : 'Research review'
        }}</span>
        <h4 id="review-cases-title">
          {{ composerOnly ? 'Request a correction' : 'Correction requests' }}
        </h4>
        <p class="panel-description">
          {{
            composerOnly
              ? 'Describe what the researcher must correct before this contribution can be merged into the project.'
              : 'Track questions raised during review, requested changes, corrected uploads, and final decisions.'
          }}
        </p>
      </div>
      <button
        v-if="!composerOnly && allowCreate && uploadId"
        type="button"
        class="new-case"
        @click="showComposer = !showComposer"
      >
        <font-awesome-icon icon="fa-solid fa-plus" />
        Open review case
      </button>
    </header>

    <form
      v-if="showComposer || composerOnly"
      class="case-composer"
      @submit.prevent="createCase"
    >
      <label>
        <span>Short title</span>
        <input v-model.trim="draft.title" required maxlength="200" />
      </label>
      <fieldset v-if="filenames.length" class="file-task-builder">
        <legend>Select files and describe each requested change</legend>
        <div class="builder-introduction">
          <p class="builder-help">
            Select only files that need another revision. Add as many precise
            changes as needed inside each selected file.
          </p>
          <strong
            >{{ selectedFileCount }} of {{ taskDrafts.length }} selected</strong
          >
        </div>
        <label v-if="taskDrafts.length > 8" class="file-builder-search">
          <span>Find a file</span>
          <input
            v-model.trim="fileQuery"
            type="search"
            placeholder="Search by project-relative filename"
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
                  ? `${task.changes.length} requested change${task.changes.length === 1 ? '' : 's'}`
                  : 'No correction requested'
              }}</small>
            </span>
          </label>
          <button
            v-if="task.selected && activeFilename !== task.filename"
            type="button"
            class="edit-file-changes"
            @click="activeFilename = task.filename"
          >
            Edit requested changes
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
                <strong>Requested change {{ changeIndex + 1 }}</strong>
                <button
                  v-if="task.changes.length > 1"
                  type="button"
                  class="remove-change"
                  :aria-label="`Remove requested change ${changeIndex + 1} for ${task.filename}`"
                  @click="removeTaskChange(task, change.id)"
                >
                  <font-awesome-icon icon="fa-solid fa-trash" />
                  Remove
                </button>
              </header>
              <label>
                <span>What must be corrected?</span>
                <textarea
                  v-model.trim="change.instruction"
                  required
                  maxlength="10000"
                  placeholder="Give the researcher one concrete, verifiable instruction"
                ></textarea>
              </label>
              <div class="change-target-grid">
                <label>
                  <span>Tier <small>Optional</small></span>
                  <input v-model.trim="change.tier_id" maxlength="255" />
                </label>
                <label>
                  <span>Annotation ID <small>Optional</small></span>
                  <input v-model.trim="change.annotation_id" maxlength="255" />
                </label>
                <label>
                  <span>Start time (ms) <small>Optional</small></span>
                  <input
                    v-model.number="change.start_ms"
                    type="number"
                    min="0"
                  />
                </label>
                <label>
                  <span>End time (ms) <small>Optional</small></span>
                  <input v-model.number="change.end_ms" type="number" min="0" />
                </label>
              </div>
              <div class="text-suggestion">
                <label>
                  <span>Current text <small>Optional</small></span>
                  <textarea
                    v-model.trim="change.current_text"
                    maxlength="10000"
                  ></textarea>
                </label>
                <span class="suggestion-arrow" aria-hidden="true">→</span>
                <label>
                  <span>Suggested replacement <small>Optional</small></span>
                  <textarea
                    v-model.trim="change.suggested_text"
                    maxlength="10000"
                  ></textarea>
                </label>
              </div>
            </article>
            <button
              type="button"
              class="add-change"
              @click="addTaskChange(task)"
            >
              <font-awesome-icon icon="fa-solid fa-plus" />
              Add another change for this file
            </button>
          </div>
        </article>
        <div v-if="filePageCount > 1" class="file-builder-pagination">
          <button
            type="button"
            :disabled="filePage === 1"
            @click="filePage -= 1"
          >
            Previous
          </button>
          <span>Page {{ filePage }} of {{ filePageCount }}</span>
          <button
            type="button"
            :disabled="filePage === filePageCount"
            @click="filePage += 1"
          >
            Next
          </button>
        </div>
      </fieldset>
      <div v-if="!requestChangesOnCreate" class="target-fields">
        <label>
          <span>Tier (optional)</span>
          <input v-model.trim="draft.tier_id" maxlength="255" />
        </label>
        <label>
          <span>Annotation ID (optional)</span>
          <input v-model.trim="draft.annotation_id" maxlength="255" />
        </label>
      </div>
      <div v-if="!requestChangesOnCreate" class="target-fields">
        <label>
          <span>Start time in ms (optional)</span>
          <input v-model.number="draft.start_ms" type="number" min="0" />
        </label>
        <label>
          <span>End time in ms (optional)</span>
          <input v-model.number="draft.end_ms" type="number" min="0" />
        </label>
      </div>
      <label v-if="!requestChangesOnCreate">
        <span>{{
          requestChangesOnCreate
            ? 'Explain what must be corrected'
            : 'Explain what should be checked'
        }}</span>
        <textarea
          v-model.trim="draft.initial_comment"
          required
          maxlength="10000"
        ></textarea>
      </label>
      <div v-if="!requestChangesOnCreate" class="text-suggestion">
        <label>
          <span>Current text (optional)</span>
          <textarea
            v-model.trim="draft.current_text"
            maxlength="10000"
          ></textarea>
        </label>
        <span class="suggestion-arrow" aria-hidden="true">→</span>
        <label>
          <span>Suggested replacement (optional)</span>
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
            requestChangesOnCreate ? 'Send correction request' : 'Open question'
          }}
        </button>
        <button type="button" @click="cancelComposer">Cancel</button>
      </div>
    </form>

    <template v-if="!composerOnly">
      <ReviewQueueOverview
        v-model:query="reviewQuery"
        v-model:status="reviewStatus"
        :cases-count="cases.length"
        :active-count="activeCount"
        :changes-requested-count="changesRequestedCount"
        :resubmitted-count="resubmittedCount"
        :active-cases-count="activeCases.length"
        :closed-cases-count="closedCases.length"
        :upload-id="uploadId"
        :loading="loading"
        :error="error"
      />
      <div v-if="!loading && !error && activeCases.length" class="case-list">
        <div v-if="!visibleActiveCases.length" class="panel-state">
          No correction requests match these filters.
        </div>
        <article
          v-for="item in visibleActiveCases"
          :id="`review-${item.case_id}`"
          :key="item.case_id"
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
                  Unread activity
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
                  <small>Originally reviewed</small>
                  Contribution #{{ item.upload_id }}
                </span>
                <template v-if="item.resubmitted_upload_id">
                  <font-awesome-icon icon="fa-solid fa-arrow-right" />
                  <span class="current-contribution">
                    <small>Corrected version to review</small>
                    Contribution #{{ item.resubmitted_upload_id }}
                  </span>
                </template>
              </div>
            </div>
            <label
              v-if="canManage && !isFinished(item.state)"
              class="reviewer-field"
              :for="`review-lead-${item.case_id}`"
            >
              <span>Review lead</span>
              <AppSelect
                :id="`review-lead-${item.case_id}`"
                :model-value="item.assigned_to || ''"
                :aria-label="`Choose the reviewer responsible for ${item.title}`"
                title="The review lead follows the discussion, checks corrected uploads, and makes sure a final decision is recorded."
                :disabled="busy || membersLoading"
                placeholder="Select a review lead"
                :options="reviewLeadOptions"
                @change="assign(item, $event)"
              />
            </label>
          </div>

          <div
            v-if="item.current_text || item.suggested_text"
            class="suggestion-diff"
            aria-label="Requested text replacement"
          >
            <div v-if="item.current_text" class="diff-before">
              <span>Current</span>
              <p>{{ item.current_text }}</p>
            </div>
            <div v-if="item.suggested_text" class="diff-after">
              <span>Suggested</span>
              <p>{{ item.suggested_text }}</p>
            </div>
          </div>

          <section v-if="item.tasks?.length" class="file-task-list">
            <div class="file-task-heading">
              <div>
                <span>Required work</span>
                <h6>
                  {{
                    isFinished(item.state)
                      ? 'Files included in this review'
                      : item.state === 'resubmitted'
                        ? 'Requested edits to review'
                        : 'Files marked for correction'
                  }}
                </h6>
              </div>
              <strong>
                {{
                  isFinished(item.state)
                    ? 'Review closed'
                    : item.state === 'resubmitted'
                      ? canManage
                        ? unresolvedTaskCount(item) + ' decision remaining'
                        : 'Awaiting reviewer decision'
                      : unresolvedTaskCount(item) + ' remaining'
                }}
              </strong>
            </div>
            <div v-if="item.tasks.length > 5" class="file-task-filters">
              <input
                v-model.trim="taskQuery"
                type="search"
                placeholder="Filter by filename, tier, annotation, or instruction"
                aria-label="Filter correction files"
              />
              <AppSelect
                id="correction-task-status-filter"
                v-model="taskStatus"
                size="small"
                aria-label="Filter by task status"
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
                aria-label="Requested change location"
              >
                <span v-if="task.tier_id">Tier: {{ task.tier_id }}</span>
                <span v-if="task.annotation_id"
                  >Annotation: {{ task.annotation_id }}</span
                >
                <span v-if="task.start_ms != null || task.end_ms != null">
                  Time: {{ task.start_ms ?? 'start' }}–{{
                    task.end_ms ?? 'end'
                  }}
                  ms
                </span>
              </div>
              <div
                v-if="task.current_text || task.suggested_text"
                class="task-text-suggestion"
              >
                <div v-if="task.current_text">
                  <span>Current text</span>
                  <p>{{ task.current_text }}</p>
                </div>
                <font-awesome-icon
                  v-if="task.current_text && task.suggested_text"
                  icon="fa-solid fa-arrow-right"
                />
                <div v-if="task.suggested_text">
                  <span>Suggested replacement</span>
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
                @click="
                  activeDiff = activeDiff === task.task_id ? '' : task.task_id
                "
              >
                <span class="comparison-disclosure-icon">
                  <font-awesome-icon icon="fa-solid fa-eye" />
                </span>
                <span>
                  <strong>{{
                    activeDiff === task.task_id
                      ? 'Close annotation comparison'
                      : 'Review annotation changes'
                  }}</strong>
                  <small>Compare accepted and submitted ELAN annotations</small>
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
                review-action-label="Add to correction request"
                @open-review="selectRevisionTarget(item, task, $event)"
              />
              <div
                v-if="canComment && canManage && item.state === 'resubmitted'"
                class="task-decision"
              >
                <span>
                  {{
                    isTaskSelectedForRevision(item, task)
                      ? 'Correction request drafted'
                      : 'Decision for this file'
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
                    {{
                      taskBusyLabel(task, 'accepted', approveTaskLabel(item))
                    }}
                  </button>
                  <button
                    v-if="
                      canManage &&
                      ['addressed', 'accepted', 'reopened'].includes(
                        task.status
                      )
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
                        ? 'Cancel correction request'
                        : 'Request another revision'
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
                  Approving this final correction closes the review. Merging the
                  contribution remains a separate decision.
                </small>
              </div>
            </article>
            <button
              v-if="filteredTasks(item).length > visibleTaskLimit"
              type="button"
              class="load-more-tasks"
              @click="visibleTaskLimit += 20"
            >
              Show 20 more requested edits
            </button>
          </section>

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
                  Open archived review
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
                aria-label="Selected annotation corrections"
              >
                <div class="revision-targets-heading">
                  <strong>Selected corrections</strong>
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
                      <span>{{ target.tier_id || 'Unknown tier' }}</span>
                    </div>
                    <button
                      type="button"
                      aria-label="Remove annotation from correction request"
                      @click="removeRevisionTarget(item, target)"
                    >
                      <font-awesome-icon icon="fa-solid fa-xmark" />
                    </button>
                  </div>
                  <span class="revision-target-location">
                    {{ revisionTargetSummary(target) }}
                  </span>
                  <label>
                    <span>Instruction for this annotation (optional)</span>
                    <input
                      v-model.trim="target.comment"
                      maxlength="1000"
                      placeholder="Add a specific correction or suggested wording"
                    />
                  </label>
                </article>
              </section>
              <label class="revision-general-note">
                <span>
                  {{
                    revisionTargets[item.case_id]?.length
                      ? 'Note for the whole revision (optional)'
                      : 'Correction instructions'
                  }}
                </span>
                <textarea
                  v-model.trim="replies[item.case_id]"
                  maxlength="10000"
                  :required="!revisionTargets[item.case_id]?.length"
                  placeholder="Add guidance that applies to every selected correction"
                ></textarea>
              </label>
            </div>
            <div
              v-if="canManage && !isFinished(item.state)"
              class="case-actions"
            >
              <router-link
                v-if="
                  item.state === 'changes_requested' &&
                  canActAsContributor(item)
                "
                class="correct-upload-link"
                :to="{
                  name: 'UploadPage',
                  query: { project: projectId, correction: item.case_id },
                }"
              >
                <font-awesome-icon icon="fa-solid fa-cloud-arrow-up" />
                Upload corrected files
              </router-link>
              <button
                v-if="item.state === 'open'"
                type="button"
                :disabled="busy || !item.assigned_to"
                @click="transition(item, 'changes_requested')"
              >
                Request first revision
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
                    ? `Send revision request (${revisionRequestCount(item)})`
                    : 'Add feedback and continue'
                }}
              </button>
              <button
                v-if="
                  item.state === 'resubmitted' &&
                  unresolvedTaskCount(item) === 0
                "
                class="resolve-case"
                type="button"
                :disabled="busy || !item.assigned_to"
                @click="transition(item, 'resolved')"
              >
                <font-awesome-icon icon="fa-solid fa-circle-check" />
                Approve correction and close review
              </button>
              <button
                v-if="item.state === 'open'"
                class="resolve-case"
                type="button"
                :disabled="busy || !item.assigned_to"
                @click="transition(item, 'resolved')"
              >
                Close without changes
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
              Reopen review
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
              Upload corrected files
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
              Link this corrected upload
            </button>
          </div>

          <ol v-if="item.comments.length" class="discussion">
            <li v-for="comment in item.comments" :key="comment.comment_id">
              <div>
                <strong>{{ comment.author_name }}</strong
                ><time>{{ formatDate(comment.created_at) }}</time>
              </div>
              <p>{{ comment.body }}</p>
            </li>
          </ol>
          <form
            v-if="
              canComment &&
              !isFinished(item.state) &&
              revisionFeedbackCaseId !== item.case_id
            "
            class="reply"
            @submit.prevent="addComment(item)"
          >
            <label :for="`reply-${item.case_id}`">Add to the discussion</label>
            <div>
              <input
                :id="`reply-${item.case_id}`"
                v-model.trim="replies[item.case_id]"
                required
                maxlength="10000"
                placeholder="Write a clear, research-focused comment"
              />
              <button type="submit" :disabled="busy">Comment</button>
            </div>
          </form>
        </article>
        <div v-if="reviewPageCount > 1" class="review-pagination">
          <button
            type="button"
            :disabled="reviewPage === 1"
            @click="reviewPage -= 1"
          >
            Previous
          </button>
          <span>Page {{ reviewPage }} of {{ reviewPageCount }}</span>
          <button
            type="button"
            :disabled="reviewPage === reviewPageCount"
            @click="reviewPage += 1"
          >
            Next
          </button>
        </div>
      </div>
      <button
        v-if="closedCases.length"
        id="closed-review-history"
        type="button"
        class="closed-history-toggle"
        :aria-expanded="showClosedCases"
        @click="showClosedCases = !showClosedCases"
      >
        <span class="closed-history-icon">
          <font-awesome-icon icon="fa-solid fa-box-archive" />
        </span>
        <span class="closed-history-copy">
          <strong>Archived review history</strong>
          <small>Browse completed decisions and their discussions</small>
        </span>
        <span class="closed-history-count">{{ closedCases.length }}</span>
        <font-awesome-icon
          class="closed-history-chevron"
          :icon="
            showClosedCases
              ? 'fa-solid fa-chevron-up'
              : 'fa-solid fa-chevron-down'
          "
        />
      </button>
      <ArchivedReviewList
        v-if="showClosedCases && closedCases.length"
        :cases="closedCases"
        :highlighted-case-id="highlightedCaseId"
      />
    </template>
  </section>
</template>

<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from 'vue';
import reviewService from '@/api/service/reviewService';
import ConflictMergeView from '@/components/common/ConflictMergeView.vue';
import ArchivedReviewList from '@/components/common/ArchivedReviewList.vue';
import AppSelect from '@/components/common/AppSelect.vue';
import ReviewQueueOverview from '@/components/pageSpecific/contributions/ReviewQueueOverview.vue';
import { getProjectUsers } from '@/api/service/projectAssociationService';
import { useReviewCaseQueue } from '@/composables/useReviewCaseQueue';
import { useReviewCaseDraft } from '@/composables/useReviewCaseDraft';
import { useReviewerTaskDecisions } from '@/composables/useReviewerTaskDecisions';
import { useReviewCaseTransitions } from '@/composables/useReviewCaseTransitions';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage.js';

const props = defineProps({
  projectId: { type: Number, required: true },
  projectName: { type: String, default: '' },
  uploadId: { type: Number, default: null },
  filenames: { type: Array, default: () => [] },
  allowCreate: { type: Boolean, default: true },
  canManage: { type: Boolean, default: true },
  canComment: { type: Boolean, default: true },
  currentUserId: { type: Number, default: null },
  highlightedCaseId: { type: String, default: '' },
  resubmissionUploadId: { type: Number, default: null },
  composerOnly: { type: Boolean, default: false },
  requestChangesOnCreate: { type: Boolean, default: false },
});
const emit = defineEmits(['created', 'cancel', 'count-change']);
const confirmAction = useUserConfirm();
const eventMessages = useEventMessageStore();
const cases = ref([]);
const {
  query: reviewQuery,
  status: reviewStatus,
  page: reviewPage,
  pageCount: reviewPageCount,
  activeCases,
  closedCases,
  visibleActiveCases,
  activeCount,
  changesRequestedCount,
  resubmittedCount,
  isFinished,
} = useReviewCaseQueue(cases);
const replies = reactive({});
const loading = ref(true);
const busy = ref(false);
const error = ref('');
const activeDiff = ref('');
const taskQuery = ref('');
const taskStatus = ref('');
const showComposer = ref(false);
const showClosedCases = ref(false);
const visibleTaskLimit = ref(20);
const members = ref([]);
const membersLoading = ref(false);
const taskStatusOptions = [
  { value: '', label: 'All statuses' },
  { value: 'requested', label: 'Needs change' },
  { value: 'reopened', label: 'Needs another change' },
  { value: 'addressed', label: 'Marked done' },
  { value: 'accepted', label: 'Accepted' },
];
const reviewLeadOptions = computed(() =>
  members.value.map((member) => ({
    value: member.user_id,
    label: memberDisplayName(member),
  }))
);
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
watch(
  [closedCases, () => props.highlightedCaseId],
  ([archived, highlightedCaseId]) => {
    if (archived.some((item) => item.case_id === highlightedCaseId)) {
      showClosedCases.value = true;
    }
  },
  { immediate: true }
);
const canActAsContributor = (item) =>
  Number.isInteger(props.currentUserId) &&
  item.contributor_id === props.currentUserId;

const formatState = (state) => state.replaceAll('_', ' ');
const formatTaskStatus = (status, item = null) => {
  if (item?.state === 'resubmitted' && status !== 'accepted') {
    return props.canManage ? 'Decision needed' : 'In review';
  }
  return (
    {
      requested: 'Needs change',
      reopened: 'Needs another change',
      addressed: 'Submitted for review',
      accepted: 'Approved',
    }[status] || status
  );
};
const {
  approveTask,
  approveTaskLabel,
  clearRevisionDraft,
  isTaskSelectedForRevision,
  removeRevisionTarget,
  revisionFeedbackCaseId,
  revisionTargets,
  revisionTargetSummary,
  selectedAnnotationIds,
  selectedRevisionTaskIds,
  selectRevisionTarget,
  taskBusyLabel,
  toggleTaskForRevision,
  unresolvedTaskCount,
} = useReviewerTaskDecisions({
  projectId: () => props.projectId,
  reviewService,
  busy,
  error,
  replaceCase,
  notify: (message, type) => eventMessages.addMessage(message, type),
});
const {
  assign,
  beginOrRequestAnotherRevision,
  hasRevisionFeedback,
  linkResubmission,
  revisionRequestCount,
  transition,
} = useReviewCaseTransitions({
  projectId: () => props.projectId,
  resubmissionUploadId: () => props.resubmissionUploadId,
  reviewService,
  busy,
  error,
  replies,
  revisionFeedbackCaseId,
  revisionTargets,
  selectedRevisionTaskIds,
  revisionTargetSummary,
  clearRevisionDraft,
  replaceCase,
  confirmAction,
  notify: (message, type) => eventMessages.addMessage(message, type),
});
async function openReviewArchive() {
  showClosedCases.value = true;
  await nextTick();
  document.getElementById('review-archive')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  });
}
function filteredTasks(item) {
  const needle = taskQuery.value.toLocaleLowerCase();
  return item.tasks.filter((task) => {
    const searchable = [
      task.filename,
      task.tier_id,
      task.annotation_id,
      task.instruction,
    ]
      .filter(Boolean)
      .join(' ')
      .toLocaleLowerCase();
    return (
      (!needle || searchable.includes(needle)) &&
      (!taskStatus.value || task.status === taskStatus.value)
    );
  });
}
const visibleTasks = (item) =>
  filteredTasks(item).slice(0, visibleTaskLimit.value);
const showNextStep = (item) =>
  !(props.canManage && item.state === 'resubmitted') ||
  selectedRevisionTaskIds(item).length > 0;
const nextStepDescription = (state, item) =>
  ({
    open: 'Discuss the question, then either ask for a corrected upload or finish the review.',
    changes_requested:
      'The contributor must revise the ELAN file and submit a corrected version.',
    resubmitted: props.canManage
      ? revisionFeedbackCaseId.value === item.case_id
        ? revisionTargets[item.case_id]?.length
          ? 'Review the selected annotations and add a note only when more context is needed.'
          : 'Explain precisely what still needs to change before sending the request.'
        : `Draft only — nothing has been sent. ${selectedRevisionTaskIds(item).length} edit${selectedRevisionTaskIds(item).length === 1 ? '' : 's'} will be included if you continue.`
      : `Your corrected contribution #${item.resubmitted_upload_id} was sent to the review lead. You can follow the decision and discussion here.`,
    resolved:
      'No further action is required. Reopen the review if this decision was premature.',
    closed: 'This review is closed. Its discussion remains preserved below.',
  })[state] || 'Continue the research review.';
const nextStepTitle = (state, item) =>
  ({
    open: 'Decide the next step',
    changes_requested: 'Waiting for corrected files',
    resubmitted: props.canManage
      ? revisionFeedbackCaseId.value === item.case_id
        ? 'Request another revision'
        : 'Correction request not sent'
      : 'Corrected version submitted',
    resolved: 'Review resolved',
    closed: 'Review closed',
  })[state] || 'Review in progress';
const nextStepIcon = (state) =>
  ({
    open: 'fa-solid fa-circle-question',
    changes_requested: 'fa-solid fa-clock',
    resubmitted: 'fa-solid fa-rotate',
    resolved: 'fa-solid fa-circle-check',
    closed: 'fa-solid fa-box-archive',
  })[state] || 'fa-solid fa-circle-info';
const formatDate = (value) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));

async function loadCases(showLoading = true) {
  if (showLoading) loading.value = true;
  error.value = '';
  try {
    cases.value = await reviewService.list(props.projectId, props.uploadId);
    if (props.highlightedCaseId) {
      const selected = cases.value.find(
        (item) => item.case_id === props.highlightedCaseId && item.unread
      );
      if (selected)
        replaceCase(
          await reviewService.markViewed(props.projectId, selected.case_id)
        );
    }
    emit('count-change', activeCount.value);
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'Review cases could not be loaded.';
  } finally {
    if (showLoading) loading.value = false;
  }
}
async function loadMembers() {
  if (!props.canManage) return;
  membersLoading.value = true;
  try {
    const { data } = await getProjectUsers(props.projectId);
    members.value = Array.isArray(data?.users)
      ? data.users.filter((member) => Number.isInteger(member?.user_id))
      : [];
  } catch {
    members.value = [];
  } finally {
    membersLoading.value = false;
  }
}
async function createCase() {
  busy.value = true;
  error.value = '';
  try {
    const created = await reviewService.create(
      props.projectId,
      buildPayload({
        uploadId: props.uploadId,
        requestChanges: props.requestChangesOnCreate,
      })
    );
    cases.value.unshift(created);
    resetDraft();
    showComposer.value = false;
    emit('created', created);
    emit('count-change', activeCount.value);
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The review case could not be created.';
  } finally {
    busy.value = false;
  }
}
async function addComment(item) {
  const body = replies[item.case_id];
  if (!body) return;
  busy.value = true;
  try {
    const updated = await reviewService.comment(
      props.projectId,
      item.case_id,
      body
    );
    replaceCase(updated);
    replies[item.case_id] = '';
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail || 'The comment could not be added.';
  } finally {
    busy.value = false;
  }
}
function memberDisplayName(member) {
  const fullName = [member.first_name, member.last_name]
    .filter(Boolean)
    .join(' ');
  return (
    fullName || member.username || member.email || 'Unnamed project member'
  );
}
function cancelComposer() {
  showComposer.value = false;
  emit('cancel');
}
function openComposer(target = {}) {
  resetDraft();
  Object.assign(draft, target);
  showComposer.value = true;
}
function replaceCase(updated) {
  const index = cases.value.findIndex(
    (item) => item.case_id === updated.case_id
  );
  if (index !== -1) cases.value[index] = updated;
  emit('count-change', activeCount.value);
}
let refreshInterval = null;
function refreshWhenVisible() {
  if (document.visibilityState === 'visible') void loadCases(false);
}
onMounted(() => {
  refreshInterval = window.setInterval(refreshWhenVisible, 15_000);
  document.addEventListener('visibilitychange', refreshWhenVisible);
  return Promise.all([loadCases(), loadMembers()]);
});
onUnmounted(() => {
  if (refreshInterval) window.clearInterval(refreshInterval);
  document.removeEventListener('visibilitychange', refreshWhenVisible);
});
watch(
  () => [props.projectId, props.uploadId],
  () => Promise.all([loadCases(), loadMembers()])
);
defineExpose({ openComposer });
</script>

<style scoped>
.review-panel {
  display: grid;
  gap: 1rem;
  margin-block: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.case-card.highlighted {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px
    color-mix(in srgb, var(--primary-color) 14%, transparent);
}

.review-panel > header,
.case-heading,
.composer-actions,
.reply > div {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

h4,
h5,
p {
  margin: 0;
}

h5 {
  margin-top: 0.65rem;
  font-size: 1rem;
}

.eyebrow {
  color: var(--primary-color);
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.panel-description {
  max-width: 48rem;
  margin-top: 0.25rem;
  color: var(--color-text-muted);
  font-size: 0.86rem;
}

.case-flags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.contribution-lineage {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  align-items: center;
  margin-top: 0.75rem;
}

.contribution-lineage > span {
  display: grid;
  gap: 0.1rem;
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  background: var(--color-surface-subtle);
  font-size: 0.8rem;
  font-weight: 700;
}

.contribution-lineage small {
  color: var(--color-text-muted);
  font-size: 0.68rem;
  font-weight: 600;
}

.contribution-lineage > svg {
  color: var(--color-text-muted);
}

.contribution-lineage .current-contribution {
  border-color: #bfdbfe;
  color: #1d4ed8;
  background: #eff6ff;
}

.review-panel.composer-only {
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

button {
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  background: var(--color-surface);
  cursor: pointer;
}

button.primary,
button.new-case {
  color: white;
  border-color: var(--primary-color);
  background: var(--primary-color);
}

button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.case-composer,
.case-composer label {
  display: grid;
  gap: 0.7rem;
}

.case-composer {
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
}

.case-composer label {
  gap: 0.3rem;
  color: var(--color-text-muted);
  font-size: 0.85rem;
  font-weight: 700;
}

input,
select,
textarea {
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text);
  background: white;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 400;
}

textarea {
  min-height: 6rem;
  resize: vertical;
}

.case-list {
  display: grid;
  gap: 0.8rem;
}

.review-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.closed-history-toggle {
  width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border-color: #cbd5e1;
  color: var(--color-text);
  background: white;
  text-align: left;
}

.closed-history-toggle:hover {
  color: var(--color-text);
  border-color: #94a3b8;
  background: #f8fafc;
}

.closed-history-icon {
  width: 2.25rem;
  height: 2.25rem;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #475569;
  background: #eef2f7;
}

.closed-history-copy {
  min-width: 0;
  display: grid;
  gap: 0.1rem;
}

.closed-history-copy small {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.closed-history-count {
  min-width: 1.7rem;
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  color: #334155;
  background: #e2e8f0;
  font-size: 0.75rem;
  font-weight: 800;
  text-align: center;
}

.closed-history-chevron {
  color: #64748b;
}

.case-card {
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: white;
}

.case-heading {
  padding: 1rem;
}

.case-identity {
  min-width: 0;
}

.reviewer-field {
  width: min(16rem, 100%);
  display: grid;
  flex: none;
  gap: 0.3rem;
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.reviewer-field small {
  font-weight: 500;
}

.reviewer-field select {
  min-height: 2.5rem;
  background: white;
}

.case-next-step {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  border-block: 1px solid var(--color-border);
  background: #f7f9fc;
}

.next-step-copy {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.next-step-copy > svg {
  flex: none;
  color: var(--primary-color);
}

.next-step-copy strong,
.next-step-copy span {
  display: block;
}

.next-step-copy span {
  margin-top: 0.15rem;
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.next-step-link {
  margin-top: 0.35rem;
  padding: 0;
  border: 0;
  color: var(--primary-color);
  background: transparent;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  text-decoration: underline;
  cursor: pointer;
}

.case-next-step.next-changes_requested {
  background: #fffbeb;
}

.case-next-step.next-resubmitted {
  display: grid;
  grid-template-columns: minmax(15rem, 1fr) auto;
  align-items: end;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.case-next-step.next-resubmitted.feedback-open {
  grid-template-columns: 1fr;
  align-items: stretch;
  gap: 0.85rem;
  padding: 1rem 1.15rem 1.1rem;
}

.feedback-open .next-step-copy {
  grid-column: 1 / -1;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid #bfdbfe;
}

.feedback-open .next-step-copy > svg {
  width: 2rem;
  height: 2rem;
  padding: 0.55rem;
  border-radius: 50%;
  background: white;
}

.revision-feedback {
  display: grid;
  gap: 0.85rem;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  font-weight: 700;
}

.revision-general-note {
  display: grid;
  gap: 0.35rem;
}

.revision-general-note textarea {
  width: 100%;
  min-height: 3.75rem;
  background: white;
}

.revision-targets {
  overflow: hidden;
  border: 1px solid #bfdbfe;
  border-radius: var(--radius-md);
  background: white;
}

.revision-targets-heading,
.revision-target-identity {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.revision-targets-heading {
  padding: 0.65rem 0.75rem;
  color: var(--color-text);
  background: #f8fafc;
}

.revision-targets-heading > span {
  min-width: 1.5rem;
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
  color: #1e40af;
  background: #dbeafe;
  text-align: center;
}

.revision-target {
  display: grid;
  gap: 0.45rem;
  padding: 0.75rem;
  border-top: 1px solid #e2e8f0;
}

.revision-target-identity > div {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.revision-target-identity strong {
  color: var(--primary-color);
}

.revision-target-identity button {
  width: 1.8rem;
  height: 1.8rem;
  display: grid;
  place-items: center;
  padding: 0;
  border-color: transparent;
  color: #64748b;
  background: transparent;
}

.revision-target-location {
  font-family: monospace;
  font-size: 0.7rem;
  font-weight: 500;
}

.revision-target label {
  display: grid;
  gap: 0.25rem;
}

.revision-target input {
  width: 100%;
  background: white;
}

.feedback-open .case-actions {
  justify-content: flex-end;
  padding-top: 0.85rem;
  border-top: 1px solid #bfdbfe;
}

.feedback-open .request-another-revision {
  min-height: 2.75rem;
  padding-inline: 1rem;
  white-space: nowrap;
}

.case-next-step.next-resolved,
.case-next-step.next-closed {
  background: #f0fdf4;
}

.case-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.case-actions button {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.5rem;
  font-weight: 700;
}

.case-actions .resolve-case {
  border-color: #15803d;
  color: white;
  background: #15803d;
}

.case-actions .request-another-revision {
  border-color: #b45309;
  color: #92400e;
  background: #fffbeb;
}

.reopen-case {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-color: var(--primary-color);
  color: var(--primary-color);
  font-weight: 700;
}

.correct-upload-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--primary-color);
  border-radius: var(--radius-sm);
  color: var(--primary-color);
  background: white;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
}

.correct-upload-link:hover {
  color: white;
  background: var(--primary-color);
}

.state-badge {
  display: inline-flex;
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  color: #1e40af;
  background: #dbeafe;
  font-size: 0.72rem;
  font-weight: 750;
  text-transform: capitalize;
}

.state-changes_requested {
  color: #92400e;
  background: #fef3c7;
}

.state-resolved,
.state-closed {
  color: #166534;
  background: #dcfce7;
}

.target {
  margin-top: 0.25rem;
  color: var(--color-text-muted);
  font-size: 0.83rem;
}

.target-fields,
.text-suggestion {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.text-suggestion {
  position: relative;
}

.suggestion-arrow {
  position: absolute;
  top: 2.5rem;
  left: 50%;
  z-index: 1;
  display: grid;
  width: 1.6rem;
  height: 1.6rem;
  place-items: center;
  border-radius: 999px;
  color: var(--primary-color);
  background: white;
  transform: translateX(-50%);
}

.activity-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
  color: #fff;
  background: #7c3aed;
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
}

.activity-badge svg {
  width: 0.4rem;
}

.suggestion-diff {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 1rem;
}

.suggestion-diff > div {
  padding: 0.7rem;
  border-radius: var(--radius-sm);
}

.suggestion-diff span {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
}

.suggestion-diff p {
  margin: 0.35rem 0 0;
  white-space: pre-wrap;
}

.diff-before {
  color: #991b1b;
  background: #fef2f2;
}

.diff-after {
  color: #166534;
  background: #f0fdf4;
}

.file-task-builder,
.file-task-list {
  display: grid;
  gap: 0.65rem;
  padding: 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.builder-help {
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.builder-introduction {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.builder-introduction > strong {
  flex: none;
  color: var(--primary-color);
  font-size: 0.75rem;
}

.file-task-draft {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #fff;
}

.file-task-draft.selected {
  border-color: #93c5fd;
  box-shadow: 0 0 0 2px rgb(37 99 235 / 8%);
}

.file-selector {
  display: flex !important;
  align-items: center;
  gap: 0.7rem !important;
  padding: 0.75rem;
  color: var(--color-text) !important;
  cursor: pointer;
}

.file-selector > input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.file-selector-box {
  width: 1.45rem;
  height: 1.45rem;
  flex: none;
  display: grid;
  place-items: center;
  border: 1px solid #94a3b8;
  border-radius: 0.35rem;
  color: transparent;
  background: #fff;
}

.file-selector input:checked + .file-selector-box {
  border-color: var(--primary-color);
  color: #fff;
  background: var(--primary-color);
}

.file-selector input:focus-visible + .file-selector-box {
  outline: 3px solid rgb(37 99 235 / 20%);
}

.file-selector > span:last-child {
  min-width: 0;
  display: grid;
  gap: 0.15rem;
}

.file-selector strong {
  overflow-wrap: anywhere;
}

.file-selector small {
  color: var(--color-text-muted);
  font-weight: 500;
}

.change-request-list {
  display: grid;
  gap: 0.75rem;
  padding: 0.75rem;
  border-top: 1px solid #dbeafe;
  background: #f8fbff;
}

.change-request-draft {
  display: grid;
  gap: 0.75rem;
  padding: 0.8rem;
  border: 1px solid #dbe5f1;
  border-radius: var(--radius-sm);
  background: #fff;
}

.change-request-draft > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.change-request-draft textarea {
  min-height: 4.5rem;
}

.change-target-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.change-target-grid label span,
.text-suggestion label span {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.5rem;
}

.change-target-grid small,
.text-suggestion label small {
  font-size: 0.68rem;
  font-weight: 500;
}

button.add-change {
  justify-self: start;
  border-color: #93c5fd;
  color: #1d4ed8;
  background: #fff;
  font-weight: 700;
}

.file-builder-search {
  padding: 0.7rem;
  border-radius: var(--radius-sm);
  background: var(--color-surface-subtle);
}

button.edit-file-changes {
  width: calc(100% - 1.5rem);
  margin: 0 0.75rem 0.75rem;
  border-color: #bfdbfe;
  color: #1d4ed8;
  background: #eff6ff;
  font-weight: 700;
}

.file-builder-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

button.load-more-tasks {
  justify-self: center;
  border-color: #bfdbfe;
  color: #1d4ed8;
  background: #eff6ff;
  font-weight: 700;
}

button.remove-change {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.5rem;
  border-color: #fecaca;
  color: #b91c1c;
  font-size: 0.72rem;
}

.file-task-list {
  margin: 1rem;
  padding: 1rem;
  border-color: #cbd5e1;
  background: #f8fafc;
}

.file-task-list h6 {
  margin: 0;
  font-size: 1rem;
}

.file-task-heading,
.file-task-heading > div {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}

.file-task-heading > div {
  align-items: flex-start;
  flex-direction: column;
}

.file-task-heading span {
  color: #b45309;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.file-task-heading > strong {
  align-self: center;
  padding: 0.3rem 0.55rem;
  border-radius: 999px;
  color: #92400e;
  background: #fef3c7;
  font-size: 0.72rem;
}

.file-task-filters {
  display: grid;
  grid-template-columns: minmax(12rem, 1fr) minmax(9rem, auto);
  gap: 0.55rem;
}

.file-task-filters input,
.file-task-filters select {
  min-width: 0;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--color-border);
  border-radius: 0.45rem;
  color: var(--color-text);
  background: white;
  font: inherit;
}

@media (width <= 700px) {
  .file-task-filters {
    grid-template-columns: 1fr;
  }
}

.file-task {
  display: grid;
  gap: 0.7rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-left: 4px solid #f59e0b;
  border-radius: var(--radius-sm);
  background: white;
}

.file-task > div:first-child {
  display: flex;
  justify-content: space-between;
}

.task-targets {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.task-targets span {
  padding: 0.25rem 0.45rem;
  border-radius: 999px;
  color: #334155;
  background: #eef2f7;
  font-size: 0.72rem;
  font-weight: 700;
}

.task-text-suggestion {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 0.6rem;
}

.task-text-suggestion > div {
  min-width: 0;
  padding: 0.6rem;
  border-radius: var(--radius-sm);
  background: #f8fafc;
}

.task-text-suggestion span {
  color: var(--color-text-muted);
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
}

.task-text-suggestion p {
  margin-top: 0.25rem;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.task-text-suggestion > svg {
  color: var(--primary-color);
}

.task-status {
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  color: #92400e;
  background: #fef3c7;
  font-size: 0.68rem;
  font-weight: 800;
}

.task-addressed {
  color: #1e40af;
  background: #dbeafe;
}

.task-accepted {
  color: #166534;
  background: #dcfce7;
}

.file-task p {
  margin: 0;
  white-space: pre-wrap;
}

.task-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.35rem;
}

.task-decision {
  display: grid;
  grid-template-columns: minmax(7rem, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.15rem;
  padding-top: 0.7rem;
  border-top: 1px solid #e2e8f0;
}

.task-decision > span {
  color: var(--color-text-muted);
  font-size: 0.76rem;
  font-weight: 700;
}

.task-decision-note {
  grid-column: 1 / -1;
  color: var(--color-text-muted);
  font-size: 0.75rem;
  line-height: 1.45;
  text-align: right;
}

.task-action {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 2.4rem;
  font-weight: 750;
  transition:
    color 150ms ease,
    border-color 150ms ease,
    background 150ms ease,
    transform 150ms ease;
}

.task-action:hover:not(:disabled) {
  transform: translateY(-1px);
}

.task-action:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--primary-color) 28%, transparent);
  outline-offset: 2px;
}

.comparison-disclosure {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  margin-top: 0.35rem;
  padding: 0.75rem 0.85rem;
  border: 1px solid #cbd9eb;
  border-radius: 0.55rem;
  color: #1e3a8a;
  background: white;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 150ms ease,
    background 150ms ease,
    box-shadow 150ms ease;
}

.comparison-disclosure:hover:not(:disabled) {
  border-color: #60a5fa;
  background: #f8fbff;
}

.comparison-disclosure:focus-visible {
  outline: 3px solid rgb(37 99 235 / 22%);
  outline-offset: 2px;
}

.comparison-disclosure.active {
  border-color: #60a5fa;
  background: #f0f7ff;
}

.comparison-disclosure > span:nth-child(2) {
  display: grid;
  gap: 0.15rem;
}

.comparison-disclosure small {
  color: #526987;
  font-weight: 500;
}

.comparison-disclosure-icon {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid #bfdbfe;
  border-radius: 50%;
  color: #2563eb;
  background: #eff6ff;
}

.comparison-chevron {
  color: #2563eb;
}

@media (width <= 700px) {
  .file-task-list {
    margin: 0.75rem;
    padding: 0.75rem;
  }

  .file-task {
    padding: 0.8rem;
  }

  .file-task > div:first-child {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.45rem;
  }

  .comparison-disclosure {
    gap: 0.6rem;
    padding: 0.7rem;
  }

  .task-decision {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .task-decision-note {
    grid-column: auto;
    text-align: left;
  }

  .task-actions {
    justify-content: stretch;
  }

  .task-action {
    justify-content: center;
    flex: 1;
  }
}

.addressed-action,
.accept-action {
  border-color: #6fc58d;
  color: #166534;
  background: #f3fbf6;
}

.accept-action:hover:not(:disabled) {
  border-color: #249052;
  background: #e8f7ee;
}

.accept-action {
  color: white;
  border-color: #15803d;
  background: #15803d;
}

.reopen-action {
  border-color: #fcd34d;
  color: #92400e;
  background: #fffbeb;
}

.reopen-action.selected {
  border-color: #b45309;
  color: white;
  background: #b45309;
}

.discussion {
  display: grid;
  gap: 0.6rem;
  margin: 1rem;
  padding: 0;
  list-style: none;
}

.discussion li {
  padding: 0.75rem;
  border-left: 3px solid color-mix(in srgb, var(--primary-color) 45%, white);
  background: var(--color-surface-subtle);
}

.discussion li > div {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.discussion time {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.discussion p {
  margin-top: 0.3rem;
  white-space: pre-wrap;
}

.reply {
  display: grid;
  gap: 0.3rem;
  margin: 1rem;
}

.reply label {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 700;
}

.reply input {
  flex: 1;
}

@media (width <= 700px) {
  .target-fields,
  .change-target-grid,
  .text-suggestion,
  .task-text-suggestion,
  .suggestion-diff {
    grid-template-columns: 1fr;
  }

  .suggestion-arrow {
    display: none;
  }

  .task-text-suggestion > svg {
    display: none;
  }

  .review-panel > header,
  .case-heading,
  .reply > div {
    align-items: stretch;
    flex-direction: column;
  }

  .case-actions button,
  .new-case {
    width: 100%;
  }

  .case-next-step {
    align-items: stretch;
    flex-direction: column;
  }

  .case-next-step.next-resubmitted {
    grid-template-columns: 1fr;
  }

  .reviewer-field {
    width: 100%;
  }

  .builder-introduction {
    align-items: flex-start;
    flex-direction: column;
  }

  .file-task-builder {
    padding: 0.55rem;
  }

  .change-request-list,
  .change-request-draft {
    padding: 0.65rem;
  }
}
</style>
