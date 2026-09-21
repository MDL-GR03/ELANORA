<template>
  <div class="import-modal-overlay" role="presentation" @click.self="close">
    <div
      ref="dialogElement"
      class="import-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-standards-title"
      tabindex="-1"
    >
      <header class="import-modal-heading">
        <span class="import-modal-icon" aria-hidden="true">
          <font-awesome-icon icon="fa-solid fa-arrow-down" />
        </span>
        <div>
          <span>{{ t('configureNamingStandards.importModal.eyebrow') }}</span>
          <h2 id="import-standards-title">
            {{ t('configureNamingStandards.importModal.heading') }}
          </h2>
        </div>
      </header>
      <button
        ref="closeButton"
        type="button"
        class="import-modal-close"
        :aria-label="t('common.cancel')"
        @click="close"
      >
        <font-awesome-icon icon="fa-solid fa-xmark" />
      </button>

      <section v-if="importStep === 1" class="import-step">
        <h3>{{ t('configureNamingStandards.importModal.selectProject') }}</h3>
        <div class="import-project-select-row">
          <AppSelect
            id="import-naming-project"
            :model-value="selectedImportProject"
            class="import-project-select-control"
            :placeholder="
              t('configureNamingStandards.importModal.chooseProject')
            "
            :options="importProjectOptions"
            @update:model-value="$emit('update:selectedImportProject', $event)"
          />
          <button
            type="button"
            class="primary-action"
            :disabled="!selectedImportProject"
            @click="$emit('next')"
          >
            {{ t('configureNamingStandards.importModal.next') }}
          </button>
        </div>
      </section>

      <section v-else class="import-step import-selection-step">
        <h3>{{ t('configureNamingStandards.importModal.selectStandards') }}</h3>
        <p v-if="importStandards.length === 0" class="empty-state">
          {{ t('configureNamingStandards.importModal.noStandards') }}
        </p>
        <p v-else-if="availableStandards.length === 0" class="empty-state">
          {{ t('configureNamingStandards.importModal.allFiltered') }}
        </p>
        <div v-else class="import-standards-list">
          <article
            v-for="standard in availableStandards"
            :key="standard.id"
            class="import-standard-preview"
          >
            <div class="import-standard-header-col">
              <div class="import-standard-header-row">
                <input
                  :id="`import-standard-${standard.id}`"
                  type="checkbox"
                  :value="standard.id"
                  :checked="selectedStandardIds.includes(standard.id)"
                  :disabled="!hasTargetFileType(standard)"
                  @click.stop
                  @change="toggleSelectedStandard(standard.id, $event)"
                />
                <label :for="`import-standard-${standard.id}`" @click.stop>
                  <strong>{{ standard.name }}</strong>
                  <span
                    v-if="
                      getSourceFileTypeDisplay(standard.project_file_type_id)
                    "
                  >
                    {{
                      getSourceFileTypeDisplay(standard.project_file_type_id)
                    }}
                  </span>
                </label>
                <button
                  type="button"
                  class="import-fold-toggle"
                  :aria-expanded="!isStandardFolded(standard.id)"
                  :aria-controls="`import-standard-details-${standard.id}`"
                  :aria-label="
                    t('configureNamingStandards.importModal.toggleDetails', {
                      name: standard.name,
                    })
                  "
                  @click="$emit('toggle-fold', standard.id)"
                >
                  <font-awesome-icon
                    class="import-standard-chevron"
                    :icon="
                      isStandardFolded(standard.id)
                        ? 'fa-solid fa-chevron-right'
                        : 'fa-solid fa-chevron-down'
                    "
                  />
                </button>
              </div>
              <div
                v-if="!hasTargetFileType(standard)"
                class="import-standard-warning-row"
                @click.stop
              >
                <span>{{
                  t('configureNamingStandards.importModal.fileTypeNotAvailable')
                }}</span>
                <button
                  type="button"
                  class="secondary-action"
                  @click="$emit('import-file-type', standard)"
                >
                  {{ t('configureNamingStandards.importModal.importFileType') }}
                </button>
              </div>
            </div>

            <transition name="fade">
              <div
                v-show="!isStandardFolded(standard.id)"
                :id="`import-standard-details-${standard.id}`"
                class="import-standard-details"
                :class="{ unavailable: !hasTargetFileType(standard) }"
              >
                <dl>
                  <div>
                    <dt>
                      {{ t('configureNamingStandards.importModal.pattern') }}
                    </dt>
                    <dd>
                      <code>{{ standard.pattern }}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>
                      {{
                        t('configureNamingStandards.importModal.description')
                      }}
                    </dt>
                    <dd>{{ standard.description || '—' }}</dd>
                  </div>
                  <div>
                    <dt>
                      {{
                        t('configureNamingStandards.importModal.exampleFile')
                      }}
                    </dt>
                    <dd>
                      <code>{{ buildExampleFilename(standard) }}</code>
                    </dd>
                  </div>
                </dl>
                <div class="component-table-wrap">
                  <table>
                    <caption>
                      {{
                        t('configureNamingStandards.importModal.components')
                      }}
                    </caption>
                    <thead>
                      <tr>
                        <th>
                          {{ t('configureNamingStandards.componentName') }}
                        </th>
                        <th>
                          {{ t('configureNamingStandards.componentRegex') }}
                        </th>
                        <th>
                          {{
                            t(
                              'configureNamingStandards.componentAcceptedValues'
                            )
                          }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="component in getPatternOrderedComponents(
                          standard
                        )"
                        :key="component.id || component.name"
                      >
                        <td>{{ component.name }}</td>
                        <td>
                          <code>{{ component.regex }}</code>
                        </td>
                        <td>
                          {{ component.accepted_values?.join(', ') || '—' }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </transition>
          </article>
        </div>
      </section>

      <footer v-if="importStep === 2" class="import-modal-footer">
        <button
          type="button"
          class="primary-action"
          :disabled="selectedStandardIds.length === 0"
          @click="$emit('import-selected')"
        >
          {{ t('configureNamingStandards.importModal.importSelected') }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useModalDialog } from '@/composables/useModalDialog';

import AppSelect from '@/components/common/AppSelect.vue';

const props = defineProps({
  importStep: { type: Number, required: true },
  selectedImportProject: { type: [Number, String], default: null },
  importProjectOptions: { type: Array, default: () => [] },
  importStandards: { type: Array, default: () => [] },
  existingStandardKeys: { type: Set, required: true },
  selectedStandardIds: { type: Array, default: () => [] },
  targetFileTypeKeys: { type: Set, required: true },
  getSourceFileTypeDisplay: { type: Function, required: true },
  buildExampleFilename: { type: Function, required: true },
  getPatternOrderedComponents: { type: Function, required: true },
  isStandardFolded: { type: Function, required: true },
});
const emit = defineEmits([
  'close',
  'update:selectedImportProject',
  'update:selectedStandardIds',
  'next',
  'toggle-fold',
  'import-file-type',
  'import-selected',
]);
const { t } = useI18n();
const dialogElement = ref(null);
const closeButton = ref(null);

const availableStandards = computed(() =>
  props.importStandards.filter(
    (standard) =>
      !props.existingStandardKeys.has(
        `${standard.name}::${standard.file_type_id}`
      )
  )
);

const hasTargetFileType = (standard) =>
  props.targetFileTypeKeys.has(
    `${standard.file_type_id}:${standard.file_type_name}`
  );

function close() {
  emit('close');
}

useModalDialog(dialogElement, { onClose: close, initialFocus: closeButton });

function toggleSelectedStandard(standardId, event) {
  const selected = new Set(props.selectedStandardIds);
  if (event.target.checked) selected.add(standardId);
  else selected.delete(standardId);
  emit('update:selectedStandardIds', [...selected]);
}
</script>

<style scoped>
.import-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  backdrop-filter: blur(3px);
}

