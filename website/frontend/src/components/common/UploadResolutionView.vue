<template>
  <div class="upload-resolution">
    <div class="resolution-header">
      <h3>{{ t('contributionResolution.title') }}</h3>
      <p class="resolution-summary">
        {{
          t(
            'contributionResolution.summary',
            decision.conflictedFiles.value.length
          )
        }}
      </p>
    </div>

    <div class="resolution-content">
      <ReviewCasePanel
        v-if="showCorrectionWorkflow"
        ref="reviewPanel"
        :project-id="projectId"
        :project-name="projectName"
        :upload-id="upload.upload_id"
        :filenames="decision.conflictedFiles.value"
      />
      <section
        v-if="decision.conflictedFiles.value.length > 0"
        class="conflicted-files"
        :aria-labelledby="conflictedTitleId"
      >
        <div class="section-heading">
          <div>
            <span class="step-label">{{
              t('contributionResolution.inspect.step')
            }}</span>
            <h4 :id="conflictedTitleId">
              {{ t('contributionResolution.inspect.title') }}
            </h4>
            <p>{{ t('contributionResolution.inspect.description') }}</p>
          </div>
        </div>
        <div class="files-list">
          <div
            v-for="file in decision.conflictedFiles.value"
            :key="file"
            class="conflict-file-item"
          >
            <div class="file-info">
              <span class="file-name">{{ file }}</span>
              <span class="file-status">{{
                t('contributionResolution.inspect.bothChanged')
              }}</span>
            </div>
            <button
              type="button"
              class="action-btn view-btn"
              :aria-expanded="decision.selectedFile.value === file"
              @click="decision.toggleFile(file)"
            >
              {{
                decision.selectedFile.value === file
                  ? t('contributionResolution.inspect.hide')
                  : t('contributionResolution.inspect.compare')
              }}
            </button>
          </div>
        </div>

        <section
          v-if="decision.selectedFile.value"
          class="inline-comparison"
          aria-live="polite"
        >
          <header>
            <div>
              <span class="step-label">{{
                t('contributionResolution.inspect.comparisonLabel')
              }}</span>
              <h4>{{ decision.selectedFile.value }}</h4>
            </div>
            <button
              type="button"
              class="close-inline"
              @click="decision.toggleFile(decision.selectedFile.value)"
            >
              {{ t('contributionResolution.inspect.closeComparison') }}
            </button>
          </header>
          <ConflictMergeView
            :project-name="projectName"
            :branch-name="upload.branch_name"
            :filename="decision.selectedFile.value"
            allow-open-review
            @open-review="openTargetedReview"
            @loaded="decision.recordComparison"
          />
        </section>
      </section>

      <div class="strategy-section">
        <span class="step-label">{{
          t('contributionResolution.choose.step')
        }}</span>
        <h4>
          {{
            t('contributionResolution.choose.title', { id: upload.upload_id })
          }}
        </h4>
        <div class="strategy-options" role="radiogroup">
          <button
            v-for="option in strategyOptions"
            :key="option.value"
            type="button"
            class="strategy-option"
            role="radio"
            :aria-checked="decision.strategy.value === option.value"
            @click="decision.choose(option.value)"
          >
            <span class="decision-indicator" aria-hidden="true">
              <font-awesome-icon
                v-if="decision.strategy.value === option.value"
                icon="fa-solid fa-check"
              />
            </span>
            <div class="strategy-content">
              <strong>{{ t(option.titleKey) }}</strong>
              <p>{{ t(option.descriptionKey) }}</p>
            </div>
          </button>

          <aside class="correction-path">
            <div class="strategy-content">
              <strong>{{
                t('contributionResolution.choose.correctionTitle')
              }}</strong>
              <p>
                {{ t('contributionResolution.choose.correctionDescription') }}
              </p>
            </div>
            <button
              type="button"
              class="correction-button"
              @click="openCorrectionComposer"
            >
              {{ t('contributionResolution.choose.correctionAction') }}
            </button>
          </aside>
        </div>
      </div>

      <div v-if="decision.otherFileCount.value" class="changes-preview">
        <h4>{{ t('contributionResolution.additional.title') }}</h4>
        <div class="changes-grid">
          <template v-for="group in otherFileGroups" :key="group.kind">
            <div v-if="group.files.length" class="change-group">
              <h5>
                {{ t(group.labelKey, { count: group.files.length }) }}
              </h5>
              <ul class="change-list">
                <li v-for="file in group.files.slice(0, 5)" :key="file">
                  {{ file }}
                </li>
                <li v-if="group.files.length > 5" class="more-files">
                  {{
                    t('contributionResolution.additional.more', {
                      count: group.files.length - 5,
                    })
                  }}
                </li>
              </ul>
            </div>
          </template>
        </div>
      </div>

      <div class="resolution-actions">
        <div v-if="decision.strategy.value" class="decision-confirmation">
          <header>
            <div>
              <span class="step-label">{{
                t('contributionResolution.confirm.step')
              }}</span>
              <h4>{{ t(chosen.titleKey) }}</h4>
            </div>
            <button
              type="button"
              class="clear-decision"
              @click="decision.clear()"
            >
              {{ t('contributionResolution.confirm.clear') }}
            </button>
          </header>
          <p class="decision-consequence">{{ t(chosen.consequenceKey) }}</p>
          <p
            v-if="decision.otherFileCount.value"
            class="decision-consequence other-files-consequence"
          >
            {{
              t(
                'contributionResolution.confirm.otherFiles',
                decision.otherFileCount.value
              )
            }}
            <strong v-if="decision.otherFiles.value.deleted.length">
              {{
                t(
                  'contributionResolution.confirm.otherDeletions',
                  decision.otherFiles.value.deleted.length
                )
              }}
            </strong>
          </p>
          <p v-if="impactSummary" class="decision-impact">
            <strong>{{
              t('contributionResolution.confirm.impactLabel')
            }}</strong>
            {{ t(chosen.impactKey, { summary: impactSummary }) }}
          </p>
          <p
            v-else-if="decision.conflictedFiles.value.length"
            class="decision-impact partial-impact"
          >
            {{
              t('contributionResolution.confirm.impactPartial', {
                compared: decision.comparedCount.value,
                total: decision.conflictedFiles.value.length,
              })
            }}
          </p>
          <i18n-t
            keypath="contributionResolution.confirm.completion"
            tag="p"
            class="completion-note"
          >
            <template #id>{{ upload.upload_id }}</template>
            <template #link>
              <router-link :to="incomingWorkRoute">{{
                t('contributionResolution.confirm.incomingWork')
              }}</router-link>
            </template>
          </i18n-t>
          <label>
            <input v-model="decision.acknowledged.value" type="checkbox" />
            {{ t(chosen.acknowledgementKey) }}
          </label>
        </div>
        <button
          type="button"
          class="action-btn resolve-btn"
          :disabled="!decision.canApply.value || resolving"
          @click="applyResolution"
        >
          {{
            resolving
              ? t('contributionResolution.actions.working')
              : t(chosen.actionKey, { id: upload.upload_id })
          }}
        </button>

        <button
          type="button"
          class="action-btn cancel-btn"
          @click="$emit('cancelled')"
        >
          {{ t('contributionResolution.actions.cancel') }}
        </button>
      </div>

      <div v-if="resolving" class="resolution-progress" role="status">
        <p class="progress-text">
          {{ t('contributionResolution.actions.working') }}
        </p>
      </div>
    </div>

    <div v-if="error" class="error-message" role="alert">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { computed, nextTick, ref, toRef, useId } from 'vue';
