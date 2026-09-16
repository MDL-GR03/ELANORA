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
  color: #64748b;
}

.standard-list {
  display: grid;
  gap: 18px;
}

.standard {
  overflow: hidden;
  background: #fff;
  border: 1px solid #dbe4f0;
  border-radius: 10px;
}

.standard-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 15px 18px;
  color: #17243b;
  text-align: left;
  background: #f1f5f9;
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
  color: #52627a;
  font-weight: 400;
}

.chevron {
  color: #64748b;
  transition: transform 0.2s;
}

.chevron.open {
  transform: rotate(180deg);
}

.standard-body {
  display: grid;
  padding: 18px 22px 22px;
  gap: 16px;
  background: #f8fafc;
}

.description {
  margin: 0;
  padding: 10px 14px;
  background: #eff6ff;
  border-left: 4px solid #3b82f6;
  border-radius: 6px;
}

.description strong {
  margin-right: 8px;
  color: #1d4ed8;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

h3,
caption {
  margin: 0 0 6px;
  color: #52627a;
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
  background: #e8eef7;
  border-radius: 6px;
}

.breakdown strong {
  color: #1d4ed8;
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 620px;
  border-collapse: collapse;
  background: #fff;
}

caption {
  padding-bottom: 6px;
}

th,
td {
  padding: 7px 10px;
  text-align: left;
  overflow-wrap: anywhere;
  border: 1px solid #dbe4f0;
}

th {
  background: #f1f5f9;
}

.delete {
  justify-self: start;
  min-height: 40px;
  padding: 8px 14px;
  color: #b42318;
  background: #fff;
  border: 1px solid #fda29b;
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
