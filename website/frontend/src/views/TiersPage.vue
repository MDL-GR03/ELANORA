<template>
  <div class="tiers-page">
    <WorkspaceHeader
      :title="t('researchScopes.title')"
      :context="currentProject?.project_name || ''"
      :description="t('researchScopes.description')"
    />
    <section class="tiers-workspace" :aria-busy="loading || operationPending">
      <nav
        class="tiers-mode-tabs"
        role="tablist"
        :aria-label="t('researchScopes.workspaceLabel')"
      >
        <button
          id="research-copy-tab"
          type="button"
          role="tab"
          :aria-selected="activeMode === 'export'"
          aria-controls="research-copy-panel"
          :tabindex="activeMode === 'export' ? 0 : -1"
          :class="{ 'is-active': activeMode === 'export' }"
          @click="activeMode = 'export'"
          @keydown="onModeTabKeydown"
        >
          {{ t('researchScopes.tabs.prepare') }}
        </button>
        <button
          id="research-topics-tab"
          type="button"
          role="tab"
          :aria-selected="activeMode === 'topics'"
          aria-controls="research-topics-panel"
          :tabindex="activeMode === 'topics' ? 0 : -1"
          :class="{ 'is-active': activeMode === 'topics' }"
          @click="activeMode = 'topics'"
          @keydown="onModeTabKeydown"
        >
          {{ t('researchScopes.tabs.topics') }}
          <span v-if="topics.length" class="tiers-tab-count">{{
            topics.length
          }}</span>
        </button>
      </nav>
      <div v-if="loading" class="tiers-state-panel">
        {{ t('researchScopes.loading') }}
      </div>
      <div
        v-else-if="error"
        class="tiers-state-panel tiers-state-panel--error"
        role="alert"
      >
        {{ error }}
      </div>

      <div
        v-else-if="activeMode === 'export'"
        id="research-copy-panel"
        class="tier-export-workspace"
        role="tabpanel"
        aria-labelledby="research-copy-tab"
      >
        <div v-if="topicLoadError" class="tiers-operation-error" role="alert">
          {{ topicLoadError }}
        </div>
        <header class="tier-export-intro">
          <div>
            <span class="tier-export-eyebrow">{{
              t('researchScopes.prepare.eyebrow')
            }}</span>
            <h2>{{ t('researchScopes.prepare.title') }}</h2>
            <p>{{ t('researchScopes.prepare.description') }}</p>
          </div>
          <div class="tier-export-safety">
            <font-awesome-icon icon="fa-solid fa-shield-halved" />
            <span>
              <strong>{{ t('researchScopes.prepare.safetyTitle') }}</strong>
              <small>{{ t('researchScopes.prepare.safetyText') }}</small>
            </span>
          </div>
        </header>
        <div v-if="!tierGroups.length" class="tiers-state-panel">
          {{ t('researchScopes.prepare.noFiles') }}
        </div>
        <div v-else class="research-copy-steps">
          <section class="research-step">
            <StepTitle
              number="1"
              :title="t('researchScopes.prepare.topicStepTitle')"
              :text="t('researchScopes.prepare.topicStepText')"
            />
            <div class="topic-choice-grid">
              <button
                type="button"
                :class="{ 'is-active': selectedTopicId === null }"
                @click="applyTopic(null)"
              >
                <strong>{{ t('researchScopes.prepare.custom') }}</strong
                ><small>{{ t('researchScopes.prepare.customHint') }}</small>
              </button>
              <button
                v-for="topic in topics"
                :key="topic.topic_id"
                type="button"
                :class="{ 'is-active': selectedTopicId === topic.topic_id }"
                @click="applyTopic(topic)"
              >
                <strong>{{ topic.name }}</strong
                ><small>{{
                  t('researchScopes.matchingFiles', {
                    count: matchingFileCount(topic),
                  })
                }}</small>
              </button>
            </div>
          </section>
          <section class="research-step">
            <StepTitle
              number="2"
              :title="t('researchScopes.prepare.fileStepTitle')"
              :text="
                selectedTopic
                  ? t('researchScopes.prepare.fileStepRanked')
                  : t('researchScopes.prepare.fileStepText')
              "
            />
            <div class="research-file-picker">
              <div class="research-file-browser">
                <label class="research-file-search">
                  <font-awesome-icon icon="fa-solid fa-magnifying-glass" />
                  <span class="sr-only">{{
                    t('researchScopes.searchFiles')
                  }}</span>
                  <input
                    v-model="fileSearch"
                    :placeholder="t('researchScopes.searchFiles')"
                  />
                </label>
                <div class="research-file-list">
                  <button
                    v-for="group in visibleRankedGroups"
                    :key="group.tier_group_id"
                    type="button"
                    :class="{
                      'is-selected': selectedGroupId === group.tier_group_id,
                    }"
                    @click="selectGroup(group)"
                  >
                    <span
                      ><strong>{{ group.elan_file_name }}</strong
                      ><small>{{
                        selectedTopic
                          ? t('researchScopes.topicTierCoverage', {
                              available: groupTopicCoverage(
                                group,
                                selectedTopic
                              ),
                              total: selectedTopic.tier_names.length,
                            })
                          : t('researchScopes.tierCount', {
                              count: countTiers(group.tiers),
                            })
                      }}</small></span
                    >
                    <span
                      v-if="uniqueBestGroupId === group.tier_group_id"
                      class="research-file-list__recommended"
                      >{{ t('researchScopes.bestMatch') }}</span
                    >
                    <font-awesome-icon
                      v-if="selectedGroupId === group.tier_group_id"
                      icon="fa-solid fa-check"
                      class="research-file-list__check"
                    />
                  </button>
                </div>
                <div
                  v-if="!visibleRankedGroups.length"
                  class="research-file-empty"
                >
                  {{ t('researchScopes.noSearchResults') }}
                </div>
                <footer
                  v-if="filteredRankedGroups.length"
                  class="research-file-pagination"
                  :aria-label="t('researchScopes.pagination.label')"
                >
                  <span>{{ fileResultRange }}</span>
                  <div v-if="filePageCount > 1">
                    <button
                      type="button"
                      :disabled="filePage === 1"
                      :aria-label="t('researchScopes.pagination.previousLabel')"
                      @click="filePage -= 1"
                    >
                      {{ t('researchScopes.pagination.previous') }}
                    </button>
                    <span>{{
                      t('researchScopes.pagination.page', {
                        page: filePage,
                        total: filePageCount,
                      })
                    }}</span>
                    <button
                      type="button"
                      :disabled="filePage === filePageCount"
                      :aria-label="t('researchScopes.pagination.nextLabel')"
                      @click="filePage += 1"
                    >
                      {{ t('researchScopes.pagination.next') }}
                    </button>
                  </div>
                </footer>
              </div>
            </div>
            <div v-if="selectedTopic" class="topic-coverage">
              <div>
                <strong>{{
                  t('researchScopes.topicInFile', {
                    topic: selectedTopic.name,
                    file: selectedGroup?.elan_file_name,
                  })
                }}</strong
                ><span>{{
                  selectedTopic.description || t('researchScopes.noDescription')
                }}</span>
              </div>
              <span
                v-if="missingTopicTiers.length"
                class="topic-coverage__missing"
                >{{
                  t('researchScopes.coverageMissing', {
                    available: topicCoverage(selectedTopic),
                    total: selectedTopic.tier_names.length,
                    missing: missingTopicTiers.join(', '),
                  })
                }}</span
              ><span v-else class="topic-coverage__complete">{{
                t('researchScopes.coverageComplete')
              }}</span>
            </div>
          </section>
          <section class="research-step research-step--tiers">
            <div class="research-step__heading">
              <StepTitle
                number="3"
                :title="t('researchScopes.prepare.tierStepTitle')"
                :text="t('researchScopes.prepare.tierStepText')"
              />
              <div class="tier-export-selection__shortcuts">
                <button type="button" @click="selectAllTiers">
                  {{ t('researchScopes.selectAll') }}</button
                ><button type="button" @click="clearSelectedTiers">
                  {{ t('researchScopes.clear') }}
                </button>
              </div>
            </div>
            <section
              v-if="availableBaselineTiers.length"
              class="copy-baseline-options"
            >
              <header>
                <font-awesome-icon icon="fa-solid fa-shield-halved" />
                <div>
                  <strong>{{ t('researchScopes.baseline.copyTitle') }}</strong>
                  <span>{{ t('researchScopes.baseline.copyText') }}</span>
                </div>
                <button type="button" @click="toggleAllBaselineContext">
                  {{
                    allBaselineIncluded
                      ? t('researchScopes.baseline.removeAll')
                      : t('researchScopes.baseline.includeAll')
                  }}
                </button>
              </header>
              <div class="copy-baseline-list">
                <div v-for="name in availableBaselineTiers" :key="name">
                  <label>
                    <input
                      type="checkbox"
                      :checked="includedBaselineNames.has(name)"
                      @change="toggleIncludedBaseline(name)"
                    />
                    <span>{{ name }}</span>
                  </label>
                  <label class="baseline-correction-choice">
                    <input
                      type="checkbox"
                      :checked="editableBaselineNames.has(name)"
                      @change="toggleEditableBaseline(name)"
                    />
                    {{ t('researchScopes.baseline.proposeCorrection') }}
                  </label>
                </div>
              </div>
              <p
                v-if="editableBaselineNames.size"
                class="baseline-edit-warning"
              >
                <font-awesome-icon icon="fa-solid fa-circle-info" />
                {{ t('researchScopes.baseline.correctionWarning') }}
              </p>
            </section>
            <div class="tier-export-tree-panel">
              <TierSelectionTree
                v-if="selectedGroup"
                root
                :tiers="selectedGroup.tiers"
                :selected-names="selectedTierNames"
                :automatic-names="automaticParentNames"
                :context-names="protectedBaselineNames"
                :correction-names="editableBaselineNames"
                @toggle="toggleTier"
              />
            </div>
            <footer class="tier-export-footer">
              <div>
                <strong>{{
                  t('researchScopes.selectedResearchTiers', {
                    count: selectedTierNames.size,
                  })
                }}</strong
                ><span>{{
                  selectedTopic
                    ? t('researchScopes.usingTopic', {
                        topic: selectedTopic.name,
                      })
                    : t('researchScopes.customWorkingScope')
                }}</span>
              </div>
              <button
                type="button"
                class="tiers-primary-button"
                :disabled="
                  (!selectedTierNames.size && !editableBaselineNames.size) ||
                  exportPending
                "
                @click="downloadResearchCopy"
              >
                <font-awesome-icon icon="fa-solid fa-download" />{{
                  exportPending
                    ? t('researchScopes.preparing')
                    : t('researchScopes.download')
                }}
              </button>
            </footer>
          </section>
        </div>
        <div class="tier-export-roundtrip">
          <strong>{{ t('researchScopes.roundtrip.title') }}</strong
          ><span>{{ t('researchScopes.roundtrip.text') }}</span>
        </div>
      </div>

      <div
        v-else
        id="research-topics-panel"
        class="topics-workspace"
        role="tabpanel"
        aria-labelledby="research-topics-tab"
      >
        <div v-if="topicLoadError" class="tiers-operation-error" role="alert">
          {{ topicLoadError }}
        </div>
        <header class="topics-intro">
          <div>
            <span class="tier-export-eyebrow">{{
              t('researchScopes.topics.eyebrow')
            }}</span>
            <h2>{{ t('researchScopes.topics.title') }}</h2>
            <p>{{ t('researchScopes.topics.description') }}</p>
          </div>
          <button
            v-if="canManageTopics && !editingTopic"
            class="tiers-primary-button"
            type="button"
            @click="startCreate"
          >
            <font-awesome-icon icon="fa-solid fa-plus" />
            {{ t('researchScopes.topics.create') }}
          </button>
        </header>
        <section class="baseline-tier-card">
          <header>
            <span class="topic-card__icon">
              <font-awesome-icon icon="fa-solid fa-shield-halved" />
            </span>
            <div>
              <h3>{{ t('researchScopes.baseline.title') }}</h3>
              <p>{{ t('researchScopes.baseline.description') }}</p>
            </div>
            <button
              v-if="canManageTopics"
              type="button"
              class="topic-action-button"
              :aria-label="
                baselineEditing
                  ? t('researchScopes.baseline.cancelEditing')
                  : t('researchScopes.baseline.edit')
              "
              :title="
                baselineEditing
                  ? t('common.cancel')
                  : t('researchScopes.baseline.edit')
              "
              @click="toggleBaselineEditor"
            >
              <font-awesome-icon
                :icon="
                  baselineEditing
                    ? 'fa-solid fa-xmark'
                    : 'fa-regular fa-pen-to-square'
                "
              />
            </button>
          </header>
          <div v-if="baselineTiers.length" class="baseline-tier-chips">
            <span v-for="name in baselineTiers" :key="name">{{ name }}</span>
          </div>
          <p v-else class="baseline-tier-empty">
            {{ t('researchScopes.baseline.empty') }}
          </p>
          <form v-if="baselineEditing" @submit.prevent="saveBaselineTiers">
            <p>
              {{ t('researchScopes.baseline.editorHint') }}
            </p>
            <div class="topic-tier-picker">
              <label v-for="name in allTierNames" :key="name">
                <input
                  type="checkbox"
                  :checked="baselineForm.has(name)"
                  @change="toggleBaselineTier(name)"
                />
                <span>{{ name }}</span>
                <small>{{
                  t('researchScopes.fileCount', {
                    count: tierFileCount(name),
                  })
                }}</small>
              </label>
            </div>
            <footer>
              <span>{{
                t('researchScopes.baseline.selected', {
                  count: baselineForm.size,
                })
              }}</span>
              <button
                type="submit"
                class="tiers-primary-button"
                :disabled="operationPending"
              >
                {{
                  operationPending
                    ? t('common.saving')
                    : t('researchScopes.baseline.save')
                }}
              </button>
            </footer>
          </form>
        </section>
        <div v-if="operationError" class="tiers-operation-error" role="alert">
          {{ operationError }}
        </div>
        <form
          v-if="editingTopic"
          class="topic-editor"
          @submit.prevent="saveTopic"
        >
          <header>
            <div>
              <span class="tier-export-eyebrow">{{
                topicForm.topic_id
                  ? t('researchScopes.topics.editEyebrow')
                  : t('researchScopes.topics.newEyebrow')
              }}</span>
              <h3>{{ t('researchScopes.topics.editorTitle') }}</h3>
            </div>
            <button type="button" class="topic-link-button" @click="cancelEdit">
              {{ t('common.cancel') }}
            </button>
          </header>
          <div class="topic-fields">
            <label
              ><span>{{ t('researchScopes.topics.name') }}</span
              ><input
                v-model.trim="topicForm.name"
                required
                maxlength="100"
                :placeholder="
                  t('researchScopes.topics.namePlaceholder')
                " /></label
            ><label
              ><span>{{ t('researchScopes.topics.explanation') }}</span
              ><textarea
                v-model.trim="topicForm.description"
                maxlength="1000"
                rows="2"
                :placeholder="t('researchScopes.topics.explanationPlaceholder')"
              />
            </label>
          </div>
          <label class="topic-search"
            ><span>{{ t('researchScopes.topics.findTiers') }}</span
            ><input
              v-model="tierSearch"
              :placeholder="t('researchScopes.topics.findTiersPlaceholder')"
          /></label>
          <div class="topic-tier-picker">
            <label v-for="name in filteredTierNames" :key="name"
              ><input
                type="checkbox"
                :checked="topicForm.tier_names.has(name)"
                @change="toggleTopicTier(name)"
              /><span>{{ name }}</span
              ><small>{{
                t('researchScopes.fileCount', { count: tierFileCount(name) })
              }}</small></label
            >
          </div>
          <label class="topic-new-tier-policy"
            ><input v-model="topicForm.allow_new_tiers" type="checkbox" /><span
              ><strong>{{ t('researchScopes.topics.allowNew') }}</strong
              ><small>{{
                t('researchScopes.topics.allowNewHint')
              }}</small></span
            ></label
          >
          <footer>
            <span>{{
              t('researchScopes.topics.selected', {
                count: topicForm.tier_names.size,
              })
            }}</span
            ><button
              class="tiers-primary-button"
              type="submit"
              :disabled="
                !topicForm.name ||
                !topicForm.tier_names.size ||
                operationPending
              "
            >
              {{
                operationPending
                  ? t('common.saving')
                  : t('researchScopes.topics.save')
              }}
            </button>
          </footer>
        </form>
        <div v-if="!topics.length && !editingTopic" class="topics-empty">
          <font-awesome-icon icon="fa-solid fa-layer-group" />
          <h3>{{ t('researchScopes.topics.emptyTitle') }}</h3>
          <p>{{ t('researchScopes.topics.emptyText') }}</p>
        </div>
        <div v-else-if="!editingTopic" class="topic-card-grid">
          <article
            v-for="topic in topics"
            :key="topic.topic_id"
            class="topic-card"
          >
            <div class="topic-card__summary">
              <div class="topic-card__icon">
                <font-awesome-icon icon="fa-solid fa-layer-group" />
              </div>
              <div class="topic-card__content">
                <h3>
                  {{ topic.name }}
                  <span
                    v-if="topic.allow_new_tiers"
                    class="topic-policy-badge"
                    >{{ t('researchScopes.topics.newTiersAllowed') }}</span
                  >
                </h3>
                <p>
                  {{ topic.description || t('researchScopes.noDescription') }}
                </p>
                <div class="topic-card__metrics">
                  <span
                    ><strong>{{ topic.tier_names.length }}</strong> research
                    tier(s)</span
                  ><span
                    ><strong>{{ matchingFileCount(topic) }}</strong> matching
                    file(s)</span
                  ><span
                    ><strong>{{ matchingFileCount(topic) }}</strong> of
                    {{ tierGroups.length }} EAF files contain at least one
                    selected tier</span
                  >
                </div>
              </div>
              <div class="topic-card__actions">
                <button
                  type="button"
                  class="topic-use-button"
                  @click="useTopic(topic)"
                >
                  {{ t('researchScopes.topics.prepareCopy') }}</button
                ><button
                  v-if="canManageTopics"
                  type="button"
                  class="topic-action-button"
                  :title="t('researchScopes.topics.edit')"
                  :aria-label="t('researchScopes.topics.edit')"
                  @click="startEdit(topic)"
                >
                  <font-awesome-icon
                    icon="fa-regular fa-pen-to-square"
                  /></button
                ><button
                  v-if="canManageTopics"
                  type="button"
                  class="topic-action-button is-danger"
                  :title="t('researchScopes.topics.delete')"
                  :aria-label="t('researchScopes.topics.delete')"
                  @click="removeTopic(topic)"
                >
                  <font-awesome-icon icon="trash" />
                </button>
              </div>
            </div>
            <button
              type="button"
              class="topic-coverage-toggle"
              :aria-expanded="expandedTopicId === topic.topic_id"
              @click="toggleTopicCoverage(topic)"
            >
              <span>{{
                expandedTopicId === topic.topic_id
                  ? t('researchScopes.topics.hideCoverage')
                  : t('researchScopes.topics.viewCoverage')
              }}</span
              ><font-awesome-icon
                :icon="
                  expandedTopicId === topic.topic_id
                    ? 'fa-solid fa-chevron-up'
                    : 'fa-solid fa-chevron-down'
                "
              />
            </button>
            <div
              v-if="expandedTopicId === topic.topic_id"
              class="topic-coverage-panel"
            >
              <label class="topic-coverage-search"
                ><span class="sr-only">{{
                  t('researchScopes.topics.searchInTopic', {
                    topic: topic.name,
                  })
                }}</span
                ><font-awesome-icon icon="fa-solid fa-magnifying-glass" /><input
                  v-model="coverageSearch"
                  :placeholder="t('researchScopes.searchFiles')"
              /></label>
              <div class="topic-tier-summary">
                <span v-for="name in topic.tier_names.slice(0, 12)" :key="name"
                  >{{ name }}
                  <small>{{
                    t('researchScopes.fileCount', {
                      count: tierFiles(name).length,
                    })
                  }}</small></span
                >
                <span v-if="topic.tier_names.length > 12">
                  {{
                    t('researchScopes.topics.moreTiers', {
                      count: topic.tier_names.length - 12,
                    })
                  }}
                </span>
              </div>
              <div
                v-if="!visibleCoverageRows(topic).length"
                class="topic-coverage-empty"
              >
                {{ t('researchScopes.topics.noMatchingFiles') }}
              </div>
              <div v-else class="topic-file-coverage-list">
                <div
                  v-for="row in visibleCoverageRows(topic)"
                  :key="row.filename"
                  class="topic-file-coverage-row"
                >
                  <div>
                    <strong>{{ row.filename }}</strong
                    ><span>{{
                      t('researchScopes.topicTierCoverage', {
                        available: row.matches.length,
                        total: topic.tier_names.length,
                      })
                    }}</span>
                  </div>
                  <div
                    class="topic-file-coverage-bar"
                    :aria-label="
                      t('researchScopes.topics.coverageAria', {
                        available: row.matches.length,
                        total: topic.tier_names.length,
                      })
                    "
                  >
                    <span :style="{ width: `${row.percent}%` }" />
                  </div>
                  <div class="topic-file-tier-names">
                    <span v-for="name in row.matches.slice(0, 3)" :key="name">{{
                      name
                    }}</span
                    ><small v-if="row.matches.length > 3"
                      >+{{ row.matches.length - 3 }}</small
                    >
                  </div>
                </div>
              </div>
              <button
                v-if="filteredCoverageRows(topic).length > coverageLimit"
                type="button"
                class="topic-show-more"
                @click="coverageLimit += 10"
              >
                {{
                  t('researchScopes.topics.showMoreFiles', {
                    count: Math.min(
                      10,
                      filteredCoverageRows(topic).length - coverageLimit
                    ),
                  })
                }}
              </button>
            </div>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import '@/assets/css/tiers.css';