import { useI18n } from 'vue-i18n';
import gitService from '@/api/service/gitService';
import ConflictMergeView from '@/components/common/ConflictMergeView.vue';
import ReviewCasePanel from '@/components/common/ReviewCasePanel.vue';
import {
  RESOLUTION_STRATEGIES,
  useResolutionDecision,
} from '@/composables/useResolutionDecision';
import { reportClientError } from '@/utils/errorDiagnostics';

const props = defineProps({
  projectId: { type: Number, required: true },
  projectName: { type: String, required: true },
  upload: { type: Object, required: true },
});

const emit = defineEmits(['resolved', 'cancelled']);

const KNOWN_IMPACT_KINDS = new Set([
  'added',
  'removed',
  'value_changed',
  'tier_changed',
  'timing_changed',
]);

const { t, locale } = useI18n();
const decision = useResolutionDecision(toRef(props, 'upload'));
const resolving = ref(false);
const error = ref('');
const showCorrectionWorkflow = ref(false);
const reviewPanel = ref(null);
const conflictedTitleId = `conflicted-files-title-${useId()}`;

const strategyOptions = [
  {
    value: RESOLUTION_STRATEGIES.incoming,
    titleKey: 'contributionResolution.choose.incomingTitle',
    descriptionKey: 'contributionResolution.choose.incomingDescription',
  },
  {
    value: RESOLUTION_STRATEGIES.current,
    titleKey: 'contributionResolution.choose.currentTitle',
    descriptionKey: 'contributionResolution.choose.currentDescription',
  },
];

