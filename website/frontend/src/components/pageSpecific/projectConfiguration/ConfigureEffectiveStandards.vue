<template>
  <div>
    <div class="configure-effective-standards-header">
      <h2 class="configure-effective-standards-title">
        {{ t('configureEffectiveStandards.title') }}
      </h2>
    </div>
    <!-- Location Selection -->
    <div class="configure-effective-standards-section">
      <label
        for="location-select"
        class="configure-effective-standards-label"
        >{{ t('configureEffectiveStandards.standardLocation') }}</label
      >
      <AppSelect
        id="location-select"
        v-model="selectedLocationId"
        :options="locationOptions"
        :placeholder="t('configureEffectiveStandards.selectStandard')"
        @change="onLocationChange"
      />
    </div>
    <!-- Drag & Drop File Type Association -->
    <div class="configure-effective-standards-dnd-row">
      <div class="configure-effective-standards-dnd-box">
        <div class="configure-effective-standards-chips-label">
          {{ t('configureEffectiveStandards.availableFileTypes') }}
        </div>
        <draggable
          :list="availableFileTypesDraggable"
          :group="{ name: 'fileTypes', pull: true, put: true }"
          item-key="id"
          class="configure-effective-standards-chips-list"
          @change="onFileTypeChange"
        >
          <template #item="{ element }">
            <div class="configure-effective-standards-chip">
              {{ element.name }} ({{ element.extension }})
            </div>
          </template>
        </draggable>
      </div>
      <div class="configure-effective-standards-dnd-box">
        <div class="configure-effective-standards-chips-label">
          {{ t('configureEffectiveStandards.associatedFileTypes') }}
        </div>
        <draggable
          :list="associatedFileTypesDraggable"
          :group="{ name: 'fileTypes', pull: true, put: true }"
          item-key="id"
          class="configure-effective-standards-chips-list"
          @change="onFileTypeChange"
        >
          <template #item="{ element }">
            <div
              class="configure-effective-standards-chip configure-effective-standards-chip--active"
            >
              {{ element.name }} ({{ element.extension }})
            </div>
          </template>
        </draggable>
      </div>
    </div>
    <!-- Standards Table -->
    <div
      v-if="activeFileTypes.length"
      class="configure-effective-standards-assign-standards-section"
    >
      <h3 class="configure-effective-standards-section-title">
        {{ t('configureEffectiveStandards.assignStandardsTitle') }}
      </h3>
      <table class="configure-effective-standards-table">
        <thead>
          <tr>
            <th class="configure-effective-standards-th">
              {{ t('configureEffectiveStandards.fileType') }}
            </th>
            <th class="configure-effective-standards-th">
              {{ t('configureEffectiveStandards.effectiveStandard') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="fileTypeId in activeFileTypes"
            :key="fileTypeId"
            class="configure-effective-standards-row"
          >
            <td class="configure-effective-standards-td">
              {{ fileTypes.find((ft) => ft.id === fileTypeId)?.name }}
            </td>
            <td class="configure-effective-standards-td">
              <AppSelect
                :id="`effective-standard-${fileTypeId}`"
                :model-value="effectiveStandards[fileTypeId] || ''"
                size="small"
                :options="standardOptions(fileTypeId)"
                @change="selectStandard(fileTypeId, $event)"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="errorMessage" class="configure-effective-standards-error">
      {{ errorMessage }}
    </div>
    <div v-if="successMessage" class="configure-effective-standards-success">
      {{ successMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useNamingStandardStore } from '@stores/namingStandard';
import { useFileTypeStore } from '@stores/fileType';
import { useEffectiveStandardStore } from '@stores/effectiveStandard';
import { useEventMessageStore } from '@stores/eventMessage';
import { useRoute } from 'vue-router';
import draggable from 'vuedraggable';
import AppSelect from '@/components/common/AppSelect.vue';

const { t } = useI18n();
const namingStandardStore = useNamingStandardStore();
const fileTypeStore = useFileTypeStore();
const effectiveStandardStore = useEffectiveStandardStore();
const eventMessageStore = useEventMessageStore();
const route = useRoute();

const projectId = Number(route.params.projectId);
const selectedLocationId = ref(null);
const errorMessage = ref('');
const successMessage = ref('');
const dragZone = ref(null);

const locations = computed(() => effectiveStandardStore.locations);
const locationOptions = computed(() =>
  locations.value.map((location) => ({
    value: location.id,
    label: t(`configureEffectiveStandards.standardLocations.${location.label}`),
    description: t(
      `configureEffectiveStandards.standardLocationsInfo.${location.label}`
    ),
  }))
);
const fileTypes = computed(() => fileTypeStore.fileTypes);
const activeFileTypes = computed(() => {
  if (!selectedLocationId.value) return [];
  return fileTypeStore.fileTypesByLocation[selectedLocationId.value] || [];
});
const effectiveStandards = computed({
  get() {
    if (!selectedLocationId.value) return {};
    return (
      effectiveStandardStore.effectiveStandards[selectedLocationId.value] || {}
    );
  },
  set(val) {
    if (!selectedLocationId.value) return;
    effectiveStandardStore.effectiveStandards[selectedLocationId.value] = val;
  },
});
const standardsByFileType = computed(() => {
  const result = {};
  for (const fileType of fileTypes.value) {
    result[fileType.id] = namingStandardStore.standards.filter(
      (s) => s.project_file_type_id === fileType.id
    );
  }
  return result;
});
const standardOptions = (fileTypeId) => [
  { value: '', label: t('configureEffectiveStandards.selectStandard') },
  ...(standardsByFileType.value[fileTypeId] || []).map((standard) => ({
    value: standard.id,
    label: standard.name,
  })),
];
const availableFileTypesDraggable = computed(() =>
  fileTypes.value.filter((ft) => !activeFileTypes.value.includes(ft.id))
);
const associatedFileTypesDraggable = computed(() =>
  fileTypes.value.filter((ft) => activeFileTypes.value.includes(ft.id))
);

async function loadInitialData() {
  await fileTypeStore.fetchFileTypes(projectId);
  await namingStandardStore.fetchStandardsAndComponentNames(projectId);
  await effectiveStandardStore.fetchLocations();
  if (locations.value.length > 0) {
    selectedLocationId.value = locations.value[0].id;
    await fileTypeStore.fetchFileTypesForLocation(
      projectId,
      selectedLocationId.value
    );
    await effectiveStandardStore.fetchEffectiveStandards(
      projectId,
      selectedLocationId.value,
      activeFileTypes.value
    );
  }
}

async function onLocationChange() {
  await fileTypeStore.fetchFileTypesForLocation(
    projectId,
    selectedLocationId.value
  );
  await effectiveStandardStore.fetchEffectiveStandards(
    projectId,
    selectedLocationId.value,
    activeFileTypes.value
  );
  errorMessage.value = '';
  successMessage.value = '';
}

async function onFileTypeChange(evt) {
  if (!selectedLocationId.value) return;
  const location = locations.value.find(
    (loc) => loc.id === selectedLocationId.value
  );
  // Handle add (drag from available to associated)
  if (evt.added && evt.added.element) {
    const added = evt.added.element;
    if (added && added.id && !activeFileTypes.value.includes(added.id)) {
      await fileTypeStore.addFileTypeToLocation(
        projectId,
        selectedLocationId.value,
        added.id
      );
      eventMessageStore.addMessage(
        t('configureEffectiveStandards.eventMessages.fileTypeAdded', {
          fileType: added.name,
          location: location?.label || '',
        }),
        'success'
      );
      await effectiveStandardStore.fetchEffectiveStandards(
        projectId,
        selectedLocationId.value,
        activeFileTypes.value
      );
    }
  }
  // Handle remove (drag from associated to available)
  if (evt.removed && evt.removed.element) {
    const removed = evt.removed.element;
    if (removed && removed.id && activeFileTypes.value.includes(removed.id)) {
      await fileTypeStore.removeFileTypeFromLocation(
        projectId,
        selectedLocationId.value,
        removed.id
      );
      // Unassign effective standard for this file type at this location
      await effectiveStandardStore.unassignEffectiveStandard(
        projectId,
        removed.id,
        selectedLocationId.value
      );
      eventMessageStore.addMessage(
        t('configureEffectiveStandards.eventMessages.fileTypeRemoved', {
          fileType: removed.name,
          location: location?.label || '',
        }),
        'success'
      );
      await effectiveStandardStore.fetchEffectiveStandards(
        projectId,
        selectedLocationId.value,
        activeFileTypes.value
      );
    }
  }
  dragZone.value = null;
}

async function onEffectiveStandardChange(fileTypeId) {
  const selected = effectiveStandards.value[fileTypeId];
  if (selected === '') {
    await effectiveStandardStore.unassignEffectiveStandard(
      projectId,
      fileTypeId,
      selectedLocationId.value
    );
    eventMessageStore.addMessage(
      t('configureEffectiveStandards.eventMessages.removeSuccess'),
      'success'
    );
  } else if (!isNaN(Number(selected))) {
    await effectiveStandardStore.assignEffectiveStandard(
      projectId,
      fileTypeId,
      selected,
      selectedLocationId.value
    );
    eventMessageStore.addMessage(
      t('configureEffectiveStandards.eventMessages.updateSuccess'),
      'success'
    );
  }
  await effectiveStandardStore.fetchEffectiveStandards(
    projectId,
    selectedLocationId.value,
    activeFileTypes.value
  );
}

function selectStandard(fileTypeId, standardId) {
  effectiveStandards.value[fileTypeId] = standardId;
  onEffectiveStandardChange(fileTypeId);
}

onMounted(() => {
  loadInitialData();
});
</script>

<style scoped>
.configure-effective-standards-header {
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-gray-200);
}

.configure-effective-standards-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-gray-900);
}

