<template>
  <div class="pending-uploads-page">
    <div class="pending-uploads-container">
      <WorkspaceHeader
        embedded
        :context="currentProjectName"
        :title="t('pendingUploads.title')"
        :description="t('pendingUploads.pageDescription')"
      />

      <ContributionWorkspaceTabs
        v-if="!workspaceMode"
        :active-view="activeView"
        :contribution-count="contributionThreads.length"
        :active-review-count="activeReviewCount"
        :can-administer="canAdminister"
        @select="setActiveView"
      />

      <section
        v-if="workspaceMode && selectedUpload"
        class="contribution-workspace"
        :aria-labelledby="`${workspaceMode}-workspace-title`"
      >
        <header class="contribution-workspace-header">
          <button
            type="button"
            class="workspace-back"
            :aria-label="t('contributionWorkspace.back')"
            :title="t('contributionWorkspace.back')"
            @click="closeWorkspace"
          >
            <font-awesome-icon icon="fa-solid fa-arrow-left" />
          </button>
          <div>
            <h2 :id="`${workspaceMode}-workspace-title`">
              {{
                workspaceMode === 'details'
                  ? t('contributionWorkspace.contribution', {
                      id: selectedUpload.upload_id,
                    })
                  : workspaceTitle
              }}
            </h2>
            <p>{{ workspaceDescription }}</p>
          </div>
        </header>

        <ReviewCasePanel
          v-if="workspaceMode === 'correction'"
          :project-id="currentProject.project_id"
          :project-name="currentProjectName"
          :upload-id="selectedUpload.upload_id"
          :filenames="selectedUploadFilenames"
          composer-only
          request-changes-on-create
          :allow-create="true"
          :can-manage="canAdminister"
          :can-comment="canContribute"
          :current-user-id="userStore.user?.user_id"
          @created="onCorrectionCreated"
          @cancel="closeWorkspace"
        />
        <UploadDetailsView
          v-else-if="workspaceMode === 'details'"
          :upload="selectedUpload"
          :project-name="currentProjectName"
        />
        <UploadResolutionView
          v-else-if="workspaceMode === 'resolution'"
          :project-id="currentProject.project_id"
          :project-name="currentProjectName"
          :upload="selectedUpload"
          @resolved="onUploadResolved"
          @cancelled="closeWorkspace"
        />
      </section>

      <!-- No Project Selected -->
      <div v-else-if="!currentProject" class="no-selection">
        <div class="no-selection-icon">
          <font-awesome-icon icon="fa-solid fa-folder-open" />
        </div>
        <h3>{{ t('pendingUploads.noProjectSelected.title') }}</h3>
        <p>{{ t('pendingUploads.noProjectSelected.message') }}</p>
        <router-link to="/projects" class="select-project-btn">
          {{ t('pendingUploads.noProjectSelected.selectProject') }}
        </router-link>
      </div>

      <!-- Loading State -->
      <div v-else-if="activeView === 'queue' && uploadsLoading" class="loading">
        <div class="loading-spinner"></div>
        <p>{{ t('pendingUploads.loading') }}</p>
      </div>

      <!-- No Pending Uploads -->
      <div
        v-else-if="activeView === 'queue' && contributionThreads.length === 0"
        class="no-uploads"
      >
        <div class="no-uploads-icon">
          <font-awesome-icon icon="fa-solid fa-circle-check" />
        </div>
        <h3>{{ t('pendingUploads.noUploads.title') }}</h3>
        <p>{{ t('pendingUploads.noUploads.message') }}</p>
      </div>

      <!-- Pending Uploads List -->
      <div
        v-else-if="activeView === 'queue'"
        id="contribution-queue-panel"
        class="uploads-section"
        role="tabpanel"
        aria-labelledby="contribution-queue-tab"
      >
        <ContributionQueueControls
          v-model:filter="queueFilter"
          v-model:query="queueQuery"
          v-model:sort="queueSort"
          :total="totalPending"
          :ready="readyCount"
          :corrections="awaitingCorrectionsCount"
          :conflicts="conflictsCount"
          :result-count="filteredContributionThreads.length"
        />

        <!-- Upload List -->
        <div class="uploads-list">
          <div
            v-for="upload in filteredContributionThreads"
            :id="`contribution-${upload.upload_id}`"
            :key="upload.upload_id"
            class="upload-item"
            :class="getUploadStatusClass(upload)"
          >
            <div class="upload-header">
              <div class="upload-info">
                <h3 class="upload-branch">
                  {{
                    t('contributionWorkspace.contribution', {
                      id: upload.upload_id,
                    })
                  }}
                </h3>
                <div class="upload-meta">
                  <span v-if="upload.version_number > 1" class="version-badge">
                    {{
                      t('contributionWorkspace.updatedVersion', {
                        version: upload.version_number,
                      })
                    }}
                  </span>
                  <span class="upload-type">{{
                    formatUploadType(upload)
                  }}</span>
                  <span class="upload-date">{{
                    formatDate(upload.uploaded_at)
                  }}</span>
                  <span class="upload-user">{{
                    t('pendingUploads.uploadedBy', {
                      user: upload.uploaded_by || t('pendingUploads.unknown'),
                    })
                  }}</span>
                </div>
              </div>

              <div class="upload-status-section">
                <div class="upload-status">
                  <span
                    class="status-badge"
                    :class="getStatusClass(upload.merge_status)"
                  >
                    {{ formatStatus(upload.merge_status) }}
                  </span>
                </div>

                <!-- Actions -->
                <div class="upload-actions">
                  <button
                    type="button"
                    class="action-btn view-btn"
                    :disabled="actionBusy"
                    @click="viewUploadDetails(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-eye" />
                    {{ t('pendingUploads.actions.viewDetails') }}
                  </button>

                  <button
                    v-if="upload.review_case"
                    type="button"
                    class="action-btn review-link-btn"
                    :disabled="actionBusy"
                    @click="openLinkedReview(upload.review_case)"
                  >
                    <font-awesome-icon icon="fa-solid fa-comments" />
                    {{ t('contributionWorkspace.actions.discussion') }}
                  </button>

                  <button
                    v-if="
                      canAdminister &&
                      !hasActiveReview(upload) &&
                      !['duplicate', 'superseded'].includes(upload.merge_status)
                    "
                    type="button"
                    class="action-btn review-btn"
                    :disabled="actionBusy"
                    @click="requestCorrection(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-comment-dots" />
                    {{ t('contributionWorkspace.actions.requestCorrection') }}
                  </button>

                  <button
                    v-if="canAdminister && upload.merge_status === 'duplicate'"
                    type="button"
                    class="action-btn dismiss-btn"
                    :disabled="actionBusy"
                    @click="dismissDuplicate(upload)"
                  >
                    <font-awesome-icon icon="fa-solid fa-box-archive" />
                    {{ t('contributionWorkspace.actions.dismissDuplicate') }}
                  </button>

                  <button
                    v-if="
                      canAdminister && upload.merge_status === 'ready_to_merge'
                    "
                    class="action-btn merge-btn"
                    type="button"
                    :disabled="actionBusy"
                    @click="mergeUpload(upload)"
                  >
                    <font-awesome-icon icon="fa-solid fa-code-merge" />
                    {{
                      merging === upload.upload_id
                        ? t('pendingUploads.actions.merging')
                        : t('pendingUploads.actions.mergeNow')
                    }}
                  </button>

                  <button
                    v-if="
                      canAdminister &&
                      upload.merge_status === 'needs_resolution'
                    "
                    class="action-btn resolve-btn"
                    type="button"
                    :disabled="actionBusy"
                    @click="resolveUpload(upload, $event)"
                  >
                    <font-awesome-icon icon="fa-solid fa-screwdriver-wrench" />
                    {{ t('pendingUploads.actions.resolveConflicts') }}
                  </button>

                  <details
                    v-if="
                      canAdminister &&
                      !['duplicate', 'superseded'].includes(upload.merge_status)
                    "
                    class="contribution-more-actions"
                  >
                    <summary>
                      {{ t('contributionWorkspace.actions.more') }}
                    </summary>
                    <div>
                      <button
                        type="button"
                        class="action-btn test-btn"
                        :disabled="actionBusy"
                        @click="testMerge(upload)"
                      >
                        <font-awesome-icon icon="fa-solid fa-shield-halved" />
                        {{
                          testing === upload.upload_id
                            ? t('pendingUploads.actions.testing')
                            : t('pendingUploads.actions.testMerge')
                        }}
                      </button>
                      <button
                        type="button"
                        class="action-btn decline-btn"
                        :disabled="actionBusy"
                        @click="openDeclineModal(upload, $event)"
                      >
                        <font-awesome-icon icon="fa-solid fa-ban" />
                        {{ t('contributionWorkspace.actions.decline') }}
                      </button>
                    </div>
                  </details>
                </div>
              </div>
            </div>

            <!-- File Summary -->
            <div class="upload-summary">
              <section
                class="research-context-review"
                :class="`research-context-review--${upload.research_context?.scope_status || 'missing_context'}`"
                :aria-label="t('contributionWorkspace.context.aria')"
              >
                <div class="research-context-review__heading">
                  <div>
                    <strong>
                      {{
                        upload.research_context?.declared_topic_name ||
                        upload.research_context?.proposed_topic_name ||
                        t('contributionWorkspace.context.general')
                      }}
                    </strong>
                    <span class="research-context-summary-text">
                      {{
                        upload.research_context?.summary ||
                        t('contributionWorkspace.context.noSummary')
                      }}
                    </span>
                  </div>
                  <span class="research-context-status">
                    {{ researchContextStatusLabel(upload.research_context) }}
                  </span>
                </div>
                <dl>
                  <div>
                    <dt>
                      {{ t('contributionWorkspace.context.detectedTiers') }}
                    </dt>
                    <dd class="research-tier-list">
                      <span
                        v-for="tier in upload.research_context?.changed_tiers ||
                        []"
                        :key="tier"
                        :class="{
                          'is-baseline':
                            upload.research_context?.baseline_changed_tiers?.includes(
                              tier
                            ),
                          'is-baseline-correction':
                            upload.research_context?.declared_baseline_correction_tiers?.includes(
                              tier
                            ),
                          'is-outside-scope':
                            upload.research_context?.outside_scope_tiers?.includes(
                              tier
                            ),
                        }"
                        :title="
                          upload.research_context?.outside_scope_tiers?.includes(
                            tier
                          )
                            ? t('contributionDetails.tiers.outside')
                            : upload.research_context?.declared_baseline_correction_tiers?.includes(
                                  tier
                                )
                              ? t('contributionDetails.tiers.correction')
                              : upload.research_context?.baseline_changed_tiers?.includes(
                                    tier
                                  )
                                ? t('contributionDetails.tiers.baseline')
                                : t('contributionDetails.tiers.topic')
                        "
                      >
                        {{ tier }}
                      </span>
                      <em
                        v-if="!upload.research_context?.changed_tiers?.length"
                      >
                        {{ t('contributionWorkspace.context.noTierChanges') }}
                      </em>
                    </dd>
                  </div>
                </dl>
                <button
                  v-if="
                    upload.research_context?.scope_status ===
                    'topic_review_needed'
                  "
                  type="button"
                  class="research-topic-review-toggle"
                  :aria-expanded="expandedTopicDecision === upload.upload_id"
                  @click="
                    expandedTopicDecision =
                      expandedTopicDecision === upload.upload_id
                        ? null
                        : upload.upload_id
                  "
                >
                  {{
                    expandedTopicDecision === upload.upload_id
                      ? t('contributionWorkspace.context.hideDecision')
                      : t('contributionWorkspace.context.reviewSuggestion')
                  }}
                  <font-awesome-icon
                    :icon="
                      expandedTopicDecision === upload.upload_id
                        ? 'fa-solid fa-chevron-up'
                        : 'fa-solid fa-chevron-down'
                    "
                  />
                </button>
                <p
                  v-if="
                    upload.research_context?.scope_status === 'outside_scope'
                  "
                  class="research-context-exception"
                >
                  {{ t('contributionWorkspace.context.outsideExplanation') }}
                </p>
                <p
                  v-else-if="
                    upload.research_context?.scope_status ===
                      'topic_review_needed' &&
                    expandedTopicDecision === upload.upload_id
                  "
                  class="research-context-exception"
                >
                  {{ t('contributionWorkspace.context.suggestionExplanation') }}
                </p>
                <div
                  v-if="
                    canAdminister &&
                    upload.research_context?.scope_status ===
                      'topic_review_needed' &&
                    expandedTopicDecision === upload.upload_id
                  "
                  class="research-topic-decision"
                >
                  <label>
                    <span>{{
                      t('contributionWorkspace.context.useExisting')
                    }}</span>
                    <AppSelect
                      v-model="topicDecisions[upload.upload_id]"
                      :placeholder="
                        t('contributionWorkspace.context.chooseTopic')
                      "
                      :options="researchTopicOptions"
                    />
                  </label>
                  <button
                    type="button"
                    class="action-btn view-btn"
                    :disabled="
                      !topicDecisions[upload.upload_id] || topicDecisionBusy
                    "
                    @click="assignResearchTopic(upload)"
                  >
                    {{ t('contributionWorkspace.context.assignTopic') }}
                  </button>
                  <label>
                    <span>{{
                      t('contributionWorkspace.context.approveName')
                    }}</span>
                    <input
                      v-model="topicSuggestionNames[upload.upload_id]"
                      maxlength="100"
                      :placeholder="
                        upload.research_context?.proposed_topic_name ||
                        t('contributionWorkspace.context.newTopicName')
                      "
                    />
                  </label>
                  <button
                    type="button"
                    class="action-btn review-btn"
                    :disabled="
                      !(topicSuggestionNames[upload.upload_id] || '').trim() ||
                      topicDecisionBusy
                    "
                    @click="createResearchTopicFromContribution(upload)"
                  >
                    {{ t('contributionWorkspace.context.createTopic') }}
                  </button>
                </div>
              </section>
              <div
                v-if="upload.annotation_collisions?.length"
                class="annotation-collision-notice"
              >
                <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
                <div>
                  <strong>{{
                    t('contributionWorkspace.collision.title')
                  }}</strong>
                  <p>
                    {{ annotationCollisionCount(upload) }}
                    {{
                      annotationCollisionCount(upload) === 1
                        ? 'annotation'
                        : 'annotations'
                    }}
                    also has a different proposal in
                    <template
                      v-for="(collision, index) in upload.annotation_collisions"
                      :key="collision.contribution_id"
                    >
                      <span v-if="index > 0">, </span>
                      <button
                        type="button"
                        @click="scrollToContribution(collision.contribution_id)"
                      >
                        contribution #{{ collision.contribution_id }}
                      </button></template
                    >. Review both before accepting either one.
                  </p>
                </div>
              </div>
              <div v-if="upload.version_history.length" class="version-history">
                <div class="version-context">
                  <font-awesome-icon icon="fa-solid fa-code-branch" />
                  <span>
                    This contribution was updated in response to
                    <button
                      v-if="upload.review_case"
                      type="button"
                      class="inline-review-link"
                      @click="openLinkedReview(upload.review_case)"
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
                        @click="viewUploadDetails(version, $event)"
                      >
                        Version {{ index + 1 }} · contribution #{{
                          version.upload_id
                        }}
                      </button>
                      <span>{{ formatDate(version.uploaded_at) }}</span>
                    </li>
                    <li class="current-version">
                      <strong>
                        Version {{ upload.version_number }} · contribution #{{
                          upload.upload_id
                        }}
                      </strong>
                      <span>
                        {{ formatDate(upload.uploaded_at) }} · Current version
                      </span>
                    </li>
                  </ol>
                </details>
              </div>
              <div
                v-if="upload.duplicate_of_upload_id"
                class="duplicate-notice"
              >
                <font-awesome-icon icon="fa-solid fa-copy" />
                Same submitted content as contribution #{{
                  upload.duplicate_of_upload_id
                }}. Only the original can be accepted.
              </div>
              <div
                v-if="upload.superseded_by_upload_id"
                class="duplicate-notice"
              >
                <font-awesome-icon icon="fa-solid fa-code-branch" />
                Superseded by contribution #{{
                  upload.superseded_by_upload_id
                }}. This version is retained as history and cannot be accepted.
              </div>
              <div
                class="quality-checks"
                aria-label="Submission quality checks"
              >
                <span class="quality-check passed">
                  <font-awesome-icon icon="fa-solid fa-circle-check" />
                  Valid ELAN files
                </span>
                <span class="quality-check passed">
                  <font-awesome-icon icon="fa-solid fa-circle-check" />
                  Naming rules passed
                </span>
                <span class="quality-check" :class="protocolCheckClass(upload)">
                  <font-awesome-icon
                    :icon="
                      upload.quality_checks?.protocol === 'passed'
                        ? 'fa-solid fa-circle-check'
                        : upload.quality_checks?.protocol === 'recheck_required'
                          ? 'fa-solid fa-triangle-exclamation'
                          : 'fa-solid fa-circle-info'
                    "
                  />
                  {{ protocolCheckLabel(upload) }}
                </span>
              </div>
              <div class="file-counts">
                <span v-if="upload.file_counts?.new > 0" class="file-count new">
                  +{{ upload.file_counts.new }}
                  {{ t('pendingUploads.fileTypes.new') }}
                </span>
                <span
                  v-if="upload.file_counts?.modified > 0"
                  class="file-count modified"
                >
                  ~{{ upload.file_counts.modified }}
                  {{ t('pendingUploads.fileTypes.modified') }}
                </span>
                <span
                  v-if="upload.file_counts?.deleted > 0"
                  class="file-count deleted"
                >
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
                  {{
                    upload.semantic_summary.annotations === 1
                      ? 'change'
                      : 'changes'
                  }}
                </strong>
                <span
                  v-if="upload.semantic_summary.added"
                  class="semantic-count added"
                >
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

            <!-- Conflicts (if any) -->
            <div
              v-if="upload.conflicted_files?.length > 0"
              class="conflicts-section"
            >
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
          </div>
          <div
            v-if="!filteredContributionThreads.length"
            class="queue-empty-filter"
          >
            No active contributions match this filter.
          </div>
        </div>
      </div>

      <ReviewCasePanel
        v-else-if="activeView === 'reviews'"
        id="contribution-reviews-panel"
        role="tabpanel"
        aria-labelledby="contribution-reviews-tab"
        :project-id="currentProject.project_id"
        :project-name="currentProjectName"
        :allow-create="false"
        :can-manage="canAdminister"
        :can-comment="canContribute"
        :current-user-id="userStore.user?.user_id"
        :highlighted-case-id="highlightedCaseId"
        :resubmission-upload-id="resubmissionUploadId"
        @count-change="onReviewCountChange"
      />

      <AcceptedProjectHistory
        v-else-if="activeView === 'history' && canAdminister"
        id="contribution-history-panel"
        role="tabpanel"
        aria-labelledby="contribution-history-tab"
        :project-name="currentProjectName"
        @restored="fetchPendingUploads"
      />

      <div
        v-if="showDeclineModal"
        class="modal-overlay"
        role="presentation"
        @click="closeDeclineModal"
      >
        <form
          ref="declineDialog"
          class="modal-content decline-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="decline-modal-title"
          tabindex="-1"
          @submit.prevent="declineUpload"
          @keydown.esc="closeDeclineModal"
          @click.stop
        >
          <div class="modal-header">
            <div>
              <span class="modal-eyebrow"
                >Contribution #{{ selectedUpload?.upload_id }}</span
              >
              <h2 id="decline-modal-title">Decline contribution</h2>
            </div>
            <button
              type="button"
              class="close-btn"
              :aria-label="t('common.close')"
              @click="closeDeclineModal"
            >
              <font-awesome-icon icon="fa-solid fa-xmark" />
            </button>
          </div>
          <div class="modal-body decline-modal-body">
            <p>
              This permanently closes the contribution and any linked correction
              discussion. Its audit history is preserved, but it cannot later be
              accepted.
            </p>
            <label for="decline-reason">Reason for the researcher</label>
            <textarea
              id="decline-reason"
              v-model="declineReason"
              rows="5"
              maxlength="1000"
              required
              minlength="3"
              placeholder="Explain why this contribution will not be accepted"
            ></textarea>
            <div class="decline-modal-actions">
              <button
                type="button"
                class="action-btn view-btn"
                @click="closeDeclineModal"
              >
                {{ t('common.cancel') }}
              </button>
              <button
                type="submit"
                class="action-btn decline-btn"
                :disabled="declineReason.trim().length < 3 || actionBusy"
              >
                {{
                  dismissing === selectedUpload?.upload_id
                    ? 'Declining…'
                    : 'Decline contribution'
                }}
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- Error Messages -->
      <div v-if="error" class="error-message" role="alert">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, watch, nextTick } from 'vue';
