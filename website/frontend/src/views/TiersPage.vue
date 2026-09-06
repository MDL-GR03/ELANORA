<template>
  <div class="tiers-page" :class="{ 'tiers-page--dragging': isDragging }">
    <WorkspaceHeader
      :title="t('tiersPage.pageTitle')"
      :context="projectStore.currentProject?.project_name || ''"
      :description="t('tiersPage.pageDescription')"
    />

    <section class="tiers-workspace" :aria-busy="loading || operationPending">
      <nav class="tiers-mode-tabs" aria-label="Tier workspace">
        <button
          type="button"
          :class="{ 'is-active': activeMode === 'export' }"
          @click="activeMode = 'export'"
        >
          <font-awesome-icon icon="fa-solid fa-download" />
          Prepare a research copy
        </button>
        <button
          type="button"
          :class="{ 'is-active': activeMode === 'organize' }"
          @click="activeMode = 'organize'"
        >
          <font-awesome-icon icon="fa-solid fa-layer-group" />
          Organize project files
        </button>
      </nav>

      <div v-if="activeMode === 'export'" class="tier-export-workspace">
        <header class="tier-export-intro">
          <div>
            <span class="tier-export-eyebrow">RESEARCH WORKING COPY</span>
            <h2>Take only the annotation layers you need</h2>
            <p>
              Choose one ELAN file and its useful tiers. The downloaded copy keeps
              required parent tiers, media links, and ELAN metadata automatically.
            </p>
          </div>
          <div class="tier-export-safety">
            <font-awesome-icon icon="fa-solid fa-shield-halved" />
            <span>Your accepted project file is never changed.</span>
          </div>
        </header>

        <div v-if="loading" class="tiers-state-panel">{{ t('tiersPage.loading') }}</div>
        <div v-else-if="error" class="tiers-state-panel tiers-state-panel--error" role="alert">{{ error }}</div>
        <div v-else-if="!tierGroups.length" class="tiers-state-panel">
          No ELAN files with tiers are available in this project.
        </div>
        <div v-else class="tier-export-layout">
          <aside class="tier-export-files" aria-label="ELAN files">
            <h3>1. Choose a file</h3>
            <button
              v-for="group in tierGroups"
              :key="group.tier_group_id"
              type="button"
              :class="{ 'is-active': selectedGroup?.tier_group_id === group.tier_group_id }"
              @click="selectGroup(group)"
            >
              <font-awesome-icon icon="fa-solid fa-file-code" />
              <span><strong>{{ group.elan_file_name }}</strong><small>{{ countTiers(group.tiers) }} tiers</small></span>
              <font-awesome-icon icon="fa-solid fa-chevron-right" />
            </button>
          </aside>

          <section class="tier-export-selection">
            <div class="tier-export-selection__header">
              <div>
                <h3>2. Select tiers</h3>
                <p v-if="selectedGroup">{{ selectedGroup.elan_file_name }}</p>
              </div>
              <div class="tier-export-selection__shortcuts">
                <button type="button" @click="selectAllTiers">Select all</button>
                <button type="button" @click="clearSelectedTiers">Clear</button>
              </div>
            </div>
            <div class="tier-export-tree-panel">
              <TierSelectionTree
                v-if="selectedGroup"
                root
                :tiers="selectedGroup.tiers"
                :selected-names="selectedTierNames"
                :automatic-names="automaticParentNames"
                @toggle="toggleTier"
              />
            </div>
            <footer class="tier-export-footer">
              <div>
                <strong>{{ selectedTierNames.size }} research tier(s) selected</strong>
                <span v-if="automaticParentNames.size">+ {{ automaticParentNames.size }} required parent tier(s), shown checked above.</span>
                <span v-else>Required parent tiers will be included automatically.</span>
              </div>
              <button
                type="button"
                class="tiers-primary-button"
                :disabled="!selectedTierNames.size || exportPending"
                @click="downloadResearchCopy"
              >
                <font-awesome-icon icon="fa-solid fa-download" />
                {{ exportPending ? 'Preparing…' : 'Download research copy' }}
              </button>
            </footer>
          </section>
        </div>

        <div class="tier-export-roundtrip">
          <strong>Continue in ELAN</strong>
          <span>Open this scoped copy in ELAN, save it under the same stable filename, then upload it normally. ELANORA will reintegrate only the tiers you intentionally selected.</span>
        </div>
      </div>

      <template v-else>
      <div class="tiers-toolbar">
        <div>
          <h2>{{ t('tiersPage.sectionsTitle') }}</h2>
          <p>{{ t('tiersPage.sectionsDescription') }}</p>
        </div>
        <form
          v-if="isInstitutionAdmin"
          class="tiers-section-create-form"
          @submit.prevent="handleCreateSection"
        >
          <label class="sr-only" for="new-tier-section">
            {{ t('tiersPage.newSectionName') }}
          </label>
          <input
            id="new-tier-section"
            v-model.trim="newSectionName"
            :placeholder="t('tiersPage.newSectionName')"
            maxlength="100"
            required
          />
          <button
            type="submit"
            class="tiers-primary-button"
            :disabled="operationPending"
          >
            <font-awesome-icon icon="fa-solid fa-plus" />
            {{ t('tiersPage.createSection') }}
          </button>
        </form>
      </div>

      <div class="tiers-guidance">
        <font-awesome-icon icon="fa-solid fa-circle-info" />
        <span>{{ t('tiersPage.moveGuidance') }}</span>
      </div>
      <div class="sr-only" aria-live="polite">{{ statusMessage }}</div>
      <div v-if="operationError" class="tiers-operation-error" role="alert">
        {{ operationError }}
      </div>

      <div v-if="loading" class="tiers-state-panel">
        {{ t('tiersPage.loading') }}
      </div>
      <div
        v-else-if="error"
        class="tiers-state-panel tiers-state-panel--error"
        role="alert"
      >
        {{ error }}
      </div>
      <div v-else class="tiers-sections-list">
        <article
          v-for="section in sections"
          :key="section.section_id"
          class="tiers-section-card"
        >
          <header class="tiers-section-header">
            <form
              v-if="editingSectionId === section.section_id"
              class="tiers-rename-form"
              @submit.prevent="handleRenameSection(section.section_id)"
            >
              <label
                class="sr-only"
                :for="`rename-section-${section.section_id}`"
              >
                {{ t('tiersPage.renameSection') }}
              </label>
              <input
                :id="`rename-section-${section.section_id}`"
                v-model.trim="renameSectionName"
                maxlength="100"
                required
                autofocus
              />
              <button
                type="submit"
                class="tiers-icon-button tiers-icon-button--confirm"
                :title="t('common.save')"
              >
                <font-awesome-icon icon="fa-solid fa-check" />
              </button>
              <button
                type="button"
                class="tiers-icon-button"
                :title="t('common.cancel')"
                @click="cancelRenameSection"
              >
                <font-awesome-icon icon="fa-solid fa-xmark" />
              </button>
            </form>
            <template v-else>
              <div class="tiers-section-heading">
                <div class="tiers-section-heading-icon">
                  <font-awesome-icon icon="fa-solid fa-layer-group" />
                </div>
                <div>
                  <h3>{{ section.name }}</h3>
                  <span>
                    {{
                      t('tiersPage.fileCount', {
                        count: sectionGroups(section.section_id).length,
                      })
                    }}
                  </span>
                </div>
              </div>
              <div v-if="isInstitutionAdmin" class="tiers-section-actions">
                <button
                  type="button"
                  class="tiers-icon-button tiers-icon-button--edit"
                  :title="t('tiersPage.renameSection')"
                  @click="startRenameSection(section.section_id, section.name)"
                >
                  <font-awesome-icon icon="fa-regular fa-pen-to-square" />
                </button>
                <button
                  type="button"
                  class="tiers-icon-button tiers-icon-button--delete"
                  :title="t('tiersPage.deleteSection')"
                  @click="handleDeleteSection(section)"
                >
                  <font-awesome-icon icon="trash" />
                </button>
              </div>
            </template>
          </header>

          <draggable
            :list="sectionGroups(section.section_id)"
            group="tier-groups"
            item-key="tier_group_id"
            handle=".tier-group-drag-handle"
            class="tier-group-drop-zone"
            :class="{
              'tier-group-drop-zone--empty':
                sectionGroups(section.section_id).length === 0,
            }"
            :sort="false"
            :disabled="operationPending || !isInstitutionAdmin"
            :scroll="true"
            :scroll-sensitivity="80"
            :scroll-speed="14"
            @change="(event) => onDrop(section.section_id, event)"
            @start="onDragStart"
            @end="onDragEnd"
          >
            <template #item="{ element }">
              <TierGroupRow
                :group="element"
                :sections="sections"
                :current-section-id="section.section_id"
                :disabled="operationPending || !isInstitutionAdmin"
                @move="persistMove(element, $event)"
              />
            </template>
            <template #footer>
              <div
                v-if="sectionGroups(section.section_id).length === 0"
                class="tiers-empty-drop-zone"
              >
                <font-awesome-icon icon="fa-solid fa-arrow-down" />
                {{ t('tiersPage.dropHere') }}
              </div>
            </template>
          </draggable>
        </article>

        <article class="tiers-section-card tiers-section-card--unsectioned">
          <header class="tiers-section-header">
            <div class="tiers-section-heading">
              <div
                class="tiers-section-heading-icon tiers-section-heading-icon--neutral"
              >
                <font-awesome-icon icon="fa-solid fa-inbox" />
              </div>
              <div>
                <h3>{{ t('tiersPage.unsectioned') }}</h3>
                <span>
                  {{
                    t('tiersPage.fileCount', {
                      count: unsectionedTierGroups.length,
                    })
                  }}
                </span>
              </div>
            </div>
          </header>
          <draggable
            :list="unsectionedTierGroups"
            group="tier-groups"
            item-key="tier_group_id"
            handle=".tier-group-drag-handle"
            class="tier-group-drop-zone"
            :class="{
              'tier-group-drop-zone--empty': unsectionedTierGroups.length === 0,
            }"
            :sort="false"
            :disabled="operationPending || !isInstitutionAdmin"
            @change="(event) => onDrop(null, event)"
            @start="onDragStart"
            @end="onDragEnd"
          >
            <template #item="{ element }">
              <TierGroupRow
                :group="element"
                :sections="sections"
                :current-section-id="null"
                :disabled="operationPending || !isInstitutionAdmin"
                @move="persistMove(element, $event)"
              />
            </template>
            <template #footer>
              <div
                v-if="unsectionedTierGroups.length === 0"
                class="tiers-empty-drop-zone"
              >
                {{ t('tiersPage.noUnsectioned') }}
              </div>
            </template>
          </draggable>
        </article>
      </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import '@/assets/css/tiers.css';