import {
  computed,
  defineComponent,
  h,
  onMounted,
  reactive,
  ref,
  watch,
} from 'vue';
import { useHead } from '@unhead/vue';
import { useI18n } from 'vue-i18n';
import {
  createResearchTopic,
  deleteResearchTopic,
  exportTierSubset,
  fetchResearchTopics,
  fetchProjectBaselineTiers,
  fetchSectionsAndGroups,
  updateResearchTopic,
  updateProjectBaselineTiers,
} from '@/api/service/tierService';
import TierSelectionTree from '@/components/pageSpecific/tiers/TierSelectionTree.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';

const StepTitle = defineComponent({
  props: {
    number: { type: String, required: true },
    title: { type: String, required: true },
    text: { type: String, required: true },
  },
  setup: (p) => () =>
    h('div', { class: 'research-step__title' }, [
      h('span', p.number),
      h('div', [h('h3', p.title), h('p', p.text)]),
    ]),
});
const projectStore = useProjectStore();
const { t } = useI18n();
const userStore = useUserStore();
const messages = useEventMessageStore();
const confirmAction = useUserConfirm();
useHead({ title: t('researchScopes.title') });
const currentProject = computed(() => projectStore.currentProject);
const canManageTopics = computed(
  () =>
    userStore.user?.role === 'admin' ||
    ['admin', 'owner'].includes(projectStore.currentPermission)
);
const tierGroups = ref([]);
const topics = ref([]);
const baselineTiers = ref([]);
const baselineEditing = ref(false);
const baselineForm = ref(new Set());
const loading = ref(true);
const error = ref('');
const operationError = ref('');
const topicLoadError = ref('');
const operationPending = ref(false);
const exportPending = ref(false);
const activeMode = ref('export');
const selectedGroupId = ref(null);
const selectedTopicId = ref(null);
const selectedTierNames = ref(new Set());
const includedBaselineNames = ref(new Set());
const editableBaselineNames = ref(new Set());
const editingTopic = ref(false);
const tierSearch = ref('');
const fileSearch = ref('');
const filePage = ref(1);
const filePageSize = 10;
let loadRequest = 0;
const topicForm = reactive({
  topic_id: null,
  name: '',
  description: '',
  tier_names: new Set(),
  allow_new_tiers: false,
});
const expandedTopicId = ref(null);
const coverageSearch = ref('');
const coverageLimit = ref(10);

