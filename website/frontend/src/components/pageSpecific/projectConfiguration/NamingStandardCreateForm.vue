<template>
  <div ref="formRef" class="configure-naming-add-form">
    <div class="configure-naming-add-title">
      {{ t('configureNamingStandards.add') }}
    </div>
    <form class="configure-naming-add-fields" @submit.prevent="emit('submit')">
      <div class="configure-naming-form-row">
        <label for="standard-name">{{
          t('configureNamingStandards.name')
        }}</label>
        <input
          id="standard-name"
          v-model="draft.name"
          :placeholder="t('configureNamingStandards.name')"
          required
        />
      </div>
      <div class="configure-naming-form-row">
        <label for="standard-desc">{{
          t('configureNamingStandards.description')
        }}</label>
        <input
          id="standard-desc"
          v-model="draft.description"
          :placeholder="t('configureNamingStandards.description')"
        />
      </div>
      <div class="configure-naming-form-row">
        <label for="standard-filetype">{{
          t('configureNamingStandards.fileType')
        }}</label>
        <AppSelect
          id="standard-filetype"
          v-model="draft.project_file_type_id"
          :required="true"
          :placeholder="t('configureNamingStandards.fileType')"
          :options="fileTypeOptions"
          @change="emit('file-type-change')"
        />
      </div>
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
            @input="emit('pattern-input')"
          />
        </div>
      </div>

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
            >:
            {{
              knownSeparators.map((separator) => `"${separator}"`).join(', ')
            }}
          </span>
        </div>
        <div class="configure-naming-example-desc">
          <code>{{ exampleCommaPattern }}</code>
        </div>
      </div>

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
            @click="emit('extract-regex')"
          >
            {{ t('configureNamingStandards.extractRegex') }}
          </button>
        </div>
      </div>

      <div class="configure-naming-components-section">
        <label class="configure-naming-components-label" for="components-table">
          {{ t('configureNamingStandards.componentsTable') }}
        </label>
        <table
          id="components-table"
          class="configure-naming-components-table configure-naming-components-edit-table"
        >
          <thead>
            <tr>
              <th>{{ t('configureNamingStandards.componentName') }}</th>
              <th>{{ t('configureNamingStandards.componentRegex') }}</th>
              <th>{{ t('configureNamingStandards.componentDescription') }}</th>
              <th>
                {{ t('configureNamingStandards.componentAcceptedValues') }}
              </th>
              <th>{{ t('configureNamingStandards.componentOrder') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(component, index) in draft.components"
              :key="component.name"
              class="configure-naming-component-row"
            >
              <td>
                <input
                  v-model="component.name"
                  :placeholder="t('configureNamingStandards.componentName')"
                  readonly
                  class="configure-naming-components-table-prefix-disabled"
                  :tabindex="isPrefix(component, index) ? -1 : 0"
                />
              </td>
              <td>
                <input
                  v-model="component.regex"
                  :placeholder="t('configureNamingStandards.regex')"
                  :readonly="isPrefix(component, index)"
                  :class="{
                    'configure-naming-components-table-prefix-disabled':
                      isPrefix(component, index),
                  }"
                  :tabindex="isPrefix(component, index) ? -1 : 0"
                />
              </td>
              <td>
                <input
                  v-model="component.description"
                  :placeholder="t('configureNamingStandards.description')"
                />
              </td>
              <td>
                <input
                  v-model="component.accepted_values_str"
                  :placeholder="getAcceptedValuesPlaceholder(component)"
                  :title="getAcceptedValuesPlaceholder(component)"
                  @input="emit('accepted-values-input', component)"
                />
              </td>
              <td>
                <span class="configure-naming-component-order"
                  >#{{ component.order }}</span
                >
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="showAcceptedValuesWarning" class="configure-naming-warning">
          <b>{{
            t('configureNamingStandards.noteAcceptedValues', {
              value: unusualAcceptedValue,
            })
          }}</b>
        </div>
        <div
          v-if="extractionError"
          ref="errorRef"
          class="configure-naming-error"
        >
          {{ extractionError }}
        </div>
      </div>
      <div class="configure-naming-form-actions">
        <button
          class="configure-naming-btn"
          type="submit"
          :disabled="!!extractionError"
        >
          {{ t('configureNamingStandards.add') }}
        </button>
        <button
          class="configure-naming-btn cancel"
          type="button"
          @click="emit('cancel')"
        >
          {{ t('configureNamingStandards.cancel') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import AppSelect from '@/components/common/AppSelect.vue';

defineProps({
  fileTypeOptions: { type: Array, required: true },
  prefixValue: { type: String, default: '' },
  knownSeparators: { type: Array, required: true },
  exampleCommaPattern: { type: String, required: true },
  extractionError: { type: String, default: '' },
  showAcceptedValuesWarning: { type: Boolean, default: false },
  unusualAcceptedValue: { type: String, default: '' },
  getAcceptedValuesPlaceholder: { type: Function, required: true },
});

const emit = defineEmits([
  'submit',
  'cancel',
  'file-type-change',
  'pattern-input',
  'extract-regex',
  'accepted-values-input',
]);
const draft = defineModel('draft', { type: Object, required: true });
const commaPattern = defineModel('commaPattern', {
  type: String,
  required: true,
});
const exampleFilename = defineModel('exampleFilename', {
  type: String,
  required: true,
});
const { t } = useI18n();
const formRef = ref(null);
const errorRef = ref(null);

const isPrefix = (component, index) =>
  index === 0 && component.name.startsWith('prefix_');

onMounted(() => {
  formRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' });
});

watch(
  () => draft.value,
  () => {},
  { deep: true }
);

watch(
  () => errorRef.value,
  async (errorElement) => {
    if (!errorElement) return;
    await nextTick();
    errorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
);
</script>

<style scoped>
.configure-naming-add-form {
  overflow-wrap: break-word;
  margin: 32px auto 0;
  background: var(--color-surface);
  border-radius: 12px;
  box-shadow: 0 2px 12px rgb(0 0 0 / 2%);
  padding: 32px 36px 28px;
  display: flex;
  flex-direction: column;
}

.configure-naming-add-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-primary);
  text-align: center;
  margin-bottom: 2rem;
  letter-spacing: 0.5px;
}

.configure-naming-add-fields,
.configure-naming-example-block {
  display: flex;
  flex-direction: column;
}

.configure-naming-add-fields {
  gap: 18px;
}

.configure-naming-example-block {
  gap: 6px;
  width: 100%;
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
  color: var(--color-slate-900-alt);
  flex-shrink: 0;
}

.configure-naming-form-row input {
  flex: 1;
  padding: 7px 10px;
  border: 1px solid var(--color-gray-300);
  border-radius: 5px;
  font-size: 1rem;
  background: var(--color-gray-100-alt);
}

.configure-naming-pattern-row {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
}

.configure-naming-prefix-box {
  background: var(--color-gray-200-alt);
  color: var(--color-primary);
  font-weight: 600;
  border: 1.5px solid var(--color-primary);
  max-width: fit-content;
  cursor: not-allowed;
  caret-color: transparent;
}

.configure-naming-pattern-sep {
  color: var(--color-slate-500-alt);
  font-size: 1.2em;
  font-weight: 700;
}

.configure-naming-pattern-box {
  flex: 2.5;
  background: var(--color-surface);
}

.configure-naming-example-desc {
  color: var(--color-slate-500-alt);
  font-size: 0.98em;
  margin: 0 0 0.2rem 7.4rem;
}

.configure-naming-accepted-separators {
  margin-left: 2rem;
}

.configure-naming-example-input {
  margin-bottom: 4px;
}

.configure-naming-error {
  color: var(--color-red-500);
  font-size: 0.98em;
  margin: 4px 0 0 8px;
}

.configure-naming-warning {
  margin-top: 4px;
}

.configure-naming-components-edit-table {
  margin: 8px 0;
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
  background: var(--color-surface);
  box-shadow: 0 1px 4px rgb(0 0 0 / 1%);
}

.configure-naming-components-edit-table input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--color-gray-300);
  border-radius: 4px;
  font-size: 1rem;
  background: var(--color-gray-100-alt);
  box-sizing: border-box;
}