import { computed, onMounted, ref, watch } from 'vue';
import { useHead } from '@unhead/vue';
import { useI18n } from 'vue-i18n';
import draggable from 'vuedraggable';
import {
  createSection,
  deleteSection,
  fetchSectionsAndGroups,
  exportTierSubset,
  moveTierGroup,
  renameSection,
} from '@/api/service/tierService';
import TierGroupRow from '@/components/pageSpecific/tiers/TierGroupRow.vue';
import TierSelectionTree from '@/components/pageSpecific/tiers/TierSelectionTree.vue';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { useEventMessageStore } from '@/stores/eventMessage';

const projectStore = useProjectStore();
const userStore = useUserStore();
const eventMessageStore = useEventMessageStore();
const isInstitutionAdmin = computed(() => userStore.user?.role === 'admin');
const { t } = useI18n();
const confirmAction = useUserConfirm();

useHead({
  title: computed(() => t('tiersPage.pageTitle')),
  meta: [
    {
      name: 'description',
      content: computed(() => t('tiersPage.pageDescription')),
    },
  ],
});

const currentProject = computed(() => projectStore.currentProject);
const sections = ref([]);
const tierGroups = ref([]);
const loading = ref(true);
const error = ref('');
const operationError = ref('');
const statusMessage = ref('');
const operationPending = ref(false);
const exportPending = ref(false);
const activeMode = ref('export');
const selectedGroupId = ref(null);
const selectedTierNames = ref(new Set());
const newSectionName = ref('');
const renameSectionName = ref('');
const editingSectionId = ref(null);
const isDragging = ref(false);
let loadRequest = 0;

