<template>
  <div class="configure-naming-page">
    <div ref="standardsTopRef" class="configure-naming-header">
      <h2 class="configure-naming-title">
        {{ t('configureNamingStandards.title') }}
      </h2>
      <div class="configure-naming-header-actions">
        <button class="configure-naming-add-btn" @click="handleShowAddStandard">
          + {{ t('configureNamingStandards.add') }}
        </button>
        <button class="configure-naming-add-btn" @click="startImportFlow">
          {{
            t('configureNamingStandards.import') ||
            'Import from another project'
          }}
        </button>
      </div>
    </div>
    <div v-if="loading">{{ t('configureNamingStandards.loading') }}</div>
    <div v-else>
      <div v-if="standards.length === 0">
        <em>{{ t('configureNamingStandards.empty') }}</em>
      </div>
      <div>
        <div
          v-for="std in standards"
          :key="std.id"
          class="configure-naming-accordion"
          style="margin-bottom: 32px"
        >
          <div
            class="configure-naming-accordion-header"
            :class="{ open: openStandardId === std.id }"
            @click="toggleAccordion(std.id)"
          >
            <span class="configure-naming-accordion-title">
              {{ std.name
              }}<span v-if="getFileTypeDisplay(std.project_file_type_id)">
                :
                <span class="configure-naming-accordion-filetype">{{
                  getFileTypeDisplay(std.project_file_type_id)
                }}</span></span
              >
            </span>
            <span
              class="configure-naming-accordion-chevron"
              :class="{ open: openStandardId === std.id }"
            >
              <font-awesome-icon icon="fa-solid fa-chevron-down" />
            </span>
          </div>
          <transition name="accordion">
            <div
              v-if="openStandardId === std.id"
              class="configure-naming-accordion-body"
            >
              <div
                v-if="std.description"
                class="configure-naming-accordion-desc-box"
              >
                <span class="configure-naming-desc-label">{{
                  t('configureNamingStandards.description')
                }}</span>
                <span class="configure-naming-desc-content">{{
                  std.description
                }}</span>
              </div>
              <div class="configure-naming-pattern-example-label">
                {{ t('configureNamingStandards.exampleFile') }}
              </div>
              <div class="configure-naming-pattern-example-value">
                <code>{{ buildExampleFilename(std) }}</code>
              </div>
              <div class="configure-naming-accordion-pattern">
                <div class="configure-naming-pattern-label">
                  {{ t('configureNamingStandards.pattern') }}
                </div>
                <div class="configure-naming-pattern-value">
                  {{ std.pattern }}
                </div>
                <div class="configure-naming-pattern-breakdown">
                  <div class="breakdown-groups">
                    <template
                      v-for="comp in getPatternOrderedComponents(std)"
                      :key="comp.id || comp.name"
                    >
                      <span class="breakdown-group">
                        <span class="breakdown-group-name">{{
                          comp.name
                        }}</span>
                        <span class="breakdown-group-arrow">→</span>
                        <span class="breakdown-group-value">{{
                          getExampleValuesForStandard(std)[comp.name]
                        }}</span>
                      </span>
                    </template>
                  </div>
                </div>
              </div>
              <div class="configure-naming-accordion-components">
                <div class="configure-naming-components-title">
                  {{ t('configureNamingStandards.componentsTable') }}
                </div>
                <table class="configure-naming-components-table">
                  <thead>
                    <tr>
                      <th>{{ t('configureNamingStandards.componentName') }}</th>
                      <th>
                        {{ t('configureNamingStandards.componentRegex') }}
                      </th>
                      <th>{{ t('configureNamingStandards.exampleFile') }}</th>
                      <th>
                        {{
                          t('configureNamingStandards.componentAcceptedValues')
                        }}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="component in getPatternOrderedComponents(std)"
                      :key="component.id || component.name"
                    >
                      <td class="configure-naming-component-name">
                        {{ component.name }}
                      </td>
                      <td class="configure-naming-component-regex">
                        {{ component.regex }}
                      </td>
                      <td>
                        {{ getExampleValuesForStandard(std)[component.name] }}
                      </td>
                      <td>
                        <span
                          v-if="
                            component.accepted_values &&
                            component.accepted_values.length
                          "
                        >
                          {{
                            component.accepted_values
                              .map((val) =>
                                typeof val === 'object' &&
                                val !== null &&
                                'value' in val
                                  ? val.value
                                  : val
                              )
                              .join(', ')
                          }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="configure-naming-accordion-actions">
                <button
                  class="configure-naming-btn delete"
                  @click="deleteStandard(std.id)"
                >
                  {{ t('configureNamingStandards.delete') }}
                </button>
              </div>
            </div>
          </transition>
        </div>
      </div>
      <div
        v-if="showAddStandard"
        ref="addFormRef"
        class="configure-naming-add-form"
      >
        <div class="configure-naming-add-title">
          {{ t('configureNamingStandards.add') }}
        </div>
        <form class="configure-naming-add-fields" @submit.prevent="addStandard">
          <!-- Name -->
          <div class="configure-naming-form-row">
            <label for="standard-name">{{
              t('configureNamingStandards.name')
            }}</label>
            <input
              id="standard-name"
              v-model="newStandard.name"
              :placeholder="t('configureNamingStandards.name')"
              required
            />
          </div>
          <!-- Description -->
          <div class="configure-naming-form-row">
            <label for="standard-desc">{{
              t('configureNamingStandards.description')
            }}</label>
            <input
              id="standard-desc"
              v-model="newStandard.description"
              :placeholder="t('configureNamingStandards.description')"
            />
          </div>
          <!-- File type -->
          <div class="configure-naming-form-row">
            <label for="standard-filetype">{{
              t('configureNamingStandards.fileType')
            }}</label>
            <AppSelect
              id="standard-filetype"
              v-model="newStandard.project_file_type_id"
              :required="true"
              :placeholder="t('configureNamingStandards.fileType')"
              :options="fileTypeOptions"
              @change="onFileTypeChange"
            />
          </div>
          <!-- Pattern: prefix + comma pattern -->
          <div class="configure-naming-form-row">
            <label for="pattern-comma-input">{{
              t('configureNamingStandards.pattern')
            }}</label>
            <div class="configure-naming-pattern-row">
              <input
                class="configure-naming-prefix-box"
                :title="prefixValue"
                :value="prefixValue"
                readonly
                tabindex="-1"
              />
              <span class="configure-naming-pattern-sep">+</span>
              <input
                id="pattern-comma-input"
                v-model="commaPattern"
                class="configure-naming-pattern-box"
                :title="commaPattern"
                :placeholder="t('configureNamingStandards.commaPattern')"
                required
                @input="onCommaPatternInput"
              />
            </div>
          </div>

          <!-- New section for example and accepted separators, one under another -->
          <div class="configure-naming-pattern-info-section">
            <div class="configure-naming-example-desc">
              <span>
                {{
                  t('configureNamingStandards.exampleCommaPatternDesc', {
                    example: 'CLSFBI1912A_S040_B',
                  })
                }}
              </span>
              <span class="configure-naming-accepted-separators">
                <b>{{ t('configureNamingStandards.acceptedSeparators') }}</b
                >: {{ knownSeparators.map((s) => `"${s}"`).join(', ') }}
              </span>
            </div>
            <div class="configure-naming-example-desc">
              <code>{{ exampleCommaPattern }}</code>
            </div>
          </div>
          <!-- Example and extraction -->
          <div class="configure-naming-form-row">
            <label for="example-file-input">{{
              t('configureNamingStandards.exampleFile')
            }}</label>
            <div class="configure-naming-example-block">
              <input
                id="example-file-input"
                v-model="exampleFilename"
                :placeholder="t('configureNamingStandards.exampleFile')"
                class="configure-naming-example-input"
              />
              <button
                type="button"
                class="configure-naming-btn"
                @click="extractRegexFromExample"
              >
                {{ t('configureNamingStandards.extractRegex') }}
              </button>
            </div>
          </div>
          <!-- Components (optional, can be hidden or shown as needed) -->
          <div class="configure-naming-components-section">
            <label
              class="configure-naming-components-label"
              for="components-table"
              >{{ t('configureNamingStandards.componentsTable') }}</label
            >
            <table
              id="components-table"
              class="configure-naming-components-table configure-naming-components-edit-table"
            >
              <thead>
                <tr>
                  <th>{{ t('configureNamingStandards.componentName') }}</th>
                  <th>{{ t('configureNamingStandards.componentRegex') }}</th>
                  <th>
                    {{ t('configureNamingStandards.componentDescription') }}
                  </th>
                  <th>
                    {{ t('configureNamingStandards.componentAcceptedValues') }}
                  </th>
                  <th>{{ t('configureNamingStandards.componentOrder') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(comp, idx) in newStandard.components"
                  :key="comp.name"
                  class="configure-naming-component-row"
                >
                  <td>
                    <input
                      v-model="comp.name"
                      placeholder="Component name"
                      readonly
                      class="configure-naming-components-table-prefix-disabled"
                      :tabindex="
                        idx === 0 && comp.name.startsWith('prefix_') ? -1 : 0
                      "
                    />
                  </td>
                  <td>
                    <input
                      v-model="comp.regex"
                      placeholder="Regex"
                      :readonly="idx === 0 && comp.name.startsWith('prefix_')"
                      :class="{
                        'configure-naming-components-table-prefix-disabled':
                          idx === 0 && comp.name.startsWith('prefix_'),
                      }"
                      :tabindex="
                        idx === 0 && comp.name.startsWith('prefix_') ? -1 : 0
                      "
                    />
                  </td>
                  <td>
                    <input
                      v-model="comp.description"
                      placeholder="Description"
                    />
                  </td>
                  <td>
                    <input
                      v-model="comp.accepted_values_str"
                      :placeholder="getAcceptedValuesPlaceholder(comp)"
                      :title="getAcceptedValuesPlaceholder(comp)"
                      @input="onAcceptedValuesInput(comp)"
                    />
                  </td>
                  <td>
                    <span class="configure-naming-component-order"
                      >#{{ comp.order }}</span
                    >
                  </td>
                </tr>
              </tbody>
            </table>
            <div
              v-if="shouldShowAcceptedValuesWarning"
              class="configure-naming-warning"
              style="margin-top: 4px"
            >
              <span>
                <b>{{
                  t('configureNamingStandards.noteAcceptedValues', {
                    value: detectedUnusualAcceptedValue,
                  })
                }}</b>
              </span>
            </div>
            <div
              v-if="regexExtractionError"
              ref="errorMessageRef"
              class="configure-naming-error"
              style="margin-top: 4px"
            >
              {{ regexExtractionError }}
            </div>
          </div>
          <div class="configure-naming-form-actions">
            <button
              class="configure-naming-btn"
              type="submit"
              :disabled="!!regexExtractionError"
            >
              {{ t('configureNamingStandards.add') }}
            </button>
            <button
              class="configure-naming-btn cancel"
              type="button"
              @click="resetAddForm"
            >
              {{ t('configureNamingStandards.cancel') }}
            </button>
          </div>
        </form>
      </div>
    </div>
    <UserPrompt
      v-model="userPromptVisible"
      :message="userPromptMessage"
      :default-value="userPromptDefault"
      :validator="userPromptValidator"
      :type="userPromptType"
      @submit="handleUserPromptSubmit"
      @cancel="handleUserPromptCancel"
    />
    <!-- Import Modal -->
    <div
      v-if="showImportModal"
      class="import-modal-overlay"
      role="presentation"
    >
      <div
        class="import-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-standards-title"
        @keydown.esc="showImportModal = false"
      >
        <div class="import-modal-heading">
          <span class="import-modal-icon">
            <font-awesome-icon icon="fa-solid fa-arrow-down" />
          </span>
          <div>
            <span>Reuse configuration</span>
            <h2 id="import-standards-title">Import naming standards</h2>
          </div>
        </div>
        <button
          type="button"
          class="import-modal-close"
          :aria-label="t('common.cancel')"
          @click="showImportModal = false"
        >
          <font-awesome-icon icon="fa-solid fa-xmark" />
        </button>
        <div v-if="importStep === 1">
          <h3 style="margin-bottom: 1.5em">
            {{ t('configureNamingStandards.importModal.selectProject') }}
          </h3>
          <div class="import-project-select-row">
            <AppSelect
              id="import-naming-project"
              v-model="selectedImportProject"
              class="import-project-select-control"
              :placeholder="
                t('configureNamingStandards.importModal.chooseProject')
              "
              :options="importProjectOptions"
            />
            <button
              class="configure-naming-btn"
              :disabled="!selectedImportProject"
              style="margin-left: 1em"
              @click="goToImportStep2"
            >
              {{ t('configureNamingStandards.importModal.next') }}
            </button>
          </div>
        </div>
        <div v-else-if="importStep === 2">
          <h3 style="margin-bottom: 1em">
            {{ t('configureNamingStandards.importModal.selectStandards') }}
          </h3>
          <div v-if="importStandards.length === 0">
            <em>{{ t('configureNamingStandards.importModal.noStandards') }}</em>
          </div>
          <div v-else>
            <template
              v-if="
                importStandards.filter(
                  (s) =>
                    !existingStandardKeys.has(`${s.name}::${s.file_type_id}`)
                ).length === 0
              "
            >
              <em>{{
                t('configureNamingStandards.importModal.allFiltered')
              }}</em>
            </template>
            <div v-else class="import-standards-list">
              <div
                v-for="std in importStandards.filter(
                  (s) =>
                    !existingStandardKeys.has(`${s.name}::${s.file_type_id}`)
                )"
                :key="std.id"
                class="import-standard-preview"
              >
                <div
                  class="import-standard-header-col"
                  @click="toggleStandardFold(std.id)"
                >
                  <div class="import-standard-header-row">
                    <input
                      v-model="selectedStandardIds"
                      type="checkbox"
                      :value="std.id"
                      :disabled="
                        !targetFileTypeKeys.has(
                          `${std.file_type_id}:${std.file_type_name}`
                        )
                      "
                      @click.stop
                    />
                    <span style="font-weight: bold; margin-left: 0.5em">
                      {{ std.name }}
                      <span
                        v-if="
                          getSourceFileTypeDisplay(std.project_file_type_id)
                        "
                        style="font-weight: normal; color: #2563eb"
                      >
                        :
                        {{ getSourceFileTypeDisplay(std.project_file_type_id) }}
                      </span>
                    </span>
                    <span
                      class="import-standard-chevron"
                      style="margin-left: auto"
                    >
                      <font-awesome-icon
                        :icon="
                          isStandardFolded(std.id)
                            ? 'fa-solid fa-chevron-right'
                            : 'fa-solid fa-chevron-down'
                        "
                      />
                    </span>
                  </div>
                  <template
                    v-if="
                      !targetFileTypeKeys.has(
                        `${std.file_type_id}:${std.file_type_name}`
                      )
                    "
                  >
                    <hr class="import-standard-header-separator" />
                    <div class="import-standard-warning-row" @click.stop>
                      <span style="color: #e74c3c">
                        {{
                          t(
                            'configureNamingStandards.importModal.fileTypeNotAvailable'
                          )
                        }}
                      </span>
                      <button
                        class="configure-naming-btn import-filetype-btn"
                        style="
                          margin-left: 1em;
                          font-size: 0.9em;
                          padding: 3px 10px;
                        "
                        tabindex="0"
                        @click.stop.prevent="importMissingFileType(std)"
                      >
                        {{
                          t(
                            'configureNamingStandards.importModal.importFileType'
                          )
                        }}
                      </button>
                    </div>
                  </template>
                </div>
                <transition name="fade">
                  <div
                    v-show="!isStandardFolded(std.id)"
                    :class="{
                      'import-standard-greyed': !targetFileTypeKeys.has(
                        `${std.file_type_id}:${std.file_type_name}`
                      ),
                    }"
                    class="import-standard-details"
                  >
                    <div>
                      <b>{{
                        t('configureNamingStandards.importModal.pattern')
                      }}</b>
                      <div>
                        {{ std.pattern }}
                      </div>
                    </div>
                    <div>
                      <b>{{
                        t('configureNamingStandards.importModal.description')
                      }}</b>
                      <div>
                        {{ std.description }}
                      </div>
                    </div>
                    <div>
                      <b>{{
                        t('configureNamingStandards.importModal.exampleFile')
                      }}</b>
                      <div>
                        {{ buildExampleFilename(std) }}
                      </div>
                    </div>
                    <div>
                      <b>{{
                        t('configureNamingStandards.importModal.components')
                      }}</b>
                      <table
                        class="configure-naming-components-table"
                        style="margin-top: 0.5em"
                      >
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
                            v-for="comp in getPatternOrderedComponents(std)"
                            :key="comp.id || comp.name"
                          >
                            <td>{{ comp.name }}</td>
                            <td>{{ comp.regex }}</td>
                            <td>
                              <span
                                v-if="
                                  comp.accepted_values &&
                                  comp.accepted_values.length
                                "
                              >
                                {{ comp.accepted_values.join(', ') }}
                              </span>
                              <span v-else>
                                ({{
                                  t(
                                    'configureNamingStandards.componentAcceptedValues'
                                  )
                                }})
                              </span>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </transition>
              </div>
            </div>
          </div>
        </div>
        <div class="import-modal-footer">
          <button
            class="configure-naming-btn"
            :disabled="selectedStandardIds.length === 0"
            @click="importSelectedStandards"
          >
            {{ t('configureNamingStandards.importModal.importSelected') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import UserPrompt from '@components/common/UserPrompt.vue';
import AppSelect from '@/components/common/AppSelect.vue';
import projectNamingStandardApi from '@/api/service/projectNamingStandard.js';
import fileTypeService from '@/api/service/fileTypeService.js';
import { ref, onMounted, watch, computed, nextTick } from 'vue';
import { useNamingStandardStore } from '@stores/namingStandard';
import { useFileTypeStore } from '@stores/fileType';
import { useRoute } from 'vue-router';
import { useEventMessageStore } from '@stores/eventMessage';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useNamingStandardImport } from '@/composables/useNamingStandardImport';
import { useI18n } from 'vue-i18n';
import {
  acceptedValuesPlaceholder,
  inferPatternComponents,
  KNOWN_NAMING_SEPARATORS,
  normalizeNumericAcceptedValues,
} from '@/utils/namingStandardPattern';

const namingStandardStore = useNamingStandardStore();
const route = useRoute();
const { t } = useI18n();
const projectId = computed(() => Number(route.params.projectId));
const userConfirm = useUserConfirm();

const loading = computed(() => namingStandardStore.isLoading);
const standards = computed(() => {
  return [...namingStandardStore.standards].sort((a, b) => {
    // First sort by name alphabetically
    const nameComparison = a.name.localeCompare(b.name);
    if (nameComparison !== 0) return nameComparison;

    // If names are equal, sort by file type display name
    const fileTypeA = getFileTypeDisplay(a.project_file_type_id);
    const fileTypeB = getFileTypeDisplay(b.project_file_type_id);
    return fileTypeA.localeCompare(fileTypeB);
  });
});
const showAddStandard = ref(false);
const newStandard = ref({
  name: '',
  project_file_type_id: '',
  pattern: '',
  description: '',
  components: [],
});

const userPromptVisible = ref(false);
const userPromptMessage = ref('');
const userPromptDefault = ref('');
const userPromptValidator = ref(null);
const userPromptType = ref('text');

let userPromptResolve = null;

function showUserPrompt(
  message,
  defaultValue = '',
  validator = null,
  type = 'text'
) {
  userPromptMessage.value = message;
  userPromptDefault.value = defaultValue;
  userPromptValidator.value = validator;
  userPromptType.value = type;
  userPromptVisible.value = true;
  return new Promise((resolve) => {
    userPromptResolve = resolve;
  });
}

function handleUserPromptSubmit(val) {
  userPromptVisible.value = false;
  if (userPromptResolve) userPromptResolve(val);
}
function handleUserPromptCancel() {
  userPromptVisible.value = false;
  if (userPromptResolve) userPromptResolve(null);
}

function onAcceptedValuesInput(comp) {
  regexExtractionError.value = '';
  if (typeof comp.accepted_values_str === 'string') {
    let length = null;
    let isDigitRegex = false;
    if (comp.regex) {
      const match = comp.regex.match(/\\p\{N\}\{(\d+)\}/u);
      if (match) {
        length = parseInt(match[1]);
        isDigitRegex = true;
      }
    }
    let input = comp.accepted_values_str;
    if (isDigitRegex) {
      const { values, error } = normalizeNumericAcceptedValues(input, length);
      if (error) {
        regexExtractionError.value = error;
        return;
      }
      comp.accepted_values = values;
      comp.accepted_values_str = values.join(', ');
      return;
    }

    let values = [];
    for (let part of input.split(/[,;]/)) {
      values.push(part.trim());
    }
    values = [...new Set(values)];

    if (length !== null) {
      for (const val of values) {
        if (val.length !== length) {
          regexExtractionError.value = t(
            'configureNamingStandards.acceptedValuesLength',
            { name: comp.name, length }
          );
          return;
        }
      }
    }

    if (comp.regex) {
      let regexStr = comp.regex;
      let re;
      try {
        re = new RegExp('^' + regexStr + '$', 'u');
      } catch {
        regexExtractionError.value = `Invalid regex for "${comp.name}".`;
        return;
      }
      for (const val of values) {
        if (!re.test(val)) {
          regexExtractionError.value = `Accepted value "${val}" does not match regex "${comp.regex}" for "${comp.name}".`;
          return;
        }
      }
    }

    comp.accepted_values = values;
  } else {
    comp.accepted_values = [];
  }
}

// Remove unused getFileTypeName
function getFileTypeNameRaw(project_file_type_id) {
  const ft = fileTypes.value.find((f) => f.id === project_file_type_id);
  return ft ? ft.name : '';
}

function getFileTypeDisplay(project_file_type_id) {
  const ft = fileTypes.value.find((f) => f.id === project_file_type_id);
  if (!ft) return '';
  return `${ft.name} (${ft.extension})${ft.description ? ' — ' + ft.description : ''}`;
}

const fileTypes = ref([]);
const fileTypeOptions = computed(() =>
  fileTypes.value.map((fileType) => ({
    value: fileType.id,
    label: `${fileType.name} (${fileType.extension})`,
    description: fileType.description || undefined,
  }))
);
const exampleFilename = ref('');
const regexExtractionError = ref('');
const commaPattern = ref('');
const exampleCommaPattern = t('configureNamingStandards.exampleCommaPattern');
const knownSeparators = KNOWN_NAMING_SEPARATORS;
const errorMessageRef = ref(null);

function onCommaPatternInput() {
  const fileType = getFileTypeNameRaw(newStandard.value.project_file_type_id);
  if (!commaPattern.value || !fileType) {
    newStandard.value.pattern = '';
    newStandard.value.components = [];
    return;
  }
  const parts = commaPattern.value.split(',').map((p) => p.trim());
  let pattern = `{prefix_${fileType}}`;
  let prevComponents = newStandard.value.components || [];
  let newComponents = [
    // Always keep prefix as first component
    prevComponents.length > 0 && prevComponents[0].name.startsWith('prefix_')
      ? { ...prevComponents[0], name: `prefix_${fileType}`, order: 1 }
      : {
          name: `prefix_${fileType}`,
          regex: '',
          description: '',
          order: 1,
          accepted_values: [],
          accepted_values_str: '',
        },
  ];
  let order = 2;
  for (const part of parts) {
    if (knownSeparators.includes(part)) {
      pattern += part;
    } else {
      pattern += `{${part}}`;
      // Try to find previous component with same name
      const prev = prevComponents.find((c) => c.name === part);
      newComponents.push(
        prev
          ? { ...prev, order }
          : {
              name: part,
              regex: '',
              description: '',
              order,
              accepted_values: [],
              accepted_values_str: '',
            }
      );
      order++;
    }
  }
  newStandard.value.pattern = pattern;
  newStandard.value.components = newComponents;
}

async function extractRegexFromExample() {
  regexExtractionError.value = '';
  const pattern = newStandard.value.pattern;
  const example = exampleFilename.value.trim();

  if (!newStandard.value.project_file_type_id) {
    regexExtractionError.value = t(
      'configureNamingStandards.selectFileTypeFirst'
    );
    return;
  }
  if (!commaPattern.value) {
    regexExtractionError.value = t(
      'configureNamingStandards.commaPatternRequired'
    );
    return;
  }
  if (!example) {
    regexExtractionError.value = t(
      'configureNamingStandards.exampleFileRequired'
    );
    return;
  }
  if (!pattern) {
    regexExtractionError.value = t('configureNamingStandards.patternRequired');
    return;
  }

  const result = await inferPatternComponents({
    pattern,
    example,
    showPrompt: showUserPrompt,
    translate: t,
  });
  if (result.error) {
    regexExtractionError.value = result.error;
    return;
  }
  newStandard.value.components = result.components;
}
const addFormRef = ref(null);
const standardsTopRef = ref(null);

async function handleShowAddStandard() {
  showAddStandard.value = true;
  nextTick(() => {
    if (addFormRef.value) {
      addFormRef.value.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  });
}

async function addStandard() {
  const exists = namingStandardStore.standards.some(
    (std) =>
      std.name.trim().toLowerCase() ===
        newStandard.value.name.trim().toLowerCase() &&
      std.project_file_type_id === newStandard.value.project_file_type_id
  );
  if (exists) {
    eventMessageStore.addMessage(
      t('configureNamingStandards.eventMessages.addFailedDuplicate'),
      'error',
      7000
    );
    return;
  }

  // Block if any regex is empty or only whitespace
  const hasEmptyRegex = newStandard.value.components.some(
    (c) => !c.regex || !c.regex.trim()
  );
  if (hasEmptyRegex) {
    eventMessageStore.addMessage(
      t('configureNamingStandards.eventMessages.addFailedEmptyRegex'),
      'error',
      7000
    );
    return;
  }

  if (regexExtractionError.value) return;
  try {
    const standardData = {
      name: newStandard.value.name.trim(),
      project_id: projectId.value,
      project_file_type_id: newStandard.value.project_file_type_id,
      pattern: newStandard.value.pattern,
      description: newStandard.value.description.trim(),
      components: newStandard.value.components.map((c) => ({
        name: c.name,
        regex: c.regex,
        description: c.description,
        order: c.order,
        accepted_values: c.accepted_values,
        project_file_type_id: newStandard.value.project_file_type_id,
      })),
    };

    // Clear cache before adding
    exampleValuesCache.value = {};

    await namingStandardStore.addNamingStandard(standardData, projectId.value);
    showAddStandard.value = false;
    resetAddForm();
    eventMessageStore.addMessage(
      t('configureNamingStandards.eventMessages.addSuccess'),
      'success',
      4000
    );

    // Ensure DOM updates and scroll to top
    await nextTick();
    if (standardsTopRef.value) {
      standardsTopRef.value.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  } catch (err) {
    if (err?.response?.status === 409) {
      eventMessageStore.addMessage(
        t('configureNamingStandards.eventMessages.addFailedDuplicate'),
        'error',
        7000
      );
    } else {
      eventMessageStore.addMessage(
        t('configureNamingStandards.eventMessages.addFailed'),
        'error',
        7000
      );
    }
  }
}

async function deleteStandard(id) {
  const confirmed = await userConfirm({
    message: t('configureNamingStandards.deleteConfirm'),
    confirmText: t('common.confirm'),
    cancelText: t('common.cancel'),
  });
  if (!confirmed) return;
  try {
    // Clear cache before deleting
    exampleValuesCache.value = {};

    await namingStandardStore.deleteNamingStandard(id, projectId.value);
    eventMessageStore.addMessage(
      'configureNamingStandards.eventMessages.deleteSuccess',
      'success',
      4000
    );
  } catch {
    eventMessageStore.addMessage(
      'configureNamingStandards.eventMessages.deleteFailed',
      'error',
      7000
    );
  }
}

// --- Composition API setup ---
const fileTypeStore = useFileTypeStore();
const eventMessageStore = useEventMessageStore();

onMounted(async () => {
  await namingStandardStore.fetchStandardsAndComponentNames(projectId.value);
});

watch(
  () => newStandard.value.project_file_type_id,
  (newVal, oldVal) => {
    if (newVal !== oldVal) {
      // If commaPattern is set, rebuild the pattern and components with new prefix
      if (commaPattern.value) {
        onCommaPatternInput();
      } else if (newStandard.value.pattern) {
        // Only update prefix in pattern and components if pattern exists
        const fileType = getFileTypeNameRaw(newVal);
        if (!fileType) return;
        newStandard.value.pattern = newStandard.value.pattern.replace(
          /\{prefix_[^}]+\}/,
          `{prefix_${fileType}}`
        );
        if (
          Array.isArray(newStandard.value.components) &&
          newStandard.value.components.length > 0
        ) {
          newStandard.value.components[0].name = `prefix_${fileType}`;
        }
      }
    }
  }
);

watch(
  () => fileTypeStore.fileTypes,
  () => {
    fileTypes.value = [...fileTypeStore.fileTypes];
  },
  { immediate: true }
);

watch(
  () => newStandard.value,
  () => {},
  { deep: true }
);

watch(regexExtractionError, async (val) => {
  if (val) {
    await nextTick();
    errorMessageRef.value?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }
});

const openStandardId = ref(null);
function toggleAccordion(id) {
  openStandardId.value = openStandardId.value === id ? null : id;
}

/**
 * Returns components in the order they appear in the pattern string.
 * This ensures pattern groups and table rows match the pattern order.
 */
function getPatternOrderedComponents(std) {
  if (!std?.pattern || !Array.isArray(std.components)) return [];
  // Extract component names in order from the pattern
  const names = Array.from(std.pattern.matchAll(/\{([^}]+)\}/g)).map(
    (m) => m[1]
  );
  // Map names to actual component objects
  return names
    .map((name) => std.components.find((c) => c.name === name))
    .filter(Boolean);
}

const exampleValuesCache = ref({});
function getExampleValuesForStandard(std) {
  if (!std || !std.components) return {};
  if (!exampleValuesCache.value[std.id]) {
    const values = {};
    for (const comp of std.components) {
      values[comp.name] = pickRandomAcceptedValue(comp);
    }
    exampleValuesCache.value[std.id] = values;
  }
  return exampleValuesCache.value[std.id];
}

// Call this whenever standards change to clear the cache
watch(
  standards,
  (newStandards, oldStandards) => {
    // Clear cache when standards change
    exampleValuesCache.value = {};

    // Force reactivity update for newly added standards
    if (newStandards.length > (oldStandards?.length || 0)) {
      nextTick(() => {
        // Trigger re-computation of example values for all standards
        newStandards.forEach((std) => {
          if (std.id && !exampleValuesCache.value[std.id]) {
            // This will trigger the cache to be populated
            getExampleValuesForStandard(std);
          }
        });
      });
    }
  },
  { immediate: true, deep: true }
);

/**
 * Returns the example filename for a standard, including the file extension.
 */
function buildExampleFilename(std) {
  let filename = std.pattern;
  const orderedComps = getPatternOrderedComponents(std);
  if (!orderedComps.length) return filename;
  const exampleValues = getExampleValuesForStandard(std);
  for (const comp of orderedComps) {
    filename = filename.replace(
      new RegExp(`\\{${comp.name}\\}`, 'g'),
      exampleValues[comp.name] ?? ''
    );
  }
  // Add extension if available
  const ft = fileTypes.value.find((f) => f.id === std.project_file_type_id);
  if (ft && ft.extension) {
    const ext = ft.extension.startsWith('.')
      ? ft.extension
      : '.' + ft.extension;
    filename += ext;
  }
  return filename;
}

function pickRandomAcceptedValue(comp) {
  if (!comp.accepted_values || !comp.accepted_values.length) {
    // fallback: use a generic value
    // Use Unicode digit class
    const digitMatch = comp.regex.match(/\\p\{N\}\{(\d+)\}/u);
    if (digitMatch) {
      const len = parseInt(digitMatch[1]);
      return String(Math.floor(Math.random() * Math.pow(10, len))).padStart(
        len,
        '0'
      );
    }
    // Use Unicode letter class
    const letterMatch = comp.regex.match(/\\p\{L\}\{(\d+)\}/u);
    if (letterMatch) {
      const len = parseInt(letterMatch[1]);
      let str = '';
      // Use basic Latin letters for example, but could be any Unicode letter
      for (let i = 0; i < len; i++)
        str += String.fromCharCode(65 + Math.floor(Math.random() * 26));
      return str;
    }
    return comp.name.toUpperCase();
  }
  // Pick a random accepted value
  const val =
    comp.accepted_values[
      Math.floor(Math.random() * comp.accepted_values.length)
    ];
  // If it's a range like "001-150", pick a random in range and pad
  if (/^\d+-\d+$/.test(val)) {
    const [start, end] = val.split('-').map(Number);
    const rand = Math.floor(Math.random() * (end - start + 1)) + start;
    // Pad to the same length as start/end
    const padLen = Math.max(String(start).length, String(end).length);
    return String(rand).padStart(padLen, '0');
  }
  return val;
}

// Computed prefix value for the pattern
const prefixValue = computed(() => {
  const ft = fileTypes.value.find(
    (f) => f.id === newStandard.value.project_file_type_id
  );
  return ft ? `prefix_${ft.name}` : '';
});

function onFileTypeChange() {
  // Only update prefix, don't clear pattern/components
  const fileType = getFileTypeNameRaw(newStandard.value.project_file_type_id);
  if (!fileType) return;
  if (newStandard.value.pattern) {
    newStandard.value.pattern = newStandard.value.pattern.replace(
      /\{prefix_[^}]+\}/,
      `{prefix_${fileType}}`
    );
  }
  if (
    Array.isArray(newStandard.value.components) &&
    newStandard.value.components.length > 0
  ) {
    newStandard.value.components[0].name = `prefix_${fileType}`;
  }
}

