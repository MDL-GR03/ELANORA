<template>
  <p v-if="standards.length === 0" class="empty-state">
    {{ t('configureNamingStandards.empty') }}
  </p>
  <div v-else class="standard-list">
    <article v-for="standard in standards" :key="standard.id" class="standard">
      <button
        type="button"
        class="standard-heading"
        :aria-expanded="openStandardId === standard.id"
        @click="$emit('toggle', standard.id)"
      >
        <span>
          <strong>{{ standard.name }}</strong>
          <small v-if="getFileTypeDisplay(standard.project_file_type_id)">
            {{ getFileTypeDisplay(standard.project_file_type_id) }}
          </small>
        </span>
        <font-awesome-icon
          class="chevron"
          :class="{ open: openStandardId === standard.id }"
          icon="fa-solid fa-chevron-down"
        />
      </button>
      <div v-if="openStandardId === standard.id" class="standard-body">
        <p v-if="standard.description" class="description">
          <strong>{{ t('configureNamingStandards.description') }}</strong>
          {{ standard.description }}
        </p>
        <div class="summary-grid">
          <section>
            <h3>{{ t('configureNamingStandards.exampleFile') }}</h3>
            <code>{{ buildExampleFilename(standard) }}</code>
          </section>
          <section>
            <h3>{{ t('configureNamingStandards.pattern') }}</h3>
            <code>{{ standard.pattern }}</code>
          </section>
        </div>
        <div
          class="breakdown"
          :aria-label="t('configureNamingStandards.componentExamples')"
        >
          <span
            v-for="component in getPatternOrderedComponents(standard)"
            :key="component.id || component.name"
          >
            <strong>{{ component.name }}</strong>
            <font-awesome-icon icon="fa-solid fa-arrow-right" />
            {{ getExampleValuesForStandard(standard)[component.name] }}
          </span>
        </div>
        <div class="table-wrap">
          <table>
            <caption>
              {{
                t('configureNamingStandards.componentsTable')
              }}
            </caption>
            <thead>
              <tr>
                <th>{{ t('configureNamingStandards.componentName') }}</th>
                <th>{{ t('configureNamingStandards.componentRegex') }}</th>
                <th>{{ t('configureNamingStandards.exampleFile') }}</th>
                <th>
                  {{ t('configureNamingStandards.componentAcceptedValues') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="component in getPatternOrderedComponents(standard)"
                :key="component.id || component.name"
              >
                <td>{{ component.name }}</td>
                <td>
                  <code>{{ component.regex }}</code>
                </td>
                <td>
                  {{ getExampleValuesForStandard(standard)[component.name] }}
                </td>
                <td>{{ acceptedValues(component) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button
          type="button"
          class="delete"
          @click="$emit('delete', standard.id)"
        >
          <font-awesome-icon icon="fa-solid fa-trash" />
          {{ t('configureNamingStandards.delete') }}
        </button>
      </div>
    </article>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n';

defineProps({
  standards: { type: Array, default: () => [] },
  openStandardId: { type: [Number, String], default: null },
  getFileTypeDisplay: { type: Function, required: true },
  buildExampleFilename: { type: Function, required: true },
  getPatternOrderedComponents: { type: Function, required: true },
  getExampleValuesForStandard: { type: Function, required: true },
});
defineEmits(['toggle', 'delete']);
const { t } = useI18n();

function acceptedValues(component) {
  return (component.accepted_values || [])
    .map((value) =>
      typeof value === 'object' && value !== null && 'value' in value
        ? value.value
        : value
    )
    .join(', ');
}
</script>

<style scoped>
.empty-state {
  color: var(--color-text-muted);
}

.standard-list {
  display: grid;
  gap: 18px;
}

.standard {
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 10px;
}

.standard-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 15px 18px;
  color: var(--color-slate-700);
  text-align: left;
  background: var(--color-gray-200);
  border: 0;
  cursor: pointer;
}

.standard-heading > span {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 12px;
}

.standard-heading small {
  color: var(--color-slate-600);
  font-weight: 400;
}

.chevron {
  color: var(--color-text-muted);
  transition: transform 0.2s;
}

.chevron.open {
  transform: rotate(180deg);
}

.standard-body {
  display: grid;
  padding: 18px 22px 22px;
  gap: 16px;
  background: var(--color-surface-subtle);
}

.description {
  margin: 0;
  padding: 10px 14px;
  background: var(--color-blue-100);
  border-left: 4px solid var(--color-blue-500);
  border-radius: 6px;
}

.description strong {
  margin-right: 8px;
  color: var(--color-blue-700);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

h3,
caption {
  margin: 0 0 6px;
  color: var(--color-slate-600);
  font-size: 0.78rem;
  font-weight: 700;
  text-align: left;
  text-transform: uppercase;
}

code {
  overflow-wrap: anywhere;
}

.breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.breakdown span {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  gap: 7px;
  background: var(--color-blue-50);
  border-radius: 6px;
}

.breakdown strong {
  color: var(--color-blue-700);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  background: var(--color-surface);
}

caption {
  padding-bottom: 6px;
}

th,
td {
  padding: 7px 10px;
  text-align: left;
  overflow-wrap: anywhere;
  border: 1px solid var(--color-blue-100-alt);
}

th {
  background: var(--color-gray-200);
}

.delete {
  justify-self: start;
  min-height: 40px;
  padding: 8px 14px;
  color: var(--color-error-medium);
  background: var(--color-surface);
  border: 1px solid var(--color-red-200);
  border-radius: 7px;
  cursor: pointer;
}

@media (width <= 640px) {
  .standard-body {
    padding: 14px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .standard-heading {
    min-height: 48px;
  }
}
</style>
