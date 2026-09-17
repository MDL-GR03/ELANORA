<template>
  <section class="governance" aria-labelledby="governance-classification">
    <p v-if="loading" class="state" role="status">
      {{ t('dataGovernance.loading') }}
    </p>
    <p v-else-if="loadError" class="state error" role="alert">
      {{ loadError }}
    </p>
    <form v-else novalidate @submit.prevent="save">
      <fieldset class="card">
        <legend id="governance-classification">
          {{ t('dataGovernance.classification.title') }}
        </legend>
        <p class="help">{{ t('dataGovernance.classification.help') }}</p>
        <div class="levels">
          <label
            v-for="level in LEVELS"
            :key="level"
            class="level"
            :class="{ selected: form.data_classification === level }"
          >
            <input
              v-model="form.data_classification"
              type="radio"
              name="data-classification"
              :value="level"
            />
            <span>
              <strong>{{
                t(`dataGovernance.classification.levels.${level}`)
              }}</strong>
              <small>{{
                t(`dataGovernance.classification.descriptions.${level}`)
              }}</small>
            </span>
          </label>
        </div>
        <p v-if="!form.data_classification" class="notice">
          {{ t('dataGovernance.classification.unclassified') }}
        </p>

        <label class="field">
          <span>{{ t('dataGovernance.legalBasis.label') }}</span>
          <textarea
            v-model="form.legal_basis"
            rows="2"
            maxlength="2000"
            :required="needsLegalBasis"
            :aria-invalid="legalBasisMissing || undefined"
            aria-describedby="governance-legal-basis-help"
          ></textarea>
          <small id="governance-legal-basis-help">
            {{
              needsLegalBasis
                ? t('dataGovernance.legalBasis.required')
                : t('dataGovernance.legalBasis.help')
            }}
          </small>
        </label>
      </fieldset>

      <fieldset class="card">
        <legend>{{ t('dataGovernance.retention.title') }}</legend>
        <p class="help">{{ t('dataGovernance.retention.help') }}</p>
        <label class="check">
          <input v-model="keepIndefinitely" type="checkbox" />
          {{ t('dataGovernance.retention.keepIndefinitely') }}
        </label>
        <label v-if="!keepIndefinitely" class="field short">
          <span>{{ t('dataGovernance.retention.days') }}</span>
          <input
            v-model.number="form.retention_days"
            type="number"
            :min="MIN_RETENTION_DAYS"
            max="36500"
            :aria-invalid="retentionTooShort || undefined"
            aria-describedby="governance-retention-minimum"
          />
          <small id="governance-retention-minimum">
            {{
              t('dataGovernance.retention.minimum', {
                days: MIN_RETENTION_DAYS,
              })
            }}
          </small>
        </label>
      </fieldset>

      <fieldset class="card">
        <legend>{{ t('dataGovernance.legalHold.title') }}</legend>
        <p class="help">{{ t('dataGovernance.legalHold.help') }}</p>
        <label class="check">
          <input v-model="form.legal_hold" type="checkbox" />
          {{ t('dataGovernance.legalHold.label') }}
        </label>
        <label v-if="form.legal_hold" class="field">
          <span>{{ t('dataGovernance.legalHold.reason') }}</span>
          <textarea
            v-model="form.legal_hold_reason"
            rows="2"
            maxlength="2000"
            required
            :aria-invalid="holdReasonMissing || undefined"
            aria-describedby="governance-hold-required"
          ></textarea>
          <small id="governance-hold-required">
            {{ t('dataGovernance.legalHold.required') }}
          </small>
        </label>
      </fieldset>

      <div class="actions">
        <small v-if="updatedAt">
          {{ t('dataGovernance.lastUpdated', { date: formatDate(updatedAt) }) }}
        </small>
        <button type="submit" :disabled="saving || !valid">
          {{ saving ? t('dataGovernance.saving') : t('dataGovernance.save') }}
        </button>
      </div>
      <p
        v-if="message"
        class="state"
        :class="{ error: saveFailed }"
        aria-live="polite"
      >
        {{ message }}
      </p>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import {
  getDataGovernance,
  saveDataGovernance,
} from '@/api/service/governanceService';

const LEVELS = ['public', 'internal', 'confidential', 'sensitive_personal'];
const MIN_RETENTION_DAYS = 30;