function resetAddForm() {
  showAddStandard.value = false;
  newStandard.value = {
    name: '',
    project_file_type_id: '',
    pattern: '',
    description: '',
    components: [],
  };
  commaPattern.value = '';
  exampleFilename.value = '';
  regexExtractionError.value = '';
  nextTick(() => {
    if (standardsTopRef.value) {
      standardsTopRef.value.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  });
}

// Detect if any accepted_values_str looks like "B A W" (single value, multiple tokens separated by space)
const detectedUnusualAcceptedValue = computed(() => {
  for (const comp of newStandard.value.components) {
    if (
      typeof comp.accepted_values_str === 'string' &&
      comp.accepted_values_str.trim() &&
      // Only one value, but contains spaces (and not commas/semicolons)
      !comp.accepted_values_str.includes(',') &&
      !comp.accepted_values_str.includes(';') &&
      comp.accepted_values_str.trim().split(/\s+/).length > 1
    ) {
      return comp.accepted_values_str.trim();
    }
  }
  return '';
});

const shouldShowAcceptedValuesWarning = computed(
  () => !!detectedUnusualAcceptedValue.value
);

function getAcceptedValuesPlaceholder(comp) {
  return acceptedValuesPlaceholder(comp.regex);
}

// Import modal
const {
  existingStandardKeys,
  getSourceFileTypeDisplay,
  goToImportStep2,
  importMissingFileType,
  importProjectOptions,
  importSelectedStandards,
  importStandards,
  importStep,
  isStandardFolded,
  selectedImportProject,
  selectedStandardIds,
  showImportModal,
  startImportFlow,
  targetFileTypeKeys,
  toggleStandardFold,
} = useNamingStandardImport({
  projectId,
  standards,
  fileTypes,
  namingStandardStore,
  fileTypeStore,
  eventMessages: eventMessageStore,
  translate: t,
  namingApi: projectNamingStandardApi,
  fileTypeApi: fileTypeService,
  clearExampleCache: () => {
    exampleValuesCache.value = {};
  },
});
</script>

<style scoped>
.configure-naming-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e0e0e0;
}