import gitService from '@/api/service/gitService';
import reviewService from '@/api/service/reviewService';
import { fetchResearchTopics } from '@/api/service/tierService';
import '@/assets/css/pending-uploads-page.css';
import UploadDetailsView from '@/components/common/UploadDetailsView.vue';
import UploadResolutionView from '@/components/common/UploadResolutionView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';
import AcceptedProjectHistory from '@/components/common/AcceptedProjectHistory.vue';
import ContributionQueueControls from '@/components/pageSpecific/contributions/ContributionQueueControls.vue';
import ContributionWorkspaceTabs from '@/components/pageSpecific/contributions/ContributionWorkspaceTabs.vue';
import { useProjectStore } from '@/stores/project.js';
import { useUserStore } from '@/stores/user.js';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { hasProjectPermission } from '@/utils/authorization';
import {
  countAnnotationCollisions,
  groupContributionThreads,
  sortContributionThreads,
} from '@/utils/contributionThreads';
import { useEventMessageStore } from '@/stores/eventMessage.js';

// State
const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const confirmAction = useUserConfirm();
const userStore = useUserStore();
const eventMessages = useEventMessageStore();
const pendingUploads = ref([]);
const uploadsLoading = ref(false);
const error = ref('');
const activeReviewCount = ref(0);
const reviewCases = ref([]);
const researchTopics = ref([]);
const topicDecisions = ref({});
const topicSuggestionNames = ref({});
const topicDecisionBusy = ref(false);
const expandedTopicDecision = ref(null);

