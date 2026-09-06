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
              ? 'Describe what the researcher should review before this contribution can be accepted.'
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
      <label v-if="filenames.length">
        <span>Related EAF file (optional)</span>
        <select v-model="draft.filename">
          <option value="">Whole submission</option>
          <option
            v-for="filename in filenames"
            :key="filename"
            :value="filename"
          >
            {{ filename }}
          </option>
        </select>
      </label>
      <label>
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
      <div class="composer-actions">
        <button type="submit" class="primary" :disabled="busy">
          {{
            requestChangesOnCreate ? 'Send correction request' : 'Open question'
          }}
        </button>
        <button type="button" @click="cancelComposer">Cancel</button>
      </div>
    </form>

    <template v-if="!composerOnly">
      <div
        v-if="cases.length"
        class="review-summary"
        aria-label="Review status summary"
      >
        <div>
          <strong>{{ activeCount }}</strong>
          <span>Active</span>
        </div>
        <div>
          <strong>{{ changesRequestedCount }}</strong>
          <span>Awaiting corrections</span>
        </div>
        <div>
          <strong>{{ resubmittedCount }}</strong>
          <span>Ready for another review</span>
        </div>
      </div>

      <div v-if="loading" class="panel-state">Loading correction requests…</div>
      <div v-else-if="error" class="panel-state error" role="alert">
        {{ error }}
      </div>
      <div v-else-if="!cases.length" class="panel-state">
        {{
          uploadId
            ? 'No correction requests have been opened for this contribution.'
            : 'No correction requests have been opened for this project.'
        }}
      </div>
      <div v-else class="case-list">
        <article
          v-for="item in cases"
          :id="`review-${item.case_id}`"
          :key="item.case_id"
          class="case-card"
          :class="{ highlighted: item.case_id === highlightedCaseId }"
        >
          <div class="case-heading">
            <div class="case-identity">
              <span class="state-badge" :class="`state-${item.state}`">
                {{ formatState(item.state) }}
              </span>
              <h5>{{ item.title }}</h5>
              <p v-if="item.filename" class="target">
                {{ item.filename
                }}<template v-if="item.tier_id"> · {{ item.tier_id }}</template>
                <template v-if="item.annotation_id">
                  · {{ item.annotation_id }}</template
                >
              </p>
              <p class="case-origin">Contribution #{{ item.upload_id }}</p>
            </div>
            <label
              v-if="canManage && !isFinished(item.state)"
              class="reviewer-field"
            >
              <span>Review lead</span>
              <select
                :value="item.assigned_to || ''"
                :aria-label="`Choose the reviewer responsible for ${item.title}`"
                title="The review lead follows the discussion, checks corrected uploads, and makes sure a final decision is recorded."
                :disabled="busy || membersLoading"
                @change="assign(item, $event.target.value)"
              >
                <option value="" disabled>Select a review lead</option>
                <option
                  v-for="member in members"
                  :key="member.user_id"
                  :value="member.user_id"
                >
                  {{ memberDisplayName(member) }}
                </option>
              </select>
            </label>
          </div>

          <div class="case-next-step" :class="`next-${item.state}`">
            <div class="next-step-copy">
              <font-awesome-icon :icon="nextStepIcon(item.state)" />
              <div>
                <strong>{{ nextStepTitle(item.state) }}</strong>
                <span>{{ nextStepDescription(item.state) }}</span>
              </div>
            </div>
            <div
              v-if="canManage && !isFinished(item.state)"
              class="case-actions"
            >
              <router-link
                v-if="item.state === 'changes_requested'"
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
                v-if="item.state !== 'changes_requested'"
                type="button"
                :disabled="busy || !item.assigned_to"
                @click="transition(item, 'changes_requested')"
              >
                Ask for corrected upload
              </button>
              <button
                class="resolve-case"
                type="button"
                title="Finish this review when no further action is needed. It can be reopened later."
                :disabled="busy || !item.assigned_to"
                @click="transition(item, 'resolved')"
              >
                Mark resolved
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
            v-if="canComment"
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
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import reviewService from '@/api/service/reviewService';
import { getProjectUsers } from '@/api/service/projectAssociationService';
import { useUserConfirm } from '@/composables/useUserConfirm';

const props = defineProps({
  projectId: { type: Number, required: true },
  uploadId: { type: Number, default: null },
  filenames: { type: Array, default: () => [] },
  allowCreate: { type: Boolean, default: true },
  canManage: { type: Boolean, default: true },
  canComment: { type: Boolean, default: true },
  highlightedCaseId: { type: String, default: '' },
  resubmissionUploadId: { type: Number, default: null },
  composerOnly: { type: Boolean, default: false },
  requestChangesOnCreate: { type: Boolean, default: false },
});
const emit = defineEmits(['created', 'cancel', 'count-change']);
const confirmAction = useUserConfirm();
const cases = ref([]);
const replies = reactive({});
const loading = ref(true);
const busy = ref(false);
const error = ref('');
const showComposer = ref(false);
const members = ref([]);
const membersLoading = ref(false);
const draft = reactive({
  title: '',
  filename: '',
  tier_id: null,
  annotation_id: null,
  start_ms: null,
  end_ms: null,
  initial_comment: '',
});
const activeCount = computed(
  () => cases.value.filter((item) => !isFinished(item.state)).length
);
const changesRequestedCount = computed(
  () => cases.value.filter((item) => item.state === 'changes_requested').length
);
const resubmittedCount = computed(
  () => cases.value.filter((item) => item.state === 'resubmitted').length
);