.configure-naming-title {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  color: #1f2937;
}

.configure-naming-header-actions {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-left: 2rem;
}

.configure-naming-add-btn {
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 10px 26px;
  cursor: pointer;
  transition: background 0.18s;
  display: block;
  width: 100%;
  margin: 0;
}

.configure-naming-add-btn:hover {
  background: #1565c0;
}

.configure-naming-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.configure-naming-accordion {
  margin-bottom: 18px;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 1px 4px #0001;
}

.configure-naming-accordion-header {
  padding: 14px 18px;
  font-size: 1.1rem;
  font-weight: 500;
  background: #e9eef5;
  border-radius: 8px 8px 0 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  user-select: none;
  transition: background 0.2s;
}

.configure-naming-accordion-header.open {
  background: #dbe7fa;
}

.configure-naming-accordion-chevron {
  font-size: 1.2rem;
  transition: transform 0.2s;
}

.configure-naming-accordion-chevron.open {
  transform: rotate(180deg);
}

.configure-naming-accordion-body {
  padding: 18px 22px 22px;
  background: #f7fafd;
  border-radius: 0 0 8px 8px;
}

.configure-naming-accordion-desc-box {
  background: #f3f6fa;
  border-left: 4px solid #3b82f6;
  padding: 10px 18px;
  margin-bottom: 1rem;
  border-radius: 6px;
  color: #2a2a2a;
  font-size: 1.08rem;
  display: flex;
  gap: 8px;
  align-items: center;
}