.configure-effective-standards-section {
  margin-bottom: 2rem;
}

.configure-effective-standards-section-title {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  color: var(--color-primary);
}

.configure-effective-standards-label {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.7rem;
  color: var(--color-gray-700-alt);
  display: block;
}

.configure-effective-standards-dnd-row {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
}

.configure-effective-standards-dnd-box {
  flex: 1;
  background: var(--color-surface);
  border-radius: 10px;
  box-shadow: 0 1px 6px rgb(0 0 0 / 7%);
  padding: 1.2rem;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  border: 2px solid var(--color-gray-200);
  transition:
    border-color 0.2s,
    background 0.2s;
}

.configure-effective-standards-chips-label {
  font-size: 1rem;
  font-weight: 500;
  margin-bottom: 0.7rem;
  color: var(--color-gray-700-alt);
}

.configure-effective-standards-chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
  min-height: 40px;
}

.configure-effective-standards-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 1rem;
  background: var(--color-gray-200);
  color: var(--color-gray-700-alt);
  border: 2px solid var(--color-gray-200);
  cursor: grab;
  transition:
    background 0.2s,
    border-color 0.2s;
  margin-bottom: 0.3rem;
}

.configure-effective-standards-chip:hover {
  background: var(--color-gray-400);
  border-color: var(--color-primary);
}

