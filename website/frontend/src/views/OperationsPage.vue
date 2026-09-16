<template>
  <main class="operations-page">
    <WorkspaceHeader
      :title="t('operations.title')"
      :description="t('operations.description')"
      :context="t('operations.context')"
    />

    <section v-if="loading" class="operations-state" aria-live="polite">
      <font-awesome-icon icon="fa-solid fa-spinner" spin />
      {{ t('operations.loading') }}
    </section>
    <section v-else-if="loadError" class="operations-state error" role="alert">
      <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
      <div>
        <strong>{{ t('operations.loadError') }}</strong>
        <p>{{ loadError }}</p>
      </div>
    </section>

    <div v-else-if="status" class="operations-grid">
      <section class="operations-card">
        <div class="card-heading">
          <span class="card-icon"
            ><font-awesome-icon icon="fa-solid fa-database"
          /></span>
          <div>
            <p class="eyebrow">{{ t('operations.storage.context') }}</p>
            <h2>{{ t('operations.storage.title') }}</h2>
          </div>
          <span class="status-pill neutral">{{ storageBackend }}</span>
        </div>
        <dl class="facts">
          <div>
            <dt>{{ t('operations.storage.location') }}</dt>
            <dd>{{ storageLocation }}</dd>
          </div>
          <div>
            <dt>{{ t('operations.storage.credentials') }}</dt>
            <dd>{{ storageCredentials }}</dd>
          </div>
        </dl>
        <p class="guidance">{{ storagePolicy }}</p>
        <div class="card-action">
          <div aria-live="polite">
            <span v-if="storageCheck" class="status-pill healthy">
              <font-awesome-icon icon="fa-solid fa-circle-check" />
              {{ t('operations.storage.healthy') }}
            </span>
            <span v-else-if="storageError" class="status-pill unhealthy">
              <font-awesome-icon icon="fa-solid fa-triangle-exclamation" />
              {{ t('operations.storage.failed') }}
            </span>
          </div>
          <button
            type="button"
            class="secondary-action"
            :disabled="checkingStorage"
            @click="runStorageCheck"
          >
            <font-awesome-icon icon="fa-solid fa-shield-halved" />
            {{
              checkingStorage
                ? t('operations.storage.checking')
                : t('operations.storage.check')
            }}
          </button>
        </div>
      </section>

      <section class="operations-card">
        <div class="card-heading">
          <span class="card-icon"
            ><font-awesome-icon icon="fa-solid fa-heart-pulse"
          /></span>
          <div>
            <p class="eyebrow">{{ t('operations.integrity.context') }}</p>
            <h2>{{ t('operations.integrity.title') }}</h2>
          </div>
          <span
            :class="[
              'status-pill',
              integrityNeedsAttention ? 'unhealthy' : 'healthy',
            ]"
          >
            {{
              integrityNeedsAttention
                ? t('operations.integrity.attention')
                : t('operations.integrity.healthy')
            }}
          </span>
        </div>
        <div class="metrics">
          <div>
            <strong>{{ status.integrity.total_projects }}</strong
            ><span>{{ t('operations.integrity.total') }}</span>
          </div>
          <div>
            <strong>{{ status.integrity.healthy_projects }}</strong
            ><span>{{ t('operations.integrity.passing') }}</span>
          </div>
          <div>
            <strong>{{
              status.integrity.unhealthy_projects +
              status.integrity.unscanned_projects
            }}</strong
            ><span>{{ t('operations.integrity.attentionCount') }}</span>
          </div>
        </div>
        <p class="guidance">
          {{
            status.integrity.latest_check_at
              ? t('operations.integrity.lastChecked', {
                  date: formatDate(status.integrity.latest_check_at),
                })
              : t('operations.integrity.notChecked')
          }}
        </p>
      </section>

      <section class="operations-card wide">
        <div class="card-heading">
          <span class="card-icon"
            ><font-awesome-icon icon="fa-solid fa-code-merge"
          /></span>
          <div>
            <p class="eyebrow">{{ t('operations.publication.context') }}</p>
            <h2>{{ t('operations.publication.title') }}</h2>
          </div>
          <span
            :class="[
              'status-pill',
              publicationNeedsAttention ? 'warning' : 'healthy',
            ]"
          >
            {{
              publicationNeedsAttention
                ? t('operations.publication.attention')
                : t('operations.publication.healthy')
            }}
          </span>
        </div>
        <div class="metrics four">
          <div>
            <strong>{{ status.publication_queue.queued }}</strong
            ><span>{{ t('operations.publication.queued') }}</span>
          </div>
          <div>
            <strong>{{ status.publication_queue.running }}</strong
            ><span>{{ t('operations.publication.running') }}</span>
          </div>
          <div>
            <strong>{{ status.publication_queue.review_needed }}</strong
            ><span>{{ t('operations.publication.reviewNeeded') }}</span>
          </div>
          <div>
            <strong>{{ status.publication_queue.failed }}</strong
            ><span>{{ t('operations.publication.failed') }}</span>
          </div>
        </div>
        <p class="guidance">{{ t('operations.publication.explanation') }}</p>
      </section>

      <section class="operations-card wide">
        <div class="card-heading">
          <span class="card-icon"
            ><font-awesome-icon icon="fa-solid fa-envelope"
          /></span>
          <div>
            <p class="eyebrow">{{ t('operations.email.context') }}</p>
            <h2>{{ t('operations.email.title') }}</h2>
          </div>
          <span
            :class="[
              'status-pill',
              emailNeedsAttention ? 'warning' : 'healthy',
            ]"
          >
            {{
              emailNeedsAttention
                ? t('operations.email.attention')
                : t('operations.email.healthy')
            }}
          </span>
        </div>
        <div class="metrics">
          <div>
            <strong>{{ status.email_delivery.pending }}</strong
            ><span>{{ t('operations.email.pending') }}</span>
          </div>
          <div>
            <strong>{{ status.email_delivery.permanently_failed }}</strong
            ><span>{{ t('operations.email.permanentlyFailed') }}</span>
          </div>
          <div>
            <strong>{{ oldestPendingEmail }}</strong
            ><span>{{ t('operations.email.oldestPending') }}</span>
          </div>
        </div>
        <p class="guidance">
          {{
            t('operations.email.explanation', {
              days: status.email_delivery.retention_days,
            })
          }}
        </p>
      </section>

      <section class="operations-card wide">
        <div class="card-heading">
          <span class="card-icon"
            ><font-awesome-icon icon="fa-solid fa-clock-rotate-left"
          /></span>
          <div>
            <p class="eyebrow">{{ t('operations.recovery.context') }}</p>
            <h2>{{ t('operations.recovery.title') }}</h2>
          </div>
          <span :class="['status-pill', recoveryPill]">{{
            recoveryState
          }}</span>
        </div>
        <div class="recovery-copy">
          <p>{{ t('operations.recovery.explanation') }}</p>
          <p
            v-if="status.recovery.state === 'not_configured'"
            class="recovery-alert"
            role="alert"
          >
            {{ t('operations.recovery.notConfigured') }}
          </p>
          <dl class="facts">
            <div>
              <dt>{{ t('operations.recovery.lastBackup') }}</dt>
              <dd>{{ formatMoment(status.recovery.latest_backup_at) }}</dd>
            </div>
            <div>
              <dt>{{ t('operations.recovery.lastVerified') }}</dt>
              <dd>
                {{ formatMoment(status.recovery.latest_verified_backup_at) }}
              </dd>
            </div>
          </dl>
          <ul v-if="status.recovery.jobs.length" class="maintenance-jobs">
            <li v-for="job in status.recovery.jobs" :key="job.job">
              <span>{{ t(`operations.recovery.jobs.${job.job}`) }}</span>
              <span :class="['status-pill', jobPill(job.outcome)]">
                {{ t(`operations.recovery.outcomes.${job.outcome}`) }}
              </span>
              <small>{{ jobSummary(job) }}</small>
            </li>
          </ul>
          <p>
            {{ t('operations.recovery.command') }}
            <code>make test-recovery</code>
          </p>
        </div>
        <div class="boundary-note">
          <font-awesome-icon icon="fa-solid fa-lock" />
          <p>
            <strong>{{ t('operations.boundary.title') }}</strong
            ><br />{{ t('operations.boundary.body') }}
          </p>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import operationsService from '@/api/service/operationsService';

