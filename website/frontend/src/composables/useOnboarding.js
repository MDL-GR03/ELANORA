/**
 * Composable for managing onboarding workflow state.
 * 
 * This composable provides methods for:
 * - Loading onboarding status
 * - Starting the onboarding workflow
 * - Marking steps as complete
 * - Skipping the onboarding
 * - Tracking progress through the workflow
 */

import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { useApi } from '@api';

/**
 * Onboarding step identifiers.
 */
export const ONBOARDING_STEPS = [
  { id: 'project_created', order: 1 },
  { id: 'protocol_configured', order: 2 },
  { id: 'collaborator_invited', order: 3 },
  { id: 'first_upload', order: 4 },
];

/**
 * Main composable for onboarding workflow.
 */
export function useOnboarding() {
  const { t } = useI18n();
  const router = useRouter();
  const api = useApi();

  // Reactive state
  const onboardingStatus = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  // Computed properties
  const currentStep = computed(() => onboardingStatus.value?.current_step || 'not_started');
  const isComplete = computed(() => onboardingStatus.value?.is_complete || false);
  const isSkipped = computed(() => onboardingStatus.value?.is_skipped || false);
  
  const projectCreated = computed(() => onboardingStatus.value?.project_created || false);
  const protocolConfigured = computed(() => onboardingStatus.value?.protocol_configured || false);
  const collaboratorInvited = computed(() => onboardingStatus.value?.collaborator_invited || false);
  const firstUpload = computed(() => onboardingStatus.value?.first_upload || false);

  const stepsCompleted = computed(() => {
    return [
      projectCreated.value,
      protocolConfigured.value,
      collaboratorInvited.value,
      firstUpload.value,
    ].filter(Boolean).length;
  });

  const totalSteps = computed(() => ONBOARDING_STEPS.length);

  const completionPercentage = computed(() => {
    return (stepsCompleted.value / totalSteps.value) * 100;
  });

  const nextStep = computed(() => {
    if (!projectCreated.value) return 'project_created';
    if (!protocolConfigured.value) return 'protocol_configured';
    if (!collaboratorInvited.value) return 'collaborator_invited';
    if (!firstUpload.value) return 'first_upload';
    return null;
  });

  // Step definitions with i18n
  const steps = computed(() => [
    {
      id: 'project_created',
      order: 1,
      title: t('onboarding.steps.project.title'),
      description: t('onboarding.steps.project.description'),
      completed: projectCreated.value,
    },
    {
      id: 'protocol_configured',
      order: 2,
      title: t('onboarding.steps.protocol.title'),
      description: t('onboarding.steps.protocol.description'),
      completed: protocolConfigured.value,
    },
    {
      id: 'collaborator_invited',
      order: 3,
      title: t('onboarding.steps.collaborator.title'),
      description: t('onboarding.steps.collaborator.description'),
      completed: collaboratorInvited.value,
    },
    {
      id: 'first_upload',
      order: 4,
      title: t('onboarding.steps.upload.title'),
      description: t('onboarding.steps.upload.description'),
      completed: firstUpload.value,
    },
  ]);

  // Methods
  /**
   * Load the current onboarding status from the API.
   */
  const loadOnboardingStatus = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.get('/api/v1/onboarding/status');
      onboardingStatus.value = response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to load onboarding status:', err);
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Start the onboarding workflow.
   */
  const startOnboarding = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.post('/api/v1/onboarding/start');
      onboardingStatus.value = {
        ...response.data,
        current_step: response.data.current_step,
      };
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to start onboarding:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Mark a specific step as complete.
   */
  const markStepComplete = async (step) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.post('/api/v1/onboarding/step/complete', { step });
      onboardingStatus.value = {
        ...onboardingStatus.value,
        current_step: response.data.current_step,
        [step]: true,
      };
      return response.data;
    } catch (err) {
      error.value = err;
      console.error(`Failed to mark step ${step} as complete:`, err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Skip the onboarding workflow entirely.
   */
  const skipOnboarding = async () => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.post('/api/v1/onboarding/skip');
      onboardingStatus.value = {
        ...onboardingStatus.value,
        current_step: 'skipped',
      };
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to skip onboarding:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Update individual step flags.
   */
  const updateStepFlags = async (flags) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const response = await api.patch('/api/v1/onboarding/status', flags);
      onboardingStatus.value = response.data;
      return response.data;
    } catch (err) {
      error.value = err;
      console.error('Failed to update step flags:', err);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  /**
   * Check if a specific step should be blocked (not yet available).
   */
  const isStepBlocked = (stepId) => {
    const stepIndex = ONBOARDING_STEPS.findIndex(s => s.id === stepId);
    const currentIndex = ONBOARDING_STEPS.findIndex(s => s.id === nextStep.value) || 0;
    return stepIndex > currentIndex;
  };

  /**
   * Get the next step to navigate to.
   */
  const getNextStepRoute = () => {
    const step = nextStep.value;
    switch (step) {
      case 'project_created':
        return { name: 'ProjectsPage' };
      case 'protocol_configured':
        return { name: 'ProjectConfigurationPage' };
      case 'collaborator_invited':
        return { name: 'AdminInvitationsPage' };
      case 'first_upload':
        return { name: 'UploadPage' };
      default:
        return { name: 'HomePage' };
    }
  };

  return {
    // State
    onboardingStatus,
    isLoading,
    error,
    
    // Computed
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
    
    // Methods
    loadOnboardingStatus,
    startOnboarding,
    markStepComplete,
    skipOnboarding,
    updateStepFlags,
    isStepBlocked,
    getNextStepRoute,
  };
}