.configure-naming-desc-label {
  font-weight: 600;
  color: #2563eb;
}

.configure-naming-desc-content {
  color: #444;
}

.configure-naming-accordion-pattern {
  margin-bottom: 10px;
}

.configure-naming-pattern-label,
.configure-naming-pattern-example-label {
  font-weight: 600;
  color: #444;
}

.configure-naming-pattern-value,
.configure-naming-pattern-example-value {
  margin-bottom: 1rem;
  color: #2a2a2a;
}

.configure-naming-pattern-info-section {
  display: flex;
  flex-direction: column;
  margin-bottom: 1rem;
}

.configure-naming-example-comma-pattern {
  display: block;
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overflow-wrap: break-word;
  white-space: pre-line;
}

.configure-naming-pattern-breakdown {
  margin-top: 10px;
  margin-bottom: 10px;
}

.breakdown-title {
  font-weight: 600;
  color: #444;
  margin-bottom: 4px;
}

.breakdown-groups {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 1rem;
}

.breakdown-group {
  background: #e9eef5;
  border-radius: 5px;
  padding: 4px 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.98rem;
}

.breakdown-group-name {
  font-weight: 600;
  color: #2563eb;
}

.breakdown-group-arrow {
  color: #888;
}

.breakdown-group-value {
  color: #222;
}