const { t, locale } = useI18n();
const status = ref(null);
const loading = ref(true);
const loadError = ref('');
const checkingStorage = ref(false);
const storageCheck = ref(null);
const storageError = ref('');
const storageBackend = computed(() =>
  status.value?.storage.backend.toUpperCase()
);
const storageLocation = computed(() =>
  status.value?.storage.location_hint === 'local_filesystem'
    ? t('operations.storage.localFilesystem')
    : status.value?.storage.location_hint
);
const storageCredentials = computed(() =>
  t(
    `operations.storage.credentialsValues.${status.value?.storage.credentials_source}`
  )
);
const storagePolicy = computed(() =>
  t(
    `operations.storage.policyValues.${status.value?.storage.policy_verification}`
  )
);
const recoveryState = computed(() =>
  t(`operations.recovery.states.${status.value?.recovery.state}`)
);
const RECOVERY_PILLS = {
  healthy: 'healthy',
  unverified: 'warning',
  not_yet_run: 'warning',
  not_configured: 'unhealthy',
  failing: 'unhealthy',
};
const recoveryPill = computed(
  () => RECOVERY_PILLS[status.value?.recovery.state] || 'warning'
);

function jobPill(outcome) {
  return { succeeded: 'healthy', failed: 'unhealthy' }[outcome] || 'warning';
}