.configure-naming-components-edit-table th,
.configure-naming-components-edit-table td {
  border: 1px solid var(--color-gray-50-alt);
}

.configure-naming-components-edit-table td {
  vertical-align: middle;
  padding: 6px 10px;
}

.configure-naming-components-edit-table th {
  background: var(--color-gray-200-alt);
  font-weight: 600;
  color: var(--color-primary);
}

.configure-naming-components-label {
  font-weight: 600;
  color: var(--color-slate-800-alt);
  display: block;
  font-size: 1.08rem;
  margin-top: 1rem;
}

.configure-naming-components-table-prefix-disabled {
  background: var(--color-gray-200-alt) !important;
  color: var(--color-slate-400-alt) !important;
  cursor: not-allowed !important;
  pointer-events: auto !important;
}

.configure-naming-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
}

@media (width <= 700px) {
  .configure-naming-add-form {
    padding: 24px 16px;
  }

  .configure-naming-form-row {
    align-items: stretch;
    flex-direction: column;
  }

  .configure-naming-form-row label {
    width: auto;
  }

  .configure-naming-example-desc {
    margin-left: 0;
  }

  .configure-naming-accepted-separators {
    display: block;
    margin: 0.5rem 0 0;
  }

  .configure-naming-components-section {
    overflow-x: auto;
  }
}
</style>