// Modal state
const showDeclineModal = ref(false);
const selectedUpload = ref(null);
const declineReason = ref('');
const declineDialog = ref(null);
let modalTrigger = null;

// Action state
const merging = ref(null); // upload_id being merged
const testing = ref(null); // upload_id being tested
const dismissing = ref(null);
const actionBusy = computed(
  () =>
    merging.value !== null ||
    testing.value !== null ||
    dismissing.value !== null
);
const queueFilter = ref('all');
const queueQuery = ref('');
const queueSort = ref('oldest');
const researchTopicOptions = computed(() =>
  researchTopics.value.map((topic) => ({
    value: topic.topic_id,
    label: topic.name,
  }))
);

// Project store
const projectStore = useProjectStore();

// Computed properties from project store
const currentProject = computed(() => projectStore.currentProject);
const currentProjectName = computed(() => {
  if (!currentProject.value) return '';

  return typeof currentProject.value === 'object'
    ? currentProject.value.project_name
    : currentProject.value;
});
const activeView = computed(() => {
  if (route.query.view === 'reviews') return 'reviews';
  if (route.query.view === 'history' && canAdminister.value) return 'history';
  return 'queue';
});
const highlightedCaseId = computed(() => String(route.query.case || ''));
const resubmissionUploadId = computed(() =>
  route.query.resubmission ? Number(route.query.resubmission) : null
);
const workspaceMode = computed(() => {
  const mode = String(route.query.workspace || '');
  return ['details', 'correction', 'resolution'].includes(mode) ? mode : '';
});
const workspaceTitle = computed(
  () =>
    ({
      details: 'Contribution details',
      correction: 'Request corrections',
      resolution: 'Resolve contribution conflicts',
    })[workspaceMode.value] || 'Contribution workspace'
);
const workspaceDescription = computed(
  () =>
    ({
      details:
        'Inspect files, validation results, and ELAN annotation changes.',
      correction:
        'Select affected files and record each concrete requested edit.',
      resolution: 'Compare conflicting versions and record a safe resolution.',
    })[workspaceMode.value] || ''
);
const canAdminister = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'admin')
);
const canContribute = computed(() =>
  hasProjectPermission(userStore.user, currentProject.value, 'write')
);
const selectedUploadFilenames = computed(() => {
  const files = selectedUpload.value?.files;
  if (!files) return [];
  return [
    ...(files.new || []),
    ...(files.modified || []),
    ...(files.deleted || []),
  ];
});