function formatMoment(value) {
  return value ? formatDate(value) : t('operations.recovery.never');
}

// The detail a job records differs by job; show the part worth acting on.
function jobSummary(job) {
  const detail = job.detail || {};
  if (detail.reason) {
    return t(`operations.recovery.reasons.${detail.reason}`);
  }
  if (typeof detail.used_percent === 'number') {
    return t('operations.recovery.diskUsed', { percent: detail.used_percent });
  }
  if (typeof detail.projects_purged === 'number') {
    return t('operations.recovery.projectsPurged', {
      count: detail.projects_purged,
    });
  }
  return formatDate(job.started_at);
}
const integrityNeedsAttention = computed(
  () =>
    Boolean(status.value?.integrity.unhealthy_projects) ||
    Boolean(status.value?.integrity.unscanned_projects)
);
const publicationNeedsAttention = computed(
  () =>
    Boolean(status.value?.publication_queue.review_needed) ||
    Boolean(status.value?.publication_queue.failed)
);
// A message that was given up on never reached the person it was addressed to,
// so an administrator has to notice it and reissue the invitation or code.
const emailNeedsAttention = computed(() =>
  Boolean(status.value?.email_delivery?.permanently_failed)
);
const oldestPendingEmail = computed(() => {
  const queuedAt = status.value?.email_delivery?.oldest_pending_at;
  return queuedAt ? formatDate(queuedAt) : '—';
});