.configure-naming-accordion-components {
  margin-bottom: 10px;
}

.configure-naming-components-title {
  font-weight: 600;
  margin-bottom: 6px;
}

.configure-naming-components-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  background: #fff;
}

.configure-naming-components-table th,
.configure-naming-components-table td {
  border: 1px solid #e0e0e0;
  padding: 6px 10px;
  text-align: left;
  overflow-wrap: break-word;
  max-width: 180px;
  white-space: pre-line;
  box-sizing: border-box;
}

.configure-naming-components-table th {
  background: #f3f6fa;
  font-weight: 600;
}

.configure-naming-component-order {
  color: #888;
  font-size: 0.95em;
  margin-left: 8px;
}

.configure-naming-accordion-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.configure-naming-btn {
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 7px 18px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.18s;
}

.configure-naming-btn.delete {
  background: #e74c3c;
}

.configure-naming-btn.cancel {
  background: #9ca3af;
}

.configure-naming-btn.cancel:hover {
  background: #7b838a;
}

.configure-naming-btn:hover {
  background: #1565c0;
}

.configure-naming-add-form {
  overflow-wrap: break-word;
  margin-top: 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px #0002;
  padding: 32px 36px 28px;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  flex-direction: column;
}

.configure-naming-add-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2563eb;
  text-align: center;
  margin-bottom: 2rem;
  letter-spacing: 0.5px;
}