function onModeTabKeydown(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const targetMode =
    event.key === 'ArrowLeft' || event.key === 'Home' ? 'export' : 'topics';
  activeMode.value = targetMode;
  const targetId =
    targetMode === 'export' ? 'research-copy-tab' : 'research-topics-tab';
  document.getElementById(targetId)?.focus();
}
const selectedGroup = computed(() =>
  tierGroups.value.find((g) => g.tier_group_id === selectedGroupId.value)
);
const selectedTopic = computed(() =>
  topics.value.find((t) => t.topic_id === selectedTopicId.value)
);
function flattenTiers(tiers) {
  return tiers.flatMap((tier) => [tier, ...flattenTiers(tier.children || [])]);
}
function countTiers(tiers) {
  return flattenTiers(tiers).length;
}
const currentTierNames = computed(
  () =>
    new Set(
      flattenTiers(selectedGroup.value?.tiers || []).map((t) => t.tier_name)
    )
);
const availableBaselineTiers = computed(() =>
  baselineTiers.value.filter((name) => currentTierNames.value.has(name))
);
const protectedBaselineNames = computed(
  () =>
    new Set(
      [...includedBaselineNames.value].filter(
        (name) => !editableBaselineNames.value.has(name)
      )
    )
);
const allBaselineIncluded = computed(
  () =>
    availableBaselineTiers.value.length > 0 &&
    availableBaselineTiers.value.every((name) =>
      includedBaselineNames.value.has(name)
    )
);
const allTierNames = computed(() =>
  [
    ...new Set(
      tierGroups.value.flatMap((g) =>
        flattenTiers(g.tiers).map((t) => t.tier_name)
      )
    ),
  ].sort()
);
const filteredTierNames = computed(() =>
  allTierNames.value.filter((name) =>
    name.toLowerCase().includes(tierSearch.value.toLowerCase())
  )
);
const missingTopicTiers = computed(() =>
  (selectedTopic.value?.tier_names || []).filter(
    (name) => !currentTierNames.value.has(name)
  )
);
const rankedGroups = computed(() => {
  if (!selectedTopic.value)
    return [...tierGroups.value].sort((a, b) =>
      a.elan_file_name.localeCompare(b.elan_file_name)
    );
  return [...tierGroups.value].sort(
    (a, b) =>
      groupTopicCoverage(b, selectedTopic.value) -
        groupTopicCoverage(a, selectedTopic.value) ||
      a.elan_file_name.localeCompare(b.elan_file_name)
  );
});
const filteredRankedGroups = computed(() => {
  const query = fileSearch.value.trim().toLowerCase();
  return rankedGroups.value.filter(
    (group) => !query || group.elan_file_name.toLowerCase().includes(query)
  );
});
const filePageCount = computed(() =>
  Math.max(1, Math.ceil(filteredRankedGroups.value.length / filePageSize))
);
const visibleRankedGroups = computed(() => {
  const start = (filePage.value - 1) * filePageSize;
  return filteredRankedGroups.value.slice(start, start + filePageSize);
});
const fileResultRange = computed(() => {
  const total = filteredRankedGroups.value.length;
  if (!total) return t('researchScopes.pagination.empty');
  const first = (filePage.value - 1) * filePageSize + 1;
  const last = Math.min(filePage.value * filePageSize, total);
  return t('researchScopes.pagination.range', { first, last, total });
});
const uniqueBestGroupId = computed(() => {
  if (!selectedTopic.value || !rankedGroups.value.length) return null;
  const firstScore = groupTopicCoverage(
    rankedGroups.value[0],
    selectedTopic.value
  );
  const secondScore = rankedGroups.value[1]
    ? groupTopicCoverage(rankedGroups.value[1], selectedTopic.value)
    : -1;
  return firstScore > secondScore && firstScore > 0
    ? rankedGroups.value[0].tier_group_id
    : null;
});
const automaticParentNames = computed(() => {
  const result = new Set();
  function visit(tiers, parents = []) {
    tiers.forEach((tier) => {
      if (selectedTierNames.value.has(tier.tier_name))
        parents.forEach((name) => {
          if (!selectedTierNames.value.has(name)) result.add(name);
        });
      visit(tier.children || [], [...parents, tier.tier_name]);
    });
  }
  visit(selectedGroup.value?.tiers || []);
  return result;
});
function groupTierNames(group) {
  return new Set(
    flattenTiers(group?.tiers || []).map((tier) => tier.tier_name)
  );
}
function groupTopicCoverage(group, topic) {
  const names = groupTierNames(group);
  return topic.tier_names.filter((name) => names.has(name)).length;
}
function matchingFileCount(topic) {
  return tierGroups.value.filter(
    (group) => groupTopicCoverage(group, topic) > 0
  ).length;
}
function tierFiles(name) {
  return tierGroups.value
    .filter((group) => groupTierNames(group).has(name))
    .map((group) => group.elan_file_name);
}
function coverageRows(topic) {
  return tierGroups.value
    .map((group) => {
      const matches = topic.tier_names.filter((name) =>
        groupTierNames(group).has(name)
      );
      return {
        filename: group.elan_file_name,
        matches,
        percent: Math.round((matches.length / topic.tier_names.length) * 100),
      };
    })
    .filter((row) => row.matches.length)
    .sort(
      (a, b) =>
        b.matches.length - a.matches.length ||
        a.filename.localeCompare(b.filename)
    );
}
function filteredCoverageRows(topic) {
  const query = coverageSearch.value.trim().toLowerCase();
  return coverageRows(topic).filter(
    (row) =>
      !query ||
      row.filename.toLowerCase().includes(query) ||
      row.matches.some((name) => name.toLowerCase().includes(query))
  );
}
function visibleCoverageRows(topic) {
  return filteredCoverageRows(topic).slice(0, coverageLimit.value);
}
function toggleTopicCoverage(topic) {
  expandedTopicId.value =
    expandedTopicId.value === topic.topic_id ? null : topic.topic_id;
  coverageSearch.value = '';
  coverageLimit.value = 10;
}
function selectGroup(group) {
  selectedGroupId.value = group.tier_group_id;
  selectedTierNames.value = new Set(
    (selectedTopic.value?.tier_names || []).filter(
      (name) =>
        groupTierNames(group).has(name) && !baselineTiers.value.includes(name)
    )
  );
  const available = new Set(
    baselineTiers.value.filter((name) => groupTierNames(group).has(name))
  );
  includedBaselineNames.value = available;
  editableBaselineNames.value = new Set();
}
function applyTopic(topic) {
  selectedTopicId.value = topic?.topic_id ?? null;
  fileSearch.value = '';
  filePage.value = 1;
  const best = topic
    ? [...tierGroups.value].sort(
        (a, b) =>
          groupTopicCoverage(b, topic) - groupTopicCoverage(a, topic) ||
          a.elan_file_name.localeCompare(b.elan_file_name)
      )[0]
    : selectedGroup.value || tierGroups.value[0];
  if (best) selectGroup(best);
  else selectedTierNames.value = new Set();
}
function topicCoverage(topic) {
  return topic.tier_names.filter((name) => currentTierNames.value.has(name))
    .length;
}
function useTopic(topic) {
  applyTopic(topic);
  activeMode.value = 'export';
}
function toggleTier(name) {
  if (baselineTiers.value.includes(name)) return;
  const next = new Set(selectedTierNames.value);
  next.has(name) ? next.delete(name) : next.add(name);
  selectedTierNames.value = next;
}
function toggleIncludedBaseline(name) {
  const included = new Set(includedBaselineNames.value);
  const editable = new Set(editableBaselineNames.value);
  if (included.has(name)) {
    included.delete(name);
    editable.delete(name);
  } else {
    included.add(name);
  }
  includedBaselineNames.value = included;
  editableBaselineNames.value = editable;
}
function toggleEditableBaseline(name) {
  const editable = new Set(editableBaselineNames.value);
  const included = new Set(includedBaselineNames.value);
  if (editable.has(name)) editable.delete(name);
  else {
    editable.add(name);
    included.add(name);
  }
  editableBaselineNames.value = editable;
  includedBaselineNames.value = included;
}
function toggleAllBaselineContext() {
  if (allBaselineIncluded.value) {
    includedBaselineNames.value = new Set();
    editableBaselineNames.value = new Set();
  } else {
    includedBaselineNames.value = new Set(availableBaselineTiers.value);
  }
}
function selectAllTiers() {
  selectedTierNames.value = new Set(
    [...currentTierNames.value].filter(
      (name) => !baselineTiers.value.includes(name)
    )
  );
}
function clearSelectedTiers() {
  selectedTierNames.value = new Set();
}
function tierFileCount(name) {
  return tierGroups.value.filter((g) =>
    flattenTiers(g.tiers).some((t) => t.tier_name === name)
  ).length;
}
async function loadData() {
  const request = ++loadRequest;
  const id = currentProject.value?.project_id;
  loading.value = true;
  error.value = '';
  if (!id) {
    error.value = t('researchScopes.messages.selectProject');
    loading.value = false;
    return;
  }
  try {
    const [treeResult, topicsResult, baselineResult] = await Promise.allSettled(
      [
        fetchSectionsAndGroups(id),
        fetchResearchTopics(id),
        fetchProjectBaselineTiers(id),
      ]
    );
    if (request !== loadRequest) return;
    if (treeResult.status === 'rejected') throw treeResult.reason;
    tierGroups.value = treeResult.value.tier_groups;
    topics.value =
      topicsResult.status === 'fulfilled' ? topicsResult.value : [];
    baselineTiers.value =
      baselineResult.status === 'fulfilled'
        ? baselineResult.value.tier_names
        : [];
    topicLoadError.value =
      topicsResult.status === 'rejected'
        ? t('researchScopes.messages.topicsUnavailable')
        : '';
    if (tierGroups.value.length) selectGroup(tierGroups.value[0]);
  } catch {
    if (request === loadRequest)
      error.value = t('researchScopes.messages.loadFailed');
  } finally {
    if (request === loadRequest) loading.value = false;
  }
}
function toggleBaselineEditor() {
  baselineEditing.value = !baselineEditing.value;
  baselineForm.value = new Set(baselineTiers.value);
}
function toggleBaselineTier(name) {
  const next = new Set(baselineForm.value);
  next.has(name) ? next.delete(name) : next.add(name);
  baselineForm.value = next;
}
async function saveBaselineTiers() {
  operationPending.value = true;
  operationError.value = '';
  try {
    const result = await updateProjectBaselineTiers(
      currentProject.value.project_id,
      [...baselineForm.value]
    );
    baselineTiers.value = result.tier_names;
    baselineEditing.value = false;
    messages.addMessage(t('researchScopes.messages.baselineSaved'), 'success');
  } catch {
    operationError.value = t('researchScopes.messages.baselineSaveFailed');
  } finally {
    operationPending.value = false;
  }
}
async function downloadResearchCopy() {
  if (
    !selectedGroup.value ||
    (!selectedTierNames.value.size && !editableBaselineNames.value.size)
  )
    return;
  exportPending.value = true;
  try {
    const response = await exportTierSubset(
      currentProject.value.project_name,
      selectedGroup.value.elan_file_name,
      [...selectedTierNames.value],
      selectedTopicId.value,
      [...includedBaselineNames.value],
      [...editableBaselineNames.value]
    );
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = selectedGroup.value.elan_file_name;
    link.click();
    URL.revokeObjectURL(url);
    messages.addMessage(t('researchScopes.messages.downloaded'), 'success');
  } catch {
    messages.addMessage(t('researchScopes.messages.downloadFailed'), 'error');
  } finally {
    exportPending.value = false;
  }
}
function resetForm() {
  Object.assign(topicForm, {
    topic_id: null,
    name: '',
    description: '',
    tier_names: new Set(),
    allow_new_tiers: false,
  });
  tierSearch.value = '';
}
function startCreate() {
  resetForm();
  editingTopic.value = true;
}
function startEdit(topic) {
  Object.assign(topicForm, {
    topic_id: topic.topic_id,
    name: topic.name,
    description: topic.description || '',
    tier_names: new Set(topic.tier_names),
    allow_new_tiers: topic.allow_new_tiers,
  });
  editingTopic.value = true;
}
function cancelEdit() {
  editingTopic.value = false;
  resetForm();
}
function toggleTopicTier(name) {
  topicForm.tier_names.has(name)
    ? topicForm.tier_names.delete(name)
    : topicForm.tier_names.add(name);
}
async function saveTopic() {
  operationPending.value = true;
  operationError.value = '';
  const payload = {
    name: topicForm.name,
    description: topicForm.description || null,
    tier_names: [...topicForm.tier_names],
    allow_new_tiers: topicForm.allow_new_tiers,
  };
  try {
    topicForm.topic_id
      ? await updateResearchTopic(
          currentProject.value.project_id,
          topicForm.topic_id,
          payload
        )
      : await createResearchTopic(currentProject.value.project_id, payload);
    await loadData();
    cancelEdit();
    messages.addMessage(t('researchScopes.messages.topicSaved'), 'success');
  } catch (e) {
    operationError.value =
      e.response?.data?.detail || t('researchScopes.messages.topicSaveFailed');
  } finally {
    operationPending.value = false;
  }
}
async function removeTopic(topic) {
  const yes = await confirmAction({
    title: t('researchScopes.messages.deleteTitle', { topic: topic.name }),
    message: t('researchScopes.messages.deleteText'),
    confirmText: t('researchScopes.topics.delete'),
    cancelText: t('common.cancel'),
    tone: 'danger',
  });
  if (!yes) return;
  await deleteResearchTopic(currentProject.value.project_id, topic.topic_id);
  await loadData();
  messages.addMessage(t('researchScopes.messages.topicDeleted'), 'success');
}
watch(fileSearch, () => {
  filePage.value = 1;
});
watch(
  () => currentProject.value?.project_id,
  () => {
    tierGroups.value = [];
    topics.value = [];
    baselineTiers.value = [];
    selectedGroupId.value = null;
    selectedTopicId.value = null;
    topicLoadError.value = '';
    void loadData();
  },
  { immediate: true }
);
onMounted(() => projectStore.initBroadcastChannel());
</script>
