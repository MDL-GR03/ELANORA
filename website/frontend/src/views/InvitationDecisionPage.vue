<template>
  <div class="invitation-decision-page">
    <div class="container">
      <div class="decision-card">
        <!-- Loading State -->
        <div v-if="loading" class="loading-state">
          <div class="spinner"></div>
          <p>{{ t('invitation.loading_invitation') }}</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="error-state">
          <div class="error-icon">✗</div>
          <h1>{{ t('invitation.error_title') }}</h1>
          <p>{{ errorMessage }}</p>
          <router-link to="/homePage" class="btn-secondary">
            {{ t('invitation.back_to_home') }}
          </router-link>
        </div>

        <!-- Decision State -->
        <div
          v-else-if="invitationData && !accepted && !rejected"
          class="decision-state"
        >
          <div class="invitation-header">
            <div class="invitation-icon">📨</div>
            <h1>{{ t('invitation.decision_title') }}</h1>
            <p class="invitation-subtitle">
              {{ t('invitation.review_invitation') }}
            </p>
          </div>

          <div class="invitation-details">
            <div class="invitation-info">
              <div class="invitation-card">
                <div class="sender-info">
                  <div class="sender-avatar">
                    {{ invitationData.sender_name.charAt(0).toUpperCase() }}
                  </div>
                  <div class="sender-details">
                    <p class="sender-name">{{ invitationData.sender_name }}</p>
                    <p class="invitation-text">
                      {{ t('invitation.invited_you_to_join') }}
                    </p>
                  </div>
                </div>

                <div class="project-info">
                  <div class="project-icon">📁</div>
                  <h3 class="project-name">
                    {{ invitationData.project_name }}
                  </h3>
                </div>
              </div>

              <div v-if="invitationData.message" class="custom-message">
                <h3>{{ t('invitation.personal_message') }}</h3>
                <div class="message-content">{{ invitationData.message }}</div>
              </div>

              <div v-if="invitationData.expires_at" class="invitation-meta">
                <div class="expiry-info">
                  <span class="icon">⏰</span>
                  {{ t('invitation.expires_at') }}
                  {{ formatDate(invitationData.expires_at) }}
                </div>
              </div>
            </div>
          </div>

          <div class="decision-buttons">
            <button
              :disabled="processing"
              class="btn-accept"
              @click="acceptInvitation"
            >
              <span class="icon">✓</span>
              {{ t('invitation.accept') }}
            </button>

            <button
              :disabled="processing"
              class="btn-reject"
              @click="rejectInvitation"
            >
              <span class="icon">✗</span>
              {{ t('invitation.reject') }}
            </button>
          </div>

          <div v-if="processing" class="processing-state">
            <div class="spinner-small"></div>
            <p>{{ t('invitation.processing') }}</p>
          </div>
        </div>

        <!-- Success State -->
        <div v-else-if="accepted" class="success-state">
          <div class="success-icon">✓</div>
          <h1>{{ t('invitation.accept_success_title') }}</h1>
          <p>{{ t('invitation.accept_success_message') }}</p>
          <router-link to="/projects" class="btn-primary">
            {{ t('invitation.go_to_projects') }}
          </router-link>
          <router-link to="/homePage" class="btn-secondary">
            {{ t('invitation.back_to_home') }}
          </router-link>
        </div>

        <!-- Rejection State -->
        <div v-else-if="rejected" class="rejection-state">
          <div class="success-icon">✓</div>
          <h1>{{ t('invitation.reject_success_title') }}</h1>
          <p>{{ t('invitation.reject_success_message') }}</p>
          <router-link to="/homePage" class="btn-primary">
            {{ t('invitation.back_to_home') }}
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { reportClientError } from '@/utils/errorDiagnostics';
import {
  acceptInvitation as acceptInvitationAPI,
  rejectInvitation as rejectInvitationAPI,
  getInvitationDetails,
} from '@/api/service/invitationService';

const route = useRoute();
const { t } = useI18n();

const loading = ref(true);
const error = ref(false);
const errorMessage = ref('');
const processing = ref(false);
const invitationData = ref(null);
const accepted = ref(false);
const rejected = ref(false);

// Fetch invitation details from API
const fetchInvitationDetails = async (invitationId) => {
  try {
    const response = await getInvitationDetails(invitationId);

    if (response.data.success) {
      return {
        invitation_id: response.data.invitation_id,
        sender_name: response.data.sender_name,
        project_name: response.data.project_name,
        message: response.data.message,
        expires_at: response.data.expires_at,
        created_at: response.data.created_at,
      };
    } else {
      throw new Error(
        response.data.message || 'Failed to fetch invitation details'
      );
    }
  } catch (err) {
    reportClientError('Error fetching invitation details', err);
    throw new Error(
      apiErrorMessage(err, t, err).message ||
        'Failed to fetch invitation details'
    );
  }
};

const loadInvitationDetails = async () => {
  try {
    const invitationId = route.params.invitationId;

    if (!invitationId) {
      throw new Error('Invalid invitation ID');
    }

    const details = await fetchInvitationDetails(invitationId);
    invitationData.value = details;
  } catch (err) {
    reportClientError('Error loading invitation', err);
    error.value = true;
    errorMessage.value = err.message || t('invitation.load_error');
  } finally {
    loading.value = false;
  }
};

const acceptInvitation = async () => {
  if (processing.value) return;

  processing.value = true;
  try {
    const invitationId = route.params.invitationId;
    const response = await acceptInvitationAPI(invitationId);

    if (response.data.success) {
      accepted.value = true;
    } else {
      throw new Error(response.data.message || t('invitation.accept_error'));
    }
  } catch (err) {
    reportClientError('Error accepting invitation', err);
    error.value = true;
    errorMessage.value = apiErrorMessage(
      err,
      t,
      err.message || t('invitation.accept_error')
    );
  } finally {
    processing.value = false;
  }
};

const rejectInvitation = async () => {
  if (processing.value) return;

  processing.value = true;
  try {
    const invitationId = route.params.invitationId;
    const response = await rejectInvitationAPI(invitationId);

    if (response.data.success) {
      rejected.value = true;
    } else {
      throw new Error(response.data.message || t('invitation.reject_error'));
    }
  } catch (err) {
    reportClientError('Error rejecting invitation', err);
    error.value = true;
    errorMessage.value = apiErrorMessage(
      err,
      t,
      err.message || t('invitation.reject_error')
    );
  } finally {
    processing.value = false;
  }
};

const formatDate = (dateString) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
};

onMounted(() => {
  loadInvitationDetails();
});
</script>

<style src="@/assets/css/invitation-decision-page.css"></style>