.configure-naming-add-fields {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.configure-naming-form-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.configure-naming-form-row label {
  width: 110px;
  font-weight: 500;
  color: #333;
  flex-shrink: 0;
}

.configure-naming-form-row input,
.configure-naming-form-row select {
  flex: 1;
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  font-size: 1rem;
  background: #f9fafb;
}

.configure-naming-pattern-row {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
}

.configure-naming-prefix-box {
  background: #f3f6fa;
  color: #2563eb;
  font-weight: 600;
  border: 1.5px solid #2563eb;
  border-radius: 5px;
  font-size: 1rem;
  max-width: fit-content;
  cursor: not-allowed;
  caret-color: transparent;
}

.configure-naming-pattern-sep {
  color: #888;
  font-size: 1.2em;
  font-weight: 700;
}

.configure-naming-pattern-box {
  flex: 2.5;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  padding: 7px 10px;
  font-size: 1rem;
  background: #fff;
}

.configure-naming-example-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.configure-naming-example-desc {
  color: #888;
  font-size: 0.98em;
  margin-bottom: 0.2rem;
  margin-left: 7.4rem;
}

.configure-naming-example-input {
  padding: 7px 10px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  font-size: 1rem;
  background: #fff;
  margin-bottom: 4px;
}

.configure-naming-error {
  color: #e74c3c;
  font-size: 0.98em;
  margin-top: 2px;
  margin-left: 8px;
}

.configure-naming-components-edit-table input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 1rem;
  background: #f9fafb;
  box-sizing: border-box;
}