.import-modal {
  position: relative;
  display: flex;
  flex-direction: column;
  width: min(900px, 100%);
  height: min(760px, calc(100vh - 48px));
  padding: 104px 32px 82px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-gray-200);
  border-radius: 18px;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
}

.import-modal-heading {
  position: absolute;
  inset: 0 0 auto;
  display: flex;
  align-items: center;
  min-height: 82px;
  padding: 18px 72px 18px 28px;
  gap: 14px;
  background: linear-gradient(
    145deg,
    var(--color-surface),
    var(--color-blue-50-alt)
  );
  border-bottom: 1px solid var(--color-blue-100);
}

.import-modal-heading > div > span {
  color: var(--color-blue-200-alt);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.import-modal-heading h2,
.import-step h3 {
  margin: 2px 0 0;
  color: var(--color-slate-900);
}

.import-modal-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  color: var(--color-blue-200-alt);
  background: var(--color-blue-100);
  border-radius: 12px;
}

.import-modal-close {
  position: absolute;
  z-index: 2;
  top: 22px;
  right: 24px;
  width: 38px;
  height: 38px;
  color: var(--color-slate-500);
  background: transparent;
  border: 0;
  border-radius: 9px;
  cursor: pointer;
}

.import-modal-close:hover {
  color: var(--color-slate-700);
  background: var(--color-blue-100-subtle);
}