const { t, locale } = useI18n();
const route = useRoute();
const projectId = computed(() => Number(route.params.projectId));

const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const saveFailed = ref(false);
const message = ref('');
const updatedAt = ref(null);
const keepIndefinitely = ref(true);
const form = reactive({
  data_classification: null,
  legal_basis: '',
  retention_days: null,
  legal_hold: false,
  legal_hold_reason: '',
});

const needsLegalBasis = computed(
  () => form.data_classification === 'sensitive_personal'
);
const legalBasisMissing = computed(
  () => needsLegalBasis.value && !form.legal_basis?.trim()
);
const holdReasonMissing = computed(
  () => form.legal_hold && !form.legal_hold_reason?.trim()
);
const retentionTooShort = computed(
  () =>
    !keepIndefinitely.value &&
    !(
      Number.isInteger(form.retention_days) &&
      form.retention_days >= MIN_RETENTION_DAYS
    )
);
const valid = computed(
  () =>
    !legalBasisMissing.value &&
    !holdReasonMissing.value &&
    !retentionTooShort.value
);

watch(keepIndefinitely, (keep) => {
  if (!keep && form.retention_days == null) form.retention_days = 3650;
});

function apply(data) {
  form.data_classification = data.data_classification;
  form.legal_basis = data.legal_basis || '';
  form.retention_days = data.retention_days;
  form.legal_hold = data.legal_hold;
  form.legal_hold_reason = data.legal_hold_reason || '';
  keepIndefinitely.value = data.retention_days == null;
  updatedAt.value = data.updated_at;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const { data } = await getDataGovernance(projectId.value);
    apply(data);
  } catch {
    loadError.value = t('dataGovernance.loadFailed');
  } finally {
    loading.value = false;
  }
}

async function save() {
  if (!valid.value) return;
  saving.value = true;
  message.value = '';
  saveFailed.value = false;
  try {
    const { data } = await saveDataGovernance(projectId.value, {
      data_classification: form.data_classification,
      legal_basis: form.legal_basis.trim() || null,
      retention_days: keepIndefinitely.value ? null : form.retention_days,
      legal_hold: form.legal_hold,
      legal_hold_reason: form.legal_hold
        ? form.legal_hold_reason.trim() || null
        : null,
    });
    apply(data);
    message.value = t('dataGovernance.saved');
  } catch {
    saveFailed.value = true;
    message.value = t('dataGovernance.saveFailed');
  } finally {
    saving.value = false;
  }
}

watch(projectId, load);
onMounted(load);
</script>

<style scoped>
.governance form {
  display: grid;
  gap: 1rem;
}

.card {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 1rem;
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 0.85rem;
  background: var(--color-surface);
}

legend {
  padding: 0 0.25rem;
  color: var(--color-slate-900);
  font-size: 1rem;
  font-weight: 800;
}

.help,
small {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.84rem;
}

.levels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr));
  gap: 0.6rem;
}

.level {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.75rem;
  border: 1px solid var(--color-blue-100-alt);
  border-radius: 0.7rem;
  cursor: pointer;
}

.level.selected {
  border-color: var(--color-primary);
  background: var(--color-blue-50-subtle);
}

.level span {
  display: grid;
  gap: 0.2rem;
}

.notice {
  margin: 0;
  color: var(--color-amber-800-alt);
  font-size: 0.84rem;
  font-weight: 700;
}

.field {
  display: grid;
  gap: 0.3rem;
  color: var(--color-gray-700);
  font-size: 0.8rem;
  font-weight: 750;
}

.field.short {
  max-width: 16rem;
}

.field textarea,
.field input {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--color-gray-400);
  border-radius: 0.55rem;
  padding: 0.6rem 0.7rem;
  color: var(--color-slate-900);
  font: inherit;
  font-size: 0.9rem;
}

[aria-invalid='true'] {
  border-color: var(--color-error);
}

.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--color-slate-900);
  font-size: 0.9rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}

.actions button {
  min-height: 2.5rem;
  border: 0;
  border-radius: 0.6rem;
  padding: 0.6rem 1rem;
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.actions button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.state {
  margin: 0;
  padding: 0.75rem 1rem;
  border-radius: 0.65rem;
  background: var(--color-success-bg-subtle);
  color: var(--color-success);
}

.state.error {
  background: var(--color-error-bg-subtler);
  color: var(--color-error);
}
</style>
