<template>
  <section class="guide-panel" aria-labelledby="first-upload-heading">
    <div class="guide-header">
      <div class="guide-icon">
        <font-awesome-icon icon="fa-solid fa-file-import" />
      </div>
      <div class="guide-title-wrap">
        <h2 id="first-upload-heading">{{ t('onboarding.steps.upload.title') }}</h2>
        <p class="guide-subtitle">{{ t('onboarding.steps.upload.description') }}</p>
      </div>
    </div>

    <div class="guide-content">
      <!-- Step Indicator -->
      <div class="step-indicator">
        <span class="step-badge">
          <font-awesome-icon icon="fa-solid fa-4" />
          {{ t('onboarding.stepOf', { step: 4, total: 4 }) }}
        </span>
      </div>

      <!-- Instructions -->
      <div class="guide-instructions">
        <h3>{{ t('onboarding.upload.instructionsTitle') }}</h3>
        <ol class="instructions-list">
          <li>{{ t('onboarding.upload.step1') }}</li>
          <li>{{ t('onboarding.upload.step2') }}</li>
          <li>{{ t('onboarding.upload.step3') }}</li>
          <li>{{ t('onboarding.upload.step4') }}</li>
        </ol>
      </div>

      <!-- Requirements Checklist -->
      <div class="requirements-checklist">
        <h4>{{ t('onboarding.upload.requirementsTitle') }}</h4>
        <ul class="checklist">
          <li class="checklist-item">
            <font-awesome-icon icon="fa-solid fa-check-circle" />
            {{ t('onboarding.upload.requirement1') }}
          </li>
          <li class="checklist-item">
            <font-awesome-icon icon="fa-solid fa-check-circle" />
            {{ t('onboarding.upload.requirement2') }}
          </li>
          <li class="checklist-item">
            <font-awesome-icon icon="fa-solid fa-check-circle" />
            {{ t('onboarding.upload.requirement3') }}
          </li>
        </ul>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <button
          type="button"
          class="btn btn-primary"
          @click="navigateToUpload"
        >
          <font-awesome-icon icon="fa-solid fa-upload" />
          {{ t('onboarding.upload.uploadFiles') }}
        </button>
        
        <button
          type="button"
          class="btn btn-text learn-more"
          @click="showHelp = !showHelp"
        >
          {{ t('common.learnMore') }}
          <font-awesome-icon :icon="showHelp ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" />
        </button>
      </div>

      <!-- Help Content -->
      <div v-if="showHelp" class="help-content" aria-label="Additional help">
        <h4>{{ t('onboarding.upload.helpTitle') }}</h4>
        <ul class="help-list">
          <li>
            <strong>{{ t('onboarding.upload.helpFileTypes') }}</strong>
            {{ t('onboarding.upload.helpFileTypesDesc') }}
          </li>
          <li>
            <strong>{{ t('onboarding.upload.helpValidation') }}</strong>
            {{ t('onboarding.upload.helpValidationDesc') }}
          </li>
          <li>
            <strong>{{ t('onboarding.upload.helpReview') }}</strong>
            {{ t('onboarding.upload.helpReviewDesc') }}
          </li>
          <li>
            <strong>{{ t('onboarding.upload.helpBatch') }}</strong>
            {{ t('onboarding.upload.helpBatchDesc') }}
          </li>
        </ul>
      </div>

      <!-- Status -->
      <div class="guide-status">
        <span class="status-label">{{ t('onboarding.status') }}:</span>
        <span class="status-value" :class="statusClass">
          <font-awesome-icon v-if="isLoading" icon="fa-solid fa-spinner" spin />
          <template v-else>
            <font-awesome-icon v-if="completed" icon="fa-solid fa-circle-check" />
            <font-awesome-icon v-else icon="fa-regular fa-circle" />
            {{ completed ? t('onboarding.completed') : t('onboarding.pending') }}
          </template>
        </span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useOnboarding } from '@/composables/useOnboarding';

const { t } = useI18n();
const router = useRouter();

const {
  firstUpload,
  isLoading,
  markStepComplete,
} = useOnboarding();

const showHelp = ref(false);

// Computed
const completed = computed(() => firstUpload.value);

const statusClass = computed(() => {
  if (completed.value) return 'status-complete';
  return 'status-pending';
});

// Methods
const navigateToUpload = () => {
  router.push({ name: 'UploadPage' });
};
</script>

<style scoped>
/* Use CSS variables from _variables.css */
.guide-panel {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 1rem);
  padding: var(--spacing-lg, 1.5rem);
  background: var(--color-surface, #fff);
  border: 1px solid var(--color-border, #dfe6ee);
  border-radius: var(--radius-lg, 1rem);
  box-shadow: 0 0.3rem 1rem rgb(15 23 42 / 5%);
}

.guide-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md, 1rem);
  margin-bottom: var(--spacing-md, 1rem);
  padding-bottom: var(--spacing-md, 1rem);
  border-bottom: 1px solid var(--color-border-subtle, #e5e7eb);
}

