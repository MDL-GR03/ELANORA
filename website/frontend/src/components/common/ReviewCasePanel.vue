<template>
  <section
    class="review-panel"
    :class="{ 'composer-only': composerOnly }"
    aria-labelledby="review-cases-title"
  >
    <header>
      <div>
        <span class="eyebrow">{{
          composerOnly
            ? t('reviewCases.panel.newRequestEyebrow')
            : t('reviewCases.panel.researchEyebrow')
        }}</span>
        <h4 id="review-cases-title">
          {{
            composerOnly
              ? t('reviewCases.panel.requestTitle')
              : t('reviewCases.panel.listTitle')
          }}
        </h4>
        <p class="panel-description">
          {{
            composerOnly
              ? t('reviewCases.panel.requestDescription')
              : t('reviewCases.panel.listDescription')
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
        {{ t('reviewCases.panel.openCase') }}
      </button>
    </header>

    <ReviewCaseComposer
      v-if="showComposer || composerOnly"
      :key="composerKey"
      ref="composer"
      :filenames="filenames"
      :upload-id="uploadId"
      :request-changes-on-create="requestChangesOnCreate"
      :busy="busy"
      :initial-target="composerTarget"
      @submit="createCase"
      @cancel="cancelComposer"
    />

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
          {{ t('reviewCases.card.noMatches') }}
        </div>
        <ReviewCaseCard
          v-for="item in visibleActiveCases"
          :key="item.case_id"
          :item="item"
        />
        <div v-if="reviewPageCount > 1" class="review-pagination">
          <button
            type="button"
            :disabled="reviewPage === 1"
            @click="reviewPage -= 1"
          >
            {{ t('reviewCases.pagination.previous') }}
          </button>
          <span>{{
            t('reviewCases.pagination.pageOf', {
              page: reviewPage,
              count: reviewPageCount,
            })
          }}</span>
          <button
            type="button"
            :disabled="reviewPage === reviewPageCount"
            @click="reviewPage += 1"
          >
            {{ t('reviewCases.pagination.next') }}
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
          <strong>{{ t('reviewCases.archive.title') }}</strong>
          <small>{{ t('reviewCases.archive.help') }}</small>
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
import { apiErrorMessage } from '@/utils/apiError';
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  toRef,
  watch,
} from 'vue';
import { useI18n } from 'vue-i18n';

import '@/assets/css/review-case-panel.css';
import reviewService from '@/api/service/reviewService';
import ArchivedReviewList from '@/components/common/ArchivedReviewList.vue';
import ReviewQueueOverview from '@/components/pageSpecific/contributions/ReviewQueueOverview.vue';
import ReviewCaseCard from '@/components/pageSpecific/reviews/ReviewCaseCard.vue';
import ReviewCaseComposer from '@/components/pageSpecific/reviews/ReviewCaseComposer.vue';
import { provideReviewCaseContext } from '@/components/pageSpecific/reviews/reviewCaseContext';
import { getProjectUsers } from '@/api/service/projectAssociationService';
import { useReviewCaseQueue } from '@/composables/useReviewCaseQueue';
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
const { t, locale } = useI18n();
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
const taskStatusOptions = computed(() =>
  ['', 'requested', 'reopened', 'addressed', 'accepted'].map((value) => ({
    value,
    label: t(`reviewCases.statusOptions.${value || 'all'}`),
  }))
);
const reviewLeadOptions = computed(() =>
  members.value.map((member) => ({
    value: member.user_id,
    label: memberDisplayName(member),
  }))
);
const composer = ref(null);
const composerKey = ref(0);
const composerTarget = ref({});
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

const CASE_STATES = [
  'open',
  'changes_requested',
  'resubmitted',
  'resolved',
  'closed',
];
const TASK_STATUSES = ['requested', 'reopened', 'addressed', 'accepted'];
const formatState = (state) =>
  CASE_STATES.includes(state)
    ? t(`reviewCases.states.${state}`)
    : state.replaceAll('_', ' ');
const formatTaskStatus = (status, item = null) => {
  if (item?.state === 'resubmitted' && status !== 'accepted') {
    return props.canManage
      ? t('reviewCases.taskStatus.decisionNeeded')
      : t('reviewCases.taskStatus.inReview');
  }
  return TASK_STATUSES.includes(status)
    ? t(`reviewCases.taskStatus.${status}`)
    : status;
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
  t,
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
  t,
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
const nextStepDescription = (state, item) => {
  const key = (name) => t(`reviewCases.nextStep.descriptions.${name}`);
  if (state === 'resubmitted') {
    if (!props.canManage) {
      return t('reviewCases.nextStep.descriptions.submitted', {
        id: item.resubmitted_upload_id,
      });
    }
    if (revisionFeedbackCaseId.value === item.case_id) {
      return revisionTargets[item.case_id]?.length
        ? key('selectedTargets')
        : key('explain');
    }
    return t('reviewCases.nextStep.descriptions.draft', {
      edits: t(
        'reviewCases.nextStep.descriptions.edits',
        selectedRevisionTaskIds(item).length
      ),
    });
  }
  return ['open', 'changes_requested', 'resolved', 'closed'].includes(state)
    ? key(state)
    : key('other');
};
const nextStepTitle = (state, item) => {
  const title = (name) => t(`reviewCases.nextStep.titles.${name}`);
  if (state === 'resubmitted') {
    if (!props.canManage) return title('submitted');
    return revisionFeedbackCaseId.value === item.case_id
      ? title('requestAnother')
      : title('notSent');
  }
  return ['open', 'changes_requested', 'resolved', 'closed'].includes(state)
    ? title(state)
    : title('other');
};
const nextStepIcon = (state) =>
  ({
    open: 'fa-solid fa-circle-question',
    changes_requested: 'fa-solid fa-clock',
    resubmitted: 'fa-solid fa-rotate',
    resolved: 'fa-solid fa-circle-check',
    closed: 'fa-solid fa-box-archive',
  })[state] || 'fa-solid fa-circle-info';
const formatDate = (value) =>
  new Intl.DateTimeFormat(locale.value, {
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
    error.value = apiErrorMessage(
      requestError,
      t,
      t('reviewCases.errors.load')
    );
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
async function createCase(payload) {
  busy.value = true;
  error.value = '';
  try {
    const created = await reviewService.create(props.projectId, payload);
    cases.value.unshift(created);
    composer.value?.reset();
    showComposer.value = false;
    emit('created', created);
    emit('count-change', activeCount.value);
  } catch (requestError) {
    error.value = apiErrorMessage(
      requestError,
      t,
      t('reviewCases.errors.create')
    );
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
    error.value = apiErrorMessage(
      requestError,
      t,
      t('reviewCases.errors.comment')
    );
  } finally {
    busy.value = false;
  }
}
function memberDisplayName(member) {
  const fullName = [member.first_name, member.last_name]
    .filter(Boolean)
    .join(' ');
  return (
    fullName ||
    member.username ||
    member.email ||
    t('reviewCases.card.unnamedMember')
  );
}
function cancelComposer() {
  showComposer.value = false;
  emit('cancel');
}
function openComposer(target = {}) {
  composerTarget.value = { ...target };
  composerKey.value += 1;
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
provideReviewCaseContext({
  activeDiff,
  addComment,
  approveTask,
  approveTaskLabel,
  assign,
  beginOrRequestAnotherRevision,
  busy,
  canActAsContributor,
  canComment: toRef(props, 'canComment'),
  canManage: toRef(props, 'canManage'),
  filteredTasks,
  formatDate,
  formatState,
  formatTaskStatus,
  hasRevisionFeedback,
  highlightedCaseId: toRef(props, 'highlightedCaseId'),
  isFinished,
  isTaskSelectedForRevision,
  linkResubmission,
  membersLoading,
  nextStepDescription,
  nextStepIcon,
  nextStepTitle,
  openReviewArchive,
  projectId: toRef(props, 'projectId'),
  projectName: toRef(props, 'projectName'),
  removeRevisionTarget,
  replies,
  resubmissionUploadId: toRef(props, 'resubmissionUploadId'),
  reviewLeadOptions,
  revisionFeedbackCaseId,
  revisionRequestCount,
  revisionTargetSummary,
  revisionTargets,
  selectRevisionTarget,
  selectedAnnotationIds,
  selectedRevisionTaskIds,
  showNextStep,
  t,
  taskBusyLabel,
  taskQuery,
  taskStatus,
  taskStatusOptions,
  toggleTaskForRevision,
  transition,
  unresolvedTaskCount,
  visibleTaskLimit,
  visibleTasks,
});

defineExpose({ openComposer });
</script>