.configure-naming-components-edit-table td {
  vertical-align: middle;
  padding: 6px 10px;
}

.configure-naming-components-edit-table th,
.configure-naming-components-edit-table td {
  border: 1px solid #e0e0e0;
}

.configure-naming-components-edit-table th {
  background: #f3f6fa;
  font-weight: 600;
  color: #2563eb;
}

.configure-naming-components-edit-table {
  margin-top: 8px;
  margin-bottom: 8px;
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 1px 4px #0001;
}

.configure-naming-components-label {
  font-weight: 600;
  color: #444;
  display: block;
  font-size: 1.08rem;
  margin-top: 1rem;
}

.configure-naming-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

.configure-naming-components-table-prefix-disabled {
  background: #f3f6fa !important;
  color: #aaa !important;
  cursor: not-allowed !important;
  pointer-events: auto !important;
}

.configure-naming-accepted-separators {
  margin-left: 2rem;
}

.import-modal-overlay {
  position: fixed;
  inset: 0;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.import-modal {
  background: #fff;
  border: 1px solid #d7e1f0;
  border-radius: 18px;
  padding: 104px 32px 82px;
  width: min(900px, 100%);
  height: min(760px, calc(100vh - 48px));
  max-width: none;
  max-height: none;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.import-modal-heading {
  position: absolute;
  z-index: 2;
  top: 0;
  right: 0;
  left: 0;
  display: flex;
  gap: 14px;
  align-items: center;
  min-height: 82px;
  padding: 18px 72px 18px 28px;
  background: linear-gradient(145deg, #fff, #f7faff);
  border-bottom: 1px solid #e2e8f2;
}

.import-modal-heading > div > span {
  color: #2864e8;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.import-modal-heading h2 {
  margin: 2px 0 0;
  color: #12213b;
  font-size: 1.2rem;
}

.import-modal-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  color: #2864e8;
  background: #e8f0ff;
  border-radius: 12px;
}

.import-modal-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 16px 28px;
  background: #f7f9fc;
  border-top: 1px solid #e2e8f2;
  display: flex;
  justify-content: flex-end;
  z-index: 2;
}

.import-modal-close {
  position: absolute;
  z-index: 3;
  top: 22px;
  right: 24px;
  width: 38px;
  height: 38px;
  color: #65748d;
  background: transparent;
  border: 0;
  border-radius: 9px;
  font-size: 1rem;
  cursor: pointer;
}

.import-modal-close:hover {
  color: #17243b;
  background: #eef3f9;
}

.import-project-select-row {
  display: flex;
  align-items: center;
  margin-bottom: 2em;
}

@media (width <= 640px) {
  .import-modal-overlay {
    align-items: end;
    padding: 12px;
  }

  .import-modal {
    height: calc(100vh - 24px);
    padding-right: 18px;
    padding-left: 18px;
    border-radius: 16px;
  }

  .import-project-select-row {
    align-items: stretch;
    flex-direction: column;
    gap: 10px;
  }

  .import-project-select-row .configure-naming-btn {
    margin-left: 0 !important;
  }
}

.import-project-select-control {
  flex: 1;
}

.import-standards-list {
  flex: 1 1 auto;
  overflow-y: auto;
  max-height: 55vh;
  margin-bottom: 1em;
}

.import-standard-preview {
  margin-bottom: 16px;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  background: #f9fafb;
  position: relative;
  transition: box-shadow 0.18s;
}

.import-standard-preview:hover {
  box-shadow: 0 2px 10px #0001;
}

.import-standard-header-col {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 4px;
  cursor: pointer;
  user-select: none;
}

.import-standard-header-row {
  display: flex;
  align-items: center;
  gap: 0.5em;
  width: 100%;
  min-height: 32px;
}

.import-standard-header-separator {
  border: none;
  border-top: 1.5px solid #e0e0e0;
  margin: 4px 0;
  width: 100%;
}

.import-standard-warning-row {
  display: flex;
  align-items: center;
  margin-top: 2px;
  margin-bottom: 2px;
  font-size: 0.98em;
  gap: 0.5em;
  background: #fffbe9;
  border-radius: 4px;
  padding: 4px 8px;
}

.import-standard-chevron {
  margin-left: auto;
  font-size: 1.2em;
  color: #888;
  transition: transform 0.2s;
  display: flex;
  align-items: center;
}

.import-standard-header-row:hover .import-standard-chevron {
  color: #2563eb;
}

.import-standard-details {
  margin: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.import-standard-greyed {
  filter: grayscale(0.7) brightness(1.08);
  pointer-events: none;
  user-select: none;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