const unsectionedTierGroups = computed(() => sectionGroups(null));
const selectedGroup = computed(() =>
  tierGroups.value.find((group) => group.tier_group_id === selectedGroupId.value)
);
const automaticParentNames = computed(() => {
  const automatic = new Set();
  function visit(tiers, ancestors = []) {
    for (const tier of tiers) {
      if (selectedTierNames.value.has(tier.tier_name)) {
        for (const ancestor of ancestors) {
          if (!selectedTierNames.value.has(ancestor)) automatic.add(ancestor);
        }
      }
      visit(tier.children || [], [...ancestors, tier.tier_name]);
    }
  }
  visit(selectedGroup.value?.tiers || []);
  return automatic;
});

function flattenTiers(tiers) {
  return tiers.flatMap((tier) => [tier, ...flattenTiers(tier.children || [])]);
}

function countTiers(tiers) {
  return flattenTiers(tiers).length;
}

function selectGroup(group) {
  selectedGroupId.value = group.tier_group_id;
  selectedTierNames.value = new Set();
}

function toggleTier(tierName) {
  const next = new Set(selectedTierNames.value);
  if (next.has(tierName)) next.delete(tierName);
  else next.add(tierName);
  selectedTierNames.value = next;
}

function selectAllTiers() {
  if (!selectedGroup.value) return;
  selectedTierNames.value = new Set(
    flattenTiers(selectedGroup.value.tiers).map((tier) => tier.tier_name)
  );
}