.configure-effective-standards-chip--active {
  background: var(--color-primary);
  color: var(--color-surface);
  border-color: var(--color-primary);
}

.configure-effective-standards-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border-radius: 8px;
  box-shadow: 0 1px 4px rgb(0 0 0 / 7%);
  overflow: visible; /* Allow dropdowns to be visible outside table boundaries */
  margin-top: 1.5rem;
  table-layout: fixed; /* Prevent column width changes when dropdown opens */
}

.configure-effective-standards-th {
  background: var(--color-gray-200);
  color: var(--color-gray-700-alt);
  font-weight: 500;
  padding: 1rem 1.2rem;
  text-align: left;
  border-bottom: 2px solid var(--color-gray-400);
}

.configure-effective-standards-th:first-child {
  width: 40%; /* File type column */
}

.configure-effective-standards-th:last-child {
  width: 60%; /* Standard selection column */
}

.configure-effective-standards-row {
  border-bottom: 1px solid var(--color-gray-200);
}

.configure-effective-standards-td {
  padding: 1rem 1.2rem;
  font-size: 1rem;
  color: var(--color-gray-600);
  position: relative; /* Ensure dropdown positioning is relative to table cell */
}

.configure-effective-standards-success {
  margin-top: 2rem;
  color: var(--color-success-600);
  background: var(--color-success-50);
  padding: 1rem 1.2rem;
  border-radius: 8px;
  text-align: center;
  font-size: 1.1rem;
}

.configure-effective-standards-error {
  margin-top: 2rem;
  color: var(--color-error-600);
  background: var(--color-error-50);
  padding: 1rem 1.2rem;
  border-radius: 8px;
  text-align: center;
  font-size: 1.1rem;
}

.configure-effective-standards-assign-standards-section {
  margin-bottom: 2rem;
  position: relative; /* Ensure proper positioning context for dropdowns */
  overflow: visible; /* Allow dropdowns to be visible outside section boundaries */
}
</style>