function setActiveView(view) {
  const query = { ...route.query, view };
  if (view !== 'reviews') {
    delete query.case;
    delete query.resubmission;
  }
  void router.replace({ query });
}

function hasActiveReview(upload) {
  return Boolean(
    upload.review_case &&
      !['resolved', 'closed'].includes(upload.review_case.state)
  );
}

// Upload computed properties
const contributionThreads = computed(() =>
  groupContributionThreads(pendingUploads.value, reviewCases.value)
);
const totalPending = computed(() => contributionThreads.value.length);
const readyCount = computed(
  () =>
    contributionThreads.value.filter((u) => u.merge_status === 'ready_to_merge')
      .length
);
const awaitingCorrectionsCount = computed(
  () =>
    contributionThreads.value.filter(
      (upload) => upload.merge_status === 'changes_requested'
    ).length
);
const filteredContributionThreads = computed(() => {
  const needle = queueQuery.value.toLocaleLowerCase();
  const matching = contributionThreads.value.filter((upload) => {
    const statusMatches =
      queueFilter.value === 'all' ||
      (queueFilter.value === 'ready' &&
        upload.merge_status === 'ready_to_merge') ||
      (queueFilter.value === 'corrections' &&
        ['under_review', 'changes_requested', 'review_required'].includes(
          upload.merge_status
        )) ||
      (queueFilter.value === 'resolution' &&
        upload.merge_status === 'needs_resolution');
    const searchable = [
      upload.upload_id,
      `#${upload.upload_id}`,
      `contribution ${upload.upload_id}`,
      upload.uploaded_by,
      upload.review_case?.title,
      ...Object.values(upload.files || {}).flat(),
      ...Object.entries(upload.semantic_summary || {}).flat(),
    ]
      .filter((value) => value != null)
      .join(' ')
      .toLocaleLowerCase();
    return statusMatches && (!needle || searchable.includes(needle));
  });
  return sortContributionThreads(matching, queueSort.value);
});
const conflictsCount = computed(
  () =>
    contributionThreads.value.filter(
      (u) => u.merge_status === 'needs_resolution'
    ).length
);