.import-step {
  min-height: 0;
}

.import-step h3 {
  margin-bottom: 1.5rem;
  font-size: 1.05rem;
}

.import-selection-step {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.import-project-select-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.import-project-select-control {
  flex: 1;
}

.primary-action,
.secondary-action {
  min-height: 40px;
  padding: 8px 18px;
  color: var(--color-surface);
  font: inherit;
  background: var(--color-blue-700-alt);
  border: 0;
  border-radius: 7px;
  cursor: pointer;
}

.secondary-action {
  min-height: 34px;
  padding: 5px 12px;
  color: var(--color-amber-900);
  background: var(--color-surface);
  border: 1px solid var(--color-amber-200);
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.empty-state {
  padding: 2rem;
  color: var(--color-slate-500);
  text-align: center;
  background: var(--color-surface-subtle);
  border: 1px dashed var(--color-border-strong);
  border-radius: 10px;
}

.import-standards-list {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.import-standard-preview {
  margin-bottom: 14px;
  background: var(--secondary-bg);
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 10px;
}

.import-standard-header-col {
  padding: 12px;
}

.import-standard-header-row {
  display: flex;
  align-items: center;
  min-height: 36px;
  gap: 0.65rem;
}

.import-standard-header-row label {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 0.35rem 0.6rem;
  cursor: pointer;
}

.import-standard-header-row label span {
  color: var(--color-slate-600);
}

.import-fold-toggle {
  width: 2.75rem;
  height: 2.75rem;
  display: grid;
  margin-left: auto;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 0.55rem;
  background: transparent;
  cursor: pointer;
}

.import-fold-toggle:hover,
.import-fold-toggle:focus-visible {
  border-color: var(--color-blue-200);
  background: var(--color-blue-100);
  outline: none;
}

.import-standard-chevron {
  color: var(--color-gray-blue-100);
}

.import-standard-warning-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  padding: 8px 10px;
  gap: 0.75rem;
  color: var(--color-amber-900);
  background: var(--color-amber-50);
  border-radius: 7px;
}

.import-standard-details {
  padding: 16px;
  border-top: 1px solid var(--color-blue-100-alt);
}

.import-standard-details.unavailable {
  opacity: 0.6;
}

dl {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0 0 16px;
  gap: 12px;
}

dt,
caption {
  color: var(--color-slate-600);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: left;
  text-transform: uppercase;
}

dd {
  margin: 5px 0 0;
  overflow-wrap: anywhere;
}

.component-table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

caption {
  padding-bottom: 7px;
}

th,
td {
  padding: 7px 9px;
  text-align: left;
  border: 1px solid var(--color-blue-100-alt);
}

th {
  background: var(--color-gray-200);
}

.import-modal-footer {
  position: absolute;
  inset: auto 0 0;
  display: flex;
  justify-content: flex-end;
  padding: 16px 28px;
  background: var(--color-f7f9fc);
  border-top: 1px solid var(--color-blue-100);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (width <= 640px) {
  .import-modal-overlay {
    align-items: end;
    padding: 8px;
  }

  .import-modal {
    height: calc(100vh - 16px);
    padding: 96px 16px 76px;
    border-radius: 14px;
  }

  .import-project-select-row,
  .import-standard-warning-row {
    align-items: stretch;
    flex-direction: column;
  }

  dl {
    grid-template-columns: 1fr;
  }

  .primary-action,
  .secondary-action {
    width: 100%;
    min-height: 44px;
  }
}
</style>