const chosen = computed(() =>
  decision.strategy.value === RESOLUTION_STRATEGIES.incoming
    ? {
        titleKey: 'contributionResolution.confirm.incomingTitle',
        consequenceKey: 'contributionResolution.confirm.incomingConsequence',
        acknowledgementKey:
          'contributionResolution.confirm.acknowledgeIncoming',
        impactKey: 'contributionResolution.confirm.impactApply',
        actionKey: 'contributionResolution.actions.merge',
      }
    : {
        titleKey: 'contributionResolution.confirm.currentTitle',
        consequenceKey: 'contributionResolution.confirm.currentConsequence',
        acknowledgementKey: 'contributionResolution.confirm.acknowledgeCurrent',
        impactKey: 'contributionResolution.confirm.impactDiscard',
        actionKey: 'contributionResolution.actions.keepCurrent',
      }
);

const otherFileGroups = computed(() => [
  {
    kind: 'new',
    labelKey: 'contributionResolution.additional.new',
    files: decision.otherFiles.value.new,
  },
  {
    kind: 'modified',
    labelKey: 'contributionResolution.additional.modified',
    files: decision.otherFiles.value.modified,
  },
  {
    kind: 'deleted',
    labelKey: 'contributionResolution.additional.deleted',
    files: decision.otherFiles.value.deleted,
  },
]);

const incomingWorkRoute = computed(() => ({
  path: '/contribution',
  query: { project: props.projectId, view: 'queue' },
}));

const impactSummary = computed(() => {
  const counts = new Map();
  for (const { kind, count } of decision.impact.value) {
    const key = KNOWN_IMPACT_KINDS.has(kind) ? kind : 'other';
    counts.set(key, (counts.get(key) || 0) + count);
  }
  if (!counts.size) return '';
  const parts = [...counts].map(([kind, count]) =>
    t(`contributionResolution.impactKinds.${kind}`, count)
  );
  return new Intl.ListFormat(locale.value, {
    style: 'long',
    type: 'conjunction',
  }).format(parts);
});

async function applyResolution() {
  if (!decision.canApply.value) {
    error.value = t('contributionResolution.errors.chooseOutcome');
    return;
  }
  resolving.value = true;
  error.value = '';
  try {
    const result = await gitService.adminCompleteMerge(
      props.projectName,
      props.upload.branch_name,
      decision.strategy.value
    );
    emit('resolved', result);
  } catch (requestError) {
    error.value = apiErrorMessage(
      requestError,
      t,
      t('contributionResolution.errors.failed')
    );
    reportClientError('Resolution error', requestError);
  } finally {
    resolving.value = false;
  }
}

function openTargetedReview(target) {
  reviewPanel.value?.openComposer(target);
}

async function openCorrectionComposer() {
  decision.clear();
  showCorrectionWorkflow.value = true;
  await nextTick();
  reviewPanel.value?.openComposer();
}
</script>



<style scoped>
.upload-resolution {
  padding: 20px 0;
}

.resolution-header {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border);
}

.resolution-header h3 {
  margin: 0 0 10px;
  color: var(--color-text);
}

.resolution-summary {
  margin: 0;
  color: var(--color-text-muted);
}