function annotationCollisionCount(upload) {
  return countAnnotationCollisions(upload);
}

function researchContextStatusLabel(context = {}) {
  return (
    {
      aligned: t('contributionWorkspace.context.statusAligned'),
      outside_scope: t('contributionWorkspace.context.statusOutside'),
      topic_review_needed: t('contributionWorkspace.context.statusDecision'),
      declared_general: t('contributionWorkspace.context.general'),
      missing_context: t('contributionWorkspace.context.statusMissing'),
    }[context?.scope_status] || t('contributionWorkspace.context.statusMissing')
  );
}

function scrollToContribution(uploadId) {
  document
    .getElementById(`contribution-${uploadId}`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Auto-refresh interval
let refreshInterval = null;
let fetchSequence = 0;
let fetchInFlight = false;

// Watch for project changes
watch(
  () => [route.query.project, projectStore.projects.length],
  ([projectId]) => {
    if (!projectId) return;
    const requested = projectStore.projects.find(
      (project) => project.project_id === Number(projectId)
    );
    if (requested) projectStore.setCurrentProject(requested);
  },
  { immediate: true }
);

watch(
  () => currentProject.value?.project_id,
  async (newProjectId, oldProjectId) => {
    if (newProjectId === oldProjectId) return;
    pendingUploads.value = [];
    error.value = '';
    if (newProjectId) {
      await Promise.all([
        fetchPendingUploads(),
        fetchReviewCount(),
        loadResearchTopics(),
      ]);
    }
  },
  { immediate: true }
);

watch(
  () => [route.query.workspace, route.query.upload, pendingUploads.value],
  ([mode, uploadId]) => {
    if (!mode || !uploadId) return;
    selectedUpload.value =
      pendingUploads.value.find(
        (upload) => upload.upload_id === Number(uploadId)
      ) || null;
  },
  { immediate: true }
);

onMounted(async () => {
  // Set up auto-refresh every 30 seconds
  refreshInterval = setInterval(() => {
    if (currentProject.value && document.visibilityState === 'visible') {
      fetchPendingUploads(false);
    }
  }, 30000);
  projectStore.initBroadcastChannel();
});

// Cleanup interval on unmount
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

async function fetchPendingUploads(showLoading = true) {
  if (!currentProjectName.value) {
    pendingUploads.value = [];
    return;
  }

  if (fetchInFlight) return;
  const requestedProject = currentProjectName.value;
  const request = ++fetchSequence;
  fetchInFlight = true;
  try {
    if (showLoading) uploadsLoading.value = true;
    error.value = '';

    const response =
      await gitService.getPendingUploadsWithStatus(requestedProject);
    if (
      request === fetchSequence &&
      requestedProject === currentProjectName.value
    ) {
      pendingUploads.value = response.pending_uploads || [];
      topicSuggestionNames.value = Object.fromEntries(
        pendingUploads.value
          .filter((upload) => upload.research_context?.proposed_topic_name)
          .map((upload) => [
            upload.upload_id,
            upload.research_context.proposed_topic_name,
          ])
      );
    }
  } catch {
    if (
      showLoading &&
      request === fetchSequence &&
      requestedProject === currentProjectName.value
    ) {
      error.value = t('pendingUploads.errors.loadFailed');
      pendingUploads.value = [];
    }
  } finally {
    fetchInFlight = false;
    if (showLoading && request === fetchSequence) uploadsLoading.value = false;
    if (
      requestedProject !== currentProjectName.value &&
      currentProjectName.value
    ) {
      void fetchPendingUploads(showLoading);
    }
  }
}

async function loadResearchTopics() {
  if (!currentProject.value?.project_id) {
    researchTopics.value = [];
    return;
  }
  try {
    researchTopics.value = await fetchResearchTopics(
      currentProject.value.project_id
    );
  } catch {
    researchTopics.value = [];
  }
}

async function assignResearchTopic(upload) {
  const topicId = Number(topicDecisions.value[upload.upload_id]);
  if (!topicId) return;
  topicDecisionBusy.value = true;
  error.value = '';
  try {
    await gitService.setContributionResearchTopic(
      currentProjectName.value,
      upload.upload_id,
      { topic_id: topicId, new_topic_name: null }
    );
    await fetchPendingUploads(false);
    eventMessages.addMessage('Research topic assigned.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The research topic could not be assigned.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    topicDecisionBusy.value = false;
  }
}

async function createResearchTopicFromContribution(upload) {
  const topicName = (topicSuggestionNames.value[upload.upload_id] || '').trim();
  if (!topicName) return;
  topicDecisionBusy.value = true;
  error.value = '';
  try {
    const context = await gitService.setContributionResearchTopic(
      currentProjectName.value,
      upload.upload_id,
      { topic_id: null, new_topic_name: topicName }
    );
    await Promise.all([fetchPendingUploads(false), loadResearchTopics()]);
    eventMessages.addMessage(
      context.declared_topic_name === topicName
        ? 'Research topic created and assigned.'
        : `Matched and assigned the existing topic “${context.declared_topic_name}”.`,
      'success'
    );
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The research topic could not be created.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    topicDecisionBusy.value = false;
  }
}

async function fetchReviewCount() {
  if (!currentProject.value?.project_id) {
    activeReviewCount.value = 0;
    reviewCases.value = [];
    return;
  }
  try {
    const cases = await reviewService.list(currentProject.value.project_id);
    reviewCases.value = cases;
    activeReviewCount.value = cases.filter(
      (item) => !['resolved', 'closed'].includes(item.state)
    ).length;
  } catch {
    activeReviewCount.value = 0;
    reviewCases.value = [];
  }
}

async function onReviewCountChange(count) {
  activeReviewCount.value = count;
  await Promise.all([fetchReviewCount(), fetchPendingUploads(false)]);
}

function openLinkedReview(reviewCase) {
  void router.replace({
    query: {
      ...route.query,
      view: 'reviews',
      case: reviewCase.case_id,
      ...(reviewCase.resubmitted_upload_id
        ? { resubmission: reviewCase.resubmitted_upload_id }
        : {}),
    },
  });
}

async function testMerge(upload) {
  try {
    testing.value = upload.upload_id;
    error.value = '';

    const response = await gitService.adminTestMerge(
      currentProjectName.value,
      upload.branch_name
    );

    // Update the upload status in the list
    const index = pendingUploads.value.findIndex(
      (u) => u.upload_id === upload.upload_id
    );
    if (index !== -1) {
      pendingUploads.value[index] = {
        ...pendingUploads.value[index],
        merge_status: response.status,
        conflicted_files: response.conflicted_files || [],
        conflicts_count: response.conflicts_count || 0,
        can_auto_merge: response.can_auto_merge,
        tested_at: response.tested_at,
      };
    }
    eventMessages.addMessage('Compatibility check completed.', 'success');
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.testMergeFailed');
    eventMessages.addMessage(error.value, 'error');
  } finally {
    testing.value = null;
  }
}

async function mergeUpload(upload) {
  if (upload.merge_status !== 'ready_to_merge') {
    error.value = t('pendingUploads.errors.notReadyToMerge');
    return;
  }

  const confirmed = await confirmAction({
    title: t('pendingUploads.mergeConfirmation.title'),
    message: t('pendingUploads.mergeConfirmation.message', {
      branch: `contribution #${upload.upload_id}`,
    }),
    confirmText: t('pendingUploads.actions.mergeNow'),
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;

  try {
    merging.value = upload.upload_id;
    error.value = '';

    await gitService.adminCompleteMerge(
      currentProjectName.value,
      upload.branch_name,
      'auto' // Auto-merge since it's ready
    );

    // Remove the merged upload from the list
    const index = pendingUploads.value.findIndex(
      (u) => u.upload_id === upload.upload_id
    );
    if (index !== -1) {
      pendingUploads.value.splice(index, 1);
    }

    // Refresh all uploads to update status of remaining ones
    await fetchPendingUploads(false);
    eventMessages.addMessage(
      'Contribution merged into the project.',
      'success'
    );
  } catch (e) {
    error.value =
      e?.response?.data?.detail || t('pendingUploads.errors.mergeFailed');
    eventMessages.addMessage(error.value, 'error');
  } finally {
    merging.value = null;
  }
}

async function dismissDuplicate(upload) {
  const confirmed = await confirmAction({
    title: `Dismiss contribution #${upload.upload_id}?`,
    message: `It contains exactly the same project content as contribution #${upload.duplicate_of_upload_id}. Its redundant Git branch will be removed, while the dismissal remains in the audit history.`,
    confirmText: 'Dismiss duplicate',
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;

  dismissing.value = upload.upload_id;
  error.value = '';
  try {
    await gitService.dismissDuplicateUpload(
      currentProjectName.value,
      upload.upload_id
    );
    pendingUploads.value = pendingUploads.value.filter(
      (item) => item.upload_id !== upload.upload_id
    );
    await fetchPendingUploads(false);
    eventMessages.addMessage('Duplicate contribution dismissed.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The duplicate contribution could not be dismissed.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    dismissing.value = null;
  }
}

function openDeclineModal(upload, event) {
  modalTrigger = event?.currentTarget || null;
  selectedUpload.value = upload;
  declineReason.value = '';
  showDeclineModal.value = true;
  void nextTick(() => declineDialog.value?.focus());
}

function closeDeclineModal() {
  if (dismissing.value !== null) return;
  showDeclineModal.value = false;
  declineReason.value = '';
  selectedUpload.value = null;
  void nextTick(() => modalTrigger?.focus());
}

async function declineUpload() {
  const upload = selectedUpload.value;
  const reason = declineReason.value.trim();
  if (!upload || reason.length < 3) return;

  dismissing.value = upload.upload_id;
  error.value = '';
  try {
    await gitService.declinePendingUpload(
      currentProjectName.value,
      upload.upload_id,
      reason
    );
    pendingUploads.value = pendingUploads.value.filter(
      (item) => item.upload_id !== upload.upload_id
    );
    showDeclineModal.value = false;
    selectedUpload.value = null;
    declineReason.value = '';
    await Promise.all([fetchPendingUploads(false), fetchReviewCount()]);
    eventMessages.addMessage('Contribution declined and archived.', 'success');
  } catch (requestError) {
    error.value =
      requestError?.response?.data?.detail ||
      'The contribution could not be declined.';
    eventMessages.addMessage(error.value, 'error');
  } finally {
    dismissing.value = null;
  }
}

function openWorkspace(mode, upload) {
  selectedUpload.value = upload;
  void router.replace({
    query: {
      ...route.query,
      view: 'queue',
      workspace: mode,
      upload: upload.upload_id,
    },
  });
}

function resolveUpload(upload) {
  openWorkspace('resolution', upload);
}

function viewUploadDetails(upload) {
  openWorkspace('details', upload);
}

function requestCorrection(upload) {
  openWorkspace('correction', upload);
}

function closeWorkspace() {
  selectedUpload.value = null;
  const query = { ...route.query };
  delete query.workspace;
  delete query.upload;
  void router.replace({ query });
}

async function onCorrectionCreated(created) {
  selectedUpload.value = null;
  eventMessages.addMessage('Correction request sent.', 'success');
  await fetchReviewCount();
  const query = {
    ...route.query,
    view: 'reviews',
    case: created.case_id,
  };
  delete query.workspace;
  delete query.upload;
  await router.replace({
    query,
  });
}

async function onUploadResolved() {
  closeWorkspace();
  eventMessages.addMessage('Contribution conflicts resolved.', 'success');
  // Refresh the list to show updated status
  await fetchPendingUploads();
}

// Utility functions
function getUploadStatusClass(upload) {
  return {
    'status-ready': upload.merge_status === 'ready_to_merge',
    'status-conflicts': upload.merge_status === 'needs_resolution',
    'status-error': upload.merge_status === 'error',
    'status-pending': [
      'pending_admin_approval',
      'under_review',
      'changes_requested',
      'review_required',
    ].includes(upload.merge_status),
    'status-duplicate': upload.merge_status === 'duplicate',
    'status-superseded': upload.merge_status === 'superseded',
  };
}

function getStatusClass(status) {
  const classes = {
    ready_to_merge: 'ready',
    needs_resolution: 'conflicts',
    error: 'error',
    pending_admin_approval: 'pending',
    under_review: 'pending',
    changes_requested: 'conflicts',
    review_required: 'pending',
    duplicate: 'duplicate',
    superseded: 'superseded',
  };
  return classes[status] || 'pending';
}

function formatStatus(status) {
  const statuses = {
    ready_to_merge: t('pendingUploads.status.readyToMerge'),
    needs_resolution: t('pendingUploads.status.needsResolution'),
    error: t('pendingUploads.status.error'),
    pending_admin_approval: t('pendingUploads.status.pendingReview'),
    under_review: 'Under review',
    changes_requested: 'Waiting for corrections',
    review_required: 'Correction ready for review',
    duplicate: 'Duplicate submission',
    superseded: 'Superseded',
  };
  return statuses[status] || status;
}

function formatUploadType(upload) {
  const kinds = ['new', 'modified', 'deleted'].filter(
    (kind) => upload.files?.[kind]?.length
  );
  if (kinds.length > 1) return 'Mixed file changes';
  if (kinds[0] === 'modified') return 'Modified files';
  if (kinds[0] === 'deleted') return 'Deleted files';
  if (kinds[0] === 'new') return 'New files';

  const type = upload.upload_type;
  const types = {
    pending_upload: t('pendingUploads.uploadTypes.newFiles'),
    upload_with_modifications: t(
      'pendingUploads.uploadTypes.withModifications'
    ),
    upload_with_deletions: t('pendingUploads.uploadTypes.withDeletions'),
  };
  return types[type] || type;
}

function formatDate(dateString) {
  if (!dateString) return t('pendingUploads.unknown');
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString));
}

function protocolCheckClass(upload) {
  const outcome = upload.quality_checks?.protocol;
  if (outcome === 'passed') return 'passed';
  if (outcome === 'recheck_required') return 'recheck-required';
  return 'not-configured';
}

function protocolCheckLabel(upload) {
  const outcome = upload.quality_checks?.protocol;
  if (outcome === 'passed') return 'Project protocol passed';
  if (outcome === 'recheck_required')
    return 'Protocol changed — acceptance will recheck this contribution';
  if (outcome === 'not_configured') return 'No project protocol configured';
  return 'Protocol check not recorded for this older contribution';
}
</script>

<style scoped>
.project-name {
  color: #1976d2;
  font-weight: 600;
}

.select-project-btn {
  display: inline-block;
  margin-top: 16px;
  padding: 12px 24px;
  background: #1976d2;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 500;
  transition: background 0.3s;
}

.select-project-btn:hover {
  background: #1565c0;
}
</style>