function clearSelectedTiers() {
  selectedTierNames.value = new Set();
}

async function downloadResearchCopy() {
  if (!selectedGroup.value || !currentProject.value || !selectedTierNames.value.size) return;
  exportPending.value = true;
  operationError.value = '';
  try {
    const response = await exportTierSubset(
      currentProject.value.project_name,
      selectedGroup.value.elan_file_name,
      [...selectedTierNames.value]
    );
    const disposition = response.headers['content-disposition'] || '';
    const serverName = disposition.match(/filename="?([^";]+)"?/i)?.[1];
    const fallbackName = selectedGroup.value.elan_file_name;
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = serverName || fallbackName;
    link.click();
    URL.revokeObjectURL(url);
    statusMessage.value = 'Research copy downloaded.';
    eventMessageStore.addMessage('Research copy downloaded and ready to open in ELAN.', 'success');
  } catch {
    operationError.value = 'The research copy could not be prepared. Please try again.';
    eventMessageStore.addMessage(operationError.value, 'error');
  } finally {
    exportPending.value = false;
  }
}

function sectionGroups(sectionId) {
  return tierGroups.value.filter((group) => group.section_id === sectionId);
}

async function loadData({ silent = false } = {}) {
  const request = ++loadRequest;
  const projectId = currentProject.value?.project_id;
  if (!silent) loading.value = true;
  error.value = '';
  try {
    if (!projectId) {
      sections.value = [];
      tierGroups.value = [];
      error.value = t('tiersPage.noProject');
      return;
    }
    const data = await fetchSectionsAndGroups(projectId);
    if (
      request !== loadRequest ||
      projectId !== currentProject.value?.project_id
    )
      return;
    sections.value = data.sections;
    tierGroups.value = data.tier_groups;
    if (!selectedGroup.value && tierGroups.value.length) {
      selectGroup(tierGroups.value[0]);
    }
  } catch {
    if (request === loadRequest) error.value = t('tiersPage.loadFailed');
  } finally {
    if (!silent && request === loadRequest) loading.value = false;
  }
}

async function runOperation(operation, successKey) {
  const operationProjectId = currentProject.value?.project_id;
  operationPending.value = true;
  operationError.value = '';
  try {
    await operation();
    if (operationProjectId === currentProject.value?.project_id) {
      statusMessage.value = t(successKey);
      await loadData({ silent: true });
    }
    return true;
  } catch {
    if (operationProjectId === currentProject.value?.project_id) {
      operationError.value = t('tiersPage.operationFailed');
      await loadData({ silent: true });
    }
    return false;
  } finally {
    operationPending.value = false;
  }
}

async function handleCreateSection() {
  if (!newSectionName.value || !currentProject.value) return;
  const created = await runOperation(
    () => createSection(currentProject.value.project_id, newSectionName.value),
    'tiersPage.sectionCreated'
  );
  if (created) newSectionName.value = '';
}

function startRenameSection(sectionId, currentName) {
  editingSectionId.value = sectionId;
  renameSectionName.value = currentName;
}

function cancelRenameSection() {
  editingSectionId.value = null;
  renameSectionName.value = '';
}

async function handleRenameSection(sectionId) {
  if (!renameSectionName.value) return;
  const renamed = await runOperation(
    () => renameSection(sectionId, renameSectionName.value),
    'tiersPage.sectionRenamed'
  );
  if (renamed) cancelRenameSection();
}

async function handleDeleteSection(section) {
  const confirmed = await confirmAction({
    title: t('tiersPage.deleteSection'),
    message: t('tiersPage.deleteConfirmation', { name: section.name }),
    confirmText: t('tiersPage.deleteSection'),
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;
  await runOperation(
    () => deleteSection(section.section_id),
    'tiersPage.sectionDeleted'
  );
}

async function persistMove(group, sectionId) {
  if (group.section_id === sectionId) return;
  await runOperation(
    () => moveTierGroup(group.tier_group_id, sectionId),
    'tiersPage.groupMoved'
  );
}

async function onDrop(newSectionId, event) {
  const movedGroup = event?.added?.element;
  if (movedGroup) await persistMove(movedGroup, newSectionId);
}

function onDragStart() {
  isDragging.value = true;
}

function onDragEnd() {
  isDragging.value = false;
}

watch(
  () => currentProject.value?.project_id,
  () => {
    sections.value = [];
    tierGroups.value = [];
    selectedGroupId.value = null;
    selectedTierNames.value = new Set();
    operationError.value = '';
    statusMessage.value = '';
    newSectionName.value = '';
    cancelRenameSection();
    void loadData();
  },
  { immediate: true }
);

onMounted(() => {
  projectStore.initBroadcastChannel();
});
</script>