.loading {
  text-align: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid var(--color-border);
  border-top: 4px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.strategy-section {
  margin-bottom: 30px;
}

.strategy-section h4 {
  margin: 0 0 15px;
  color: var(--color-text);
}

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.strategy-option {
  display: flex;
  position: relative;
  align-items: flex-start;
  width: 100%;
  gap: 12px;
  padding: 16px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  color: inherit;
  background: var(--color-surface);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease;
}

.strategy-option[aria-checked='true'] {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.decision-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 1.15rem;
  height: 1.15rem;
  margin-top: 0.15rem;
  border: 1.5px solid var(--color-gray-600);
  border-radius: 50%;
  color: white;
  background: white;
  font-size: 0.72rem;
  font-weight: 800;
}

.strategy-option:hover {
  border-color: var(--color-primary-light);
}

.strategy-option[aria-checked='true'] .decision-indicator {
  border-color: var(--color-primary);
  background: var(--color-primary);
}

.strategy-option[aria-checked='true'] .strategy-content {
  color: var(--color-primary-light);
}

.strategy-content strong {
  display: block;
  margin-bottom: 4px;
}

.strategy-content p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.correction-path {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.correction-button,
.close-inline {
  flex: none;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-sm);
  color: var(--color-accent-dark);
  background: var(--color-surface);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.step-label {
  display: inline-block;
  margin-bottom: 0.35rem;
  color: var(--color-primary-dark);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.section-heading h4,
.section-heading p {
  margin: 0;
}

.section-heading p {
  margin-top: 0.25rem;
  color: var(--color-text-muted);
}

.conflicted-files {
  margin-bottom: 30px;
  padding: 20px;
  background: var(--color-warning-bg);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--color-warning);
}

.conflicted-files h4 {
  color: var(--color-text);
}

.files-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.conflict-file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-family: monospace;
  font-weight: 500;
}

.file-status {
  font-size: 0.8rem;
  color: var(--color-warning);
}

.inline-comparison {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--color-info);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.inline-comparison > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid var(--color-info-bg);
}

.inline-comparison > header h4 {
  margin: 0;
  overflow-wrap: anywhere;
}

.inline-comparison :deep(.review-list) {
  max-height: none;
  overflow: visible;
}

.changes-preview {
  margin-bottom: 30px;
}

.changes-preview h4 {
  margin: 0 0 15px;
  color: var(--color-text);
}

.changes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.change-group h5 {
  margin: 0 0 10px;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.change-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.change-list li {
  padding: 4px 0;
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--color-text);
}

.more-files {
  color: var(--color-text-muted);
  font-style: italic;
}

.resolution-actions {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 20px;
}

.decision-confirmation {
  flex: 1 0 100%;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-subtle);
}

.decision-confirmation > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.decision-confirmation h4,
.decision-confirmation p {
  margin: 0 0 0.5rem;
}

.clear-decision {
  flex: none;
  padding: 0.35rem 0.55rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  background: var(--color-surface);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.decision-consequence {
  color: var(--color-text-muted);
}

.decision-confirmation .decision-impact {
  margin: 0.75rem 0;
  padding: 0.7rem 0.8rem;
  border-left: 3px solid var(--color-primary);
  background: var(--color-surface);
}

.completion-note {
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.completion-note a {
  color: var(--color-primary-dark);
  font-weight: 700;
}

.decision-confirmation label {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border-subtle);
  font-weight: 700;
}

.decision-confirmation input {
  flex: none;
  width: 1rem;
  height: 1rem;
  margin-top: 0.15rem;
}

.action-btn {
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s;
}

.resolve-btn {
  background: var(--color-success);
  color: white;
}

.resolve-btn:disabled {
  background: var(--color-gray-300);
  cursor: not-allowed;
}

.cancel-btn {
  background: var(--color-text-muted);
  color: white;
}

.view-btn {
  background: var(--color-info);
  color: white;
  padding: 8px 16px;
  font-size: 0.8rem;
}

.resolution-progress {
  margin-top: 20px;
}

.progress-text {
  margin: 0;
  text-align: center;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.error-message {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error);
  color: var(--color-error);
  padding: 16px;
  border-radius: var(--radius-md);
  margin-top: 20px;
}

@media (width <= 700px) {
  .conflict-file-item,
  .correction-path,
  .inline-comparison > header,
  .decision-confirmation > header {
    align-items: stretch;
    flex-direction: column;
  }

  .view-btn,
  .correction-button,
  .close-inline,
  .clear-decision,
  .resolution-actions > .action-btn {
    width: 100%;
  }
}
</style>