function formatDate(value) {
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

async function loadStatus() {
  try {
    status.value = await operationsService.getStatus();
  } catch (error) {
    loadError.value = apiErrorMessage(error, t, t('operations.loadError'));
  } finally {
    loading.value = false;
  }
}

async function runStorageCheck() {
  checkingStorage.value = true;
  storageCheck.value = null;
  storageError.value = '';
  try {
    storageCheck.value = await operationsService.checkStorage();
  } catch (error) {
    storageError.value = apiErrorMessage(
      error,
      t,
      t('operations.storage.failed')
    );
  } finally {
    checkingStorage.value = false;
  }
}

onMounted(loadStatus);
</script>

<style scoped>
.operations-page {
  width: min(80rem, calc(100% - 2rem));
  margin: 2rem auto;
  display: grid;
  gap: 1.5rem;
}

.operations-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

.operations-card,
.operations-state {
  background: #fff;
  border: 1px solid #dbe4f0;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 0.3rem 1rem rgb(15 23 42 / 5%);
}

.operations-card.wide {
  grid-column: 1 / -1;
}

.card-heading {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.9rem;
  align-items: center;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-heading h2 {
  margin: 0.15rem 0 0;
  color: #172033;
  font-size: 1.2rem;
}

.card-icon {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 0.75rem;
  background: #eaf1ff;
  color: #2563eb;
}

.eyebrow {
  margin: 0;
  color: #64748b;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border-radius: 999px;
  padding: 0.35rem 0.65rem;
  font-size: 0.78rem;
  font-weight: 700;
}

.status-pill.neutral {
  background: #edf4ff;
  color: #1d4ed8;
}

.status-pill.healthy {
  background: #e8f8ef;
  color: #16733b;
}

.status-pill.warning {
  background: #fff4d8;
  color: #8a5700;
}

.status-pill.unhealthy {
  background: #feecec;
  color: #b42318;
}

.facts {
  display: grid;
  gap: 0;
  margin: 1rem 0;
}

.facts div {
  display: grid;
  grid-template-columns: minmax(8rem, 0.7fr) minmax(0, 1.3fr);
  gap: 1rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #edf0f5;
}

.facts dt {
  color: #64748b;
  font-weight: 700;
}

.facts dd {
  margin: 0;
  color: #172033;
  overflow-wrap: anywhere;
}

.guidance {
  color: #5b6b85;
  line-height: 1.55;
}

.card-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 1rem;
}

.secondary-action {
  min-height: 2.75rem;
  border: 1px solid #9fc0ff;
  border-radius: 0.65rem;
  background: #fff;
  color: #174ea6;
  padding: 0.65rem 0.9rem;
  font-weight: 700;
  cursor: pointer;
}

.secondary-action:disabled {
  cursor: wait;
  opacity: 0.65;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  margin: 1rem 0;
}

.metrics.four {
  grid-template-columns: repeat(4, 1fr);
}

.metrics div {
  display: grid;
  gap: 0.2rem;
  padding: 0.85rem;
  background: #f7f9fc;
  border-radius: 0.7rem;
}

.metrics strong {
  color: #172033;
  font-size: 1.45rem;
}

.metrics span {
  color: #64748b;
  font-size: 0.82rem;
}

.recovery-copy {
  color: #40506a;
  line-height: 1.55;
}

.recovery-alert {
  border: 1px solid #fecaca;
  border-radius: 0.6rem;
  background: #fff1f2;
  padding: 0.7rem 0.9rem;
  color: #b91c1c;
  font-weight: 650;
}

.maintenance-jobs {
  display: grid;
  gap: 0.4rem;
  margin: 0.9rem 0;
  padding: 0;
  list-style: none;
}

.maintenance-jobs li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  border-top: 1px solid #e2e8f0;
  padding-top: 0.5rem;
  font-size: 0.88rem;
}

.maintenance-jobs small {
  color: #64748b;
}

code {
  border-radius: 0.35rem;
  background: #f1f5f9;
  padding: 0.18rem 0.4rem;
  color: #334155;
}

.boundary-note {
  display: flex;
  gap: 0.8rem;
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid #d9e5f7;
  border-radius: 0.75rem;
  background: #f7faff;
  color: #40506a;
}

.boundary-note p {
  margin: 0;
}

.operations-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  min-height: 10rem;
  color: #52627b;
}

.operations-state.error {
  color: #b42318;
}

.operations-state p {
  margin: 0.25rem 0 0;
}

@media (width <= 48rem) {
  .operations-page {
    width: min(100% - 1rem, 80rem);
    margin: 1rem auto;
  }

  .operations-grid {
    grid-template-columns: 1fr;
  }

  .operations-card.wide {
    grid-column: auto;
  }

  .card-heading {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .card-heading > .status-pill {
    grid-column: 1 / -1;
    width: fit-content;
  }

  .metrics,
  .metrics.four {
    grid-template-columns: repeat(2, 1fr);
  }

  .facts div {
    grid-template-columns: 1fr;
    gap: 0.25rem;
  }

  .card-action {
    align-items: stretch;
    flex-direction: column;
  }

  .secondary-action {
    width: 100%;
  }
}
</style>