.guide-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--size-12, 3rem);
  height: var(--size-12, 3rem);
  border-radius: var(--radius-lg, 1rem);
  background: var(--color-accent-bg, #ffedd5);
  color: var(--color-accent, #d97706);
  font-size: var(--text-xl, 1.25rem);
}

.guide-title-wrap {
  flex: 1;
}

.guide-title-wrap h2 {
  margin: 0;
  color: var(--color-text, #172033);
  font-size: var(--text-xl, 1.25rem);
  font-weight: 700;
}

.guide-subtitle {
  margin: var(--spacing-xs, 0.25rem) 0 0;
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-base, 1rem);
  line-height: 1.5;
}

.guide-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg, 1.5rem);
}

.step-indicator {
  align-self: flex-start;
}

.step-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 0.375rem);
  padding: var(--spacing-xs, 0.25rem) var(--spacing-md, 1rem);
  border-radius: var(--radius-full, 999px);
  background: var(--color-accent-bg, #ffedd5);
  color: var(--color-accent-dark, #92400e);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.guide-instructions {
  padding: var(--spacing-md, 1rem);
  background: var(--color-surface-subtle, #f8fafc);
  border-radius: var(--radius-md, 0.75rem);
}

.guide-instructions h3 {
  margin: 0 0 var(--spacing-md, 1rem);
  color: var(--color-text, #172033);
  font-size: var(--text-lg, 1.125rem);
  font-weight: 600;
}

.instructions-list {
  margin: 0;
  padding: 0 0 0 var(--spacing-lg, 1.5rem);
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  line-height: 1.6;
}

.instructions-list li {
  margin-bottom: var(--spacing-sm, 0.5rem);
  padding-left: var(--spacing-md, 1rem);
}

.instructions-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: calc(var(--text-base, 1rem) / 2 - 0.25rem);
  width: 0.5rem;
  height: 0.5rem;
  border-radius: var(--radius-full, 999px);
  background: var(--color-accent, #d97706);
}

/* Requirements Checklist */
.requirements-checklist {
  padding: var(--spacing-md, 1rem);
  background: var(--color-surface, #fff);
  border-radius: var(--radius-md, 0.75rem);
  border: 1px solid var(--color-border-subtle, #e5e7eb);
}

.requirements-checklist h4 {
  margin: 0 0 var(--spacing-md, 1rem);
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  font-weight: 600;
}

.checklist {
  margin: 0;
  padding: 0;
  list-style: none;
}

.checklist-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
  padding: var(--spacing-sm, 0.5rem) 0;
  color: var(--color-text, #172033);
  font-size: var(--text-sm, 0.875rem);
  border-bottom: 1px solid var(--color-border-subtle, #e5e7eb);
}

.checklist-item:last-child {
  border-bottom: none;
}

.checklist-item svg {
  color: var(--color-success, #16a34a);
}

/* Quick Actions */
.quick-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
  flex-wrap: wrap;
}

.learn-more {
  color: var(--color-accent, #d97706);
}

.help-content {
  padding: var(--spacing-md, 1rem);
  background: var(--color-surface-subtle, #f8fafc);
  border-radius: var(--radius-md, 0.75rem);
  border: 1px solid var(--color-border-subtle, #e5e7eb);
}

.help-content h4 {
  margin: 0 0 var(--spacing-md, 1rem);
  color: var(--color-text, #172033);
  font-size: var(--text-base, 1rem);
  font-weight: 600;
}

.help-list {
  margin: 0;
  padding: 0 0 0 var(--spacing-md, 1rem);
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-sm, 0.875rem);
  line-height: 1.6;
}

.help-list li {
  margin-bottom: var(--spacing-sm, 0.5rem);
}

.help-list strong {
  color: var(--color-text, #172033);
}

.guide-status {
  display: flex;
  align-items: center;
  gap: var(--spacing-md, 1rem);
  align-self: flex-end;
  padding: var(--spacing-md, 1rem);
  background: var(--color-surface-subtle, #f8fafc);
  border-radius: var(--radius-md, 0.75rem);
}

.status-label {
  color: var(--color-text-muted, #64748b);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.status-value {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs, 0.375rem);
  padding: var(--spacing-xs, 0.25rem) var(--spacing-md, 1rem);
  border-radius: var(--radius-full, 999px);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
}

.status-value.status-complete {
  background: var(--color-success-bg, #dcfce7);
  color: var(--color-success-dark, #14532d);
}

.status-value.status-pending {
  background: var(--color-warning-bg, #fef3c7);
  color: var(--color-warning-dark, #7a4b00);
}

/* Responsive */
@media (width <= 48rem) {
  .guide-panel {
    width: 100%;
  }

  .guide-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .instructions-list {
    padding-left: var(--spacing-md, 1rem);
  }

  .instructions-list li::before {
    left: 0;
  }

  .quick-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .quick-actions .btn {
    width: 100%;
  }

  .guide-status {
    align-self: auto;
    width: 100%;
    justify-content: center;
  }
}
</style>