const formatState = (state) => state.replaceAll('_', ' ');
const isFinished = (state) => ['resolved', 'closed'].includes(state);
const nextStepDescription = (state) =>
  ({
    open: 'Discuss the question, then either ask for a corrected upload or finish the review.',
    changes_requested:
      'The contributor must revise the ELAN file and submit a corrected version.',
    resubmitted:
      'Inspect the corrected contribution and decide whether it is ready or needs another revision.',
    resolved:
      'No further action is required. Reopen the review if this decision was premature.',
    closed:
      'This review is complete. Its discussion remains available as project history.',
  })[state] || 'Continue the research review.';
const nextStepTitle = (state) =>
  ({
    open: 'Decide the next step',
    changes_requested: 'Waiting for corrected files',
    resubmitted: 'Review the corrected upload',
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

async function loadCases() {
  loading.value = true;
  error.value = '';
  try {
    cases.value = await reviewService.list(props.projectId, props.uploadId);
    emit('count-change', activeCount.value);
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'Review cases could not be loaded.';
  } finally {
    loading.value = false;
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
    const created = await reviewService.create(props.projectId, {
      upload_id: props.uploadId,
      request_changes: props.requestChangesOnCreate,
      title: draft.title,
      filename: draft.filename || null,
      tier_id: draft.tier_id,
      annotation_id: draft.annotation_id,
      start_ms: draft.start_ms,
      end_ms: draft.end_ms,
      initial_comment: draft.initial_comment,
    });
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
async function transition(item, state) {
  const confirmation = {
    changes_requested: {
      title: 'Ask for a corrected upload?',
      message:
        'The researcher will be asked to revise this contribution and upload corrected ELAN files. The discussion remains available.',
      confirmText: 'Ask for corrected upload',
    },
    resolved: {
      title: 'Mark this review as resolved?',
      message:
        'This means no further action is required and removes the case from the active count. You can reopen it later.',
      confirmText: 'Mark resolved',
    },
    open: {
      title: 'Reopen this review?',
      message:
        'The case will return to active review. Its previous discussion and decisions remain in the history.',
      confirmText: 'Reopen review',
    },
  }[state];
  if (
    confirmation &&
    !(await confirmAction({ ...confirmation, cancelText: 'Cancel' }))
  ) {
    return;
  }
  busy.value = true;
  try {
    replaceCase(
      await reviewService.transition(props.projectId, item.case_id, state)
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The review state could not be changed.';
  } finally {
    busy.value = false;
  }
}
async function assign(item, value) {
  busy.value = true;
  error.value = '';
  try {
    replaceCase(
      await reviewService.transition(
        props.projectId,
        item.case_id,
        item.state,
        {
          assigned_to: value ? Number(value) : null,
        }
      )
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The assignment could not be saved.';
  } finally {
    busy.value = false;
  }
}
async function linkResubmission(item) {
  busy.value = true;
  error.value = '';
  try {
    replaceCase(
      await reviewService.resubmit(
        props.projectId,
        item.case_id,
        props.resubmissionUploadId
      )
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The corrected upload could not be linked.';
  } finally {
    busy.value = false;
  }
}
function resetDraft() {
  Object.assign(draft, {
    title: '',
    filename: '',
    tier_id: null,
    annotation_id: null,
    start_ms: null,
    end_ms: null,
    initial_comment: '',
  });
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
onMounted(() => Promise.all([loadCases(), loadMembers()]));
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
  margin-top: 0.45rem;
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

.review-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
}

.review-summary > div {
  display: grid;
  gap: 0.15rem;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: white;
}

.review-summary strong {
  color: var(--primary-color);
  font-size: 1.25rem;
}

.review-summary span,
.case-origin {
  color: var(--color-text-muted);
  font-size: 0.78rem;
}

.case-origin {
  margin-top: 0.45rem;
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
}

textarea {
  min-height: 6rem;
  resize: vertical;
}

.case-list {
  display: grid;
  gap: 0.8rem;
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
  padding: 0.8rem 1rem;
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

.case-next-step.next-changes_requested {
  background: #fffbeb;
}

.case-next-step.next-resolved,
.case-next-step.next-closed {
  background: #f0fdf4;
}

.case-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
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

.panel-state {
  padding: 1rem;
  color: var(--color-text-muted);
  text-align: center;
}

.panel-state.error {
  color: #991b1b;
}

@media (width <= 700px) {
  .review-summary {
    grid-template-columns: 1fr;
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

  .reviewer-field {
    width: 100%;
  }
}
</style>
