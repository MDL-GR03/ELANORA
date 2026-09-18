<template>
  <div class="onboarding-wizard" role="region" aria-label="Onboarding Wizard">
    <!-- Progress Header -->
    <header class="wizard-header">
      <h2 class="wizard-title">
        {{ t('onboarding.title') }}
      </h2>
      <p class="wizard-description">
        {{ t('onboarding.description') }}
      </p>
      
      <!-- Progress Bar -->
      <div class="progress-container">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: `${completionPercentage}%` }"
            role="progressbar"
            :aria-valuenow="completionPercentage"
            aria-valuemin="0"
            aria-valuemax="100"
          ></div>
        </div>
        <span class="progress-text">
          {{ stepsCompleted }}/{{ totalSteps }} {{ t('onboarding.stepsComplete') }}
        </span>
      </div>
    </header>

    <!-- Steps List -->
    <div class="steps-container">
      <div 
        v-for="step in steps" 
        :key="step.id" 
        class="step-item" 
        :class="{
          'completed': step.completed,
          'current': step.id === nextStep,
          'blocked': isStepBlocked(step.id),
        }"
        role="listitem"
        :aria-current="step.id === nextStep ? 'step' : undefined"
      >
        <div class="step-icon-container">
          <span class="step-number">{{ step.order }}</span>
          <span 
            class="step-icon" 
            :class="step.completed ? 'completed' : ''"
          >
            <font-awesome-icon 
              v-if="step.completed" 
              icon="fa-solid fa-circle-check" 
            />
            <font-awesome-icon 
              v-else-if="step.id === nextStep" 
              icon="fa-solid fa-circle-pause" 
            />
            <font-awesome-icon 
              v-else 
              icon="fa-regular fa-circle" 
            />
          </span>
        </div>
        
        <div class="step-content">
          <h3 class="step-title">{{ step.title }}</h3>
          <p class="step-description">{{ step.description }}</p>
        </div>

        <!-- Action Button -->
        <div class="step-actions" v-if="step.id === nextStep">
          <button 
            class="step-button" 
            @click="handleStepAction(step.id)"
            :disabled="isLoading"
          >
            <font-awesome-icon icon="fa-solid fa-arrow-right" />
            {{ t('onboarding.continue') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Action Footer -->
    <footer class="wizard-footer">
      <button 
        class="skip-button" 
        @click="handleSkip"
        :disabled="isLoading || isComplete"
      >
        {{ t('onboarding.skip') }}
      </button>
      
      <button 
        v-if="isComplete" 
        class="complete-button" 
        @click="handleComplete"
        :disabled="isLoading"
      >
        <font-awesome-icon icon="fa-solid fa-check" />
        {{ t('onboarding.complete') }}
      </button>
    </footer>
  </div>
</template>

<script>
/**
 * OnboardingWizard component for guided first-time setup.
 * 
 * This component displays the onboarding progress and provides
 * a step-by-step guide through the initial setup process.
 */

import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { useOnboarding } from '@/composables/useOnboarding';

import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';

export default {
  name: 'OnboardingWizard',
  components: {
    FontAwesomeIcon,
  },
  setup() {
    const { t } = useI18n();
    const router = useRouter();
    
    const {
      onboardingStatus,
      isLoading,
      error,
      currentStep,
      isComplete,
      isSkipped,
      projectCreated,
      protocolConfigured,
      collaboratorInvited,
      firstUpload,
      stepsCompleted,
      totalSteps,
      completionPercentage,
      nextStep,
      steps,
      loadOnboardingStatus,
      startOnboarding,
      markStepComplete,
      skipOnboarding,
      updateStepFlags,
      isStepBlocked,
      getNextStepRoute,
    } = useOnboarding();

    // Methods
    const handleStepAction = async (stepId) => {
      try {
        // Mark the current step as complete
        await markStepComplete(stepId);
        
        // Reload status to get updated state
        await loadOnboardingStatus();
        
        // If this step is complete, navigate to the appropriate page
        if (stepId === 'project_created') {
          router.push({ name: 'ProjectsPage' });
        } else if (stepId === 'protocol_configured') {
          router.push({ name: 'ProjectConfigurationPage' });
        } else if (stepId === 'collaborator_invited') {
          router.push({ name: 'AdminInvitationsPage' });
        } else if (stepId === 'first_upload') {
          router.push({ name: 'UploadPage' });
        }
      } catch (err) {
        console.error('Failed to complete step:', err);
      }
    };

    const handleSkip = async () => {
      try {
        await skipOnboarding();
        await loadOnboardingStatus();
      } catch (err) {
        console.error('Failed to skip onboarding:', err);
      }
    };

    const handleComplete = () => {
      // Onboarding is already complete, just navigate home
      router.push({ name: 'HomePage' });
    };

    // Load onboarding status on mount
    onMounted(() => {
      loadOnboardingStatus();
    });

    return {
      t,
      onboardingStatus,
      isLoading,
      error,
      currentStep,
      isComplete,
      isSkipped,
      projectCreated,
      protocolConfigured,
      collaboratorInvited,
      firstUpload,
      stepsCompleted,
      totalSteps,
      completionPercentage,
      nextStep,
      steps,
      isStepBlocked,
      handleStepAction,
      handleSkip,
      handleComplete,
    };
  },
};
</script>

<style scoped>
.onboarding-wizard {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid var(--color-border);
}

.wizard-header {
  margin-bottom: 1.5rem;
}

.wizard-title {
  color: var(--color-text);
  font-size: var(--font-size-xl);
  font-weight: 700;
  margin: 0 0 0.5rem;
}

.wizard-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-base);
  margin: 0 0 1rem;
  line-height: 1.5;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  flex: 1;
  height: 0.5rem;
  background: var(--color-border-subtle);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  white-space: nowrap;
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: var(--color-surface-subtle);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
  role: listitem;
}

.step-item.completed {
  border-color: var(--color-success);
  background: color-mix(in srgb, var(--color-success-bg) 50%, var(--color-surface-subtle));
}

.step-item.current {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary-bg) 50%, var(--color-surface-subtle));
}

.step-item.blocked {
  opacity: 0.6;
  cursor: not-allowed;
}

.step-icon-container {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.step-number {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 700;
}

.step-item.completed .step-number {
  background: var(--color-success);
  color: white;
}

.step-item.current .step-number {
  background: var(--color-primary);
  color: white;
}

.step-icon {
  color: var(--color-text-muted);
}

.step-item.completed .step-icon {
  color: var(--color-success);
}

.step-item.current .step-icon {
  color: var(--color-primary);
}

.step-content {
  flex: 1;
}

.step-title {
  color: var(--color-text);
  font-size: var(--font-size-base);
  font-weight: 600;
  margin: 0 0 0.25rem;
}

.step-description {
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  margin: 0;
  line-height: 1.4;
}

.step-actions {
  flex-shrink: 0;
}

.step-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.1s ease;
}

.step-button:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
}

.step-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.wizard-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border-subtle);
}

.skip-button {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.skip-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: var(--color-primary-bg);
}

.skip-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.complete-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--color-success);
  color: white;
  font-size: var(--font-size-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.1s ease;
}

.complete-button:hover:not(:disabled) {
  background: var(--color-success-dark);
  transform: translateY(-1px);
}

.complete-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}
</style>
