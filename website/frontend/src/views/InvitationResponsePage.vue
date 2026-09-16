<template>
  <div class="invitation-response-page">
    <div class="container">
      <div class="response-card">
        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>{{ t('invitation.processing') }}</p>
        </div>

        <!-- Success State -->
        <div v-else-if="success" class="success-state">
          <div class="icon success-icon">✓</div>
          <h1>{{ successTitle }}</h1>
          <p>{{ successMessage }}</p>
          <router-link to="/projects" class="btn-primary">
            {{ t('invitation.go_to_projects') }}
          </router-link>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error-state">
          <div class="icon error-icon">✗</div>
          <h1>{{ t('invitation.error_title') }}</h1>
          <p>{{ errorMessage }}</p>
          <router-link to="/homePage" class="btn-secondary">
            {{ t('invitation.back_to_home') }}
          </router-link>
        </div>

        <!-- Default State (shouldn't appear) -->
        <div v-else class="loading-state">
          <p>{{ t('invitation.processing') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { reportClientError } from '@/utils/errorDiagnostics';
import {
  acceptInvitation,
  rejectInvitation,
} from '@/api/service/invitationService';

const route = useRoute();
const { t } = useI18n();

const loading = ref(true);
const success = ref(false);
const error = ref(false);
const errorMessage = ref('');
const action = ref('');

const successTitle = computed(() => {
  return action.value === 'accept'
    ? t('invitation.accept_success_title')
    : t('invitation.reject_success_title');
});

const successMessage = computed(() => {
  return action.value === 'accept'
    ? t('invitation.accept_success_message')
    : t('invitation.reject_success_message');
});

const processInvitation = async () => {
  try {
    const invitationId = route.params.invitationId;
    action.value = route.params.action;

    if (!invitationId || !['accept', 'reject'].includes(action.value)) {
      throw new Error('Invalid invitation parameters');
    }

    let response;
    if (action.value === 'accept') {
      response = await acceptInvitation(invitationId);
    } else {
      response = await rejectInvitation(invitationId);
    }

    if (response.data.success) {
      success.value = true;
    } else {
      throw new Error(response.data.message || 'Unknown error');
    }
  } catch (err) {
    reportClientError('Error processing invitation', err);
    error.value = true;
    errorMessage.value = apiErrorMessage(
      err,
      t,
      err.message || t('invitation.general_error')
    );
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  processInvitation();
});
</script>

<style src="@/assets/css/invitation-response-page.css"></style>
