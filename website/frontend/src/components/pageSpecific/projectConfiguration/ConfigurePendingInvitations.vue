<template>
  <div class="configure-pending-invitations">
    <div class="invitations-header">
      <h3>{{ t('projectSettings.invitations.title') }}</h3>
      <button
        v-if="canManageInvitations"
        class="btn-send-invitation"
        @click="showInviteModal = true"
      >
        <span class="invite-icon">✉</span>
        {{ t('projectSettings.invitations.send_invitation') }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button class="btn-retry" @click="loadInvitations">
        {{ t('common.retry') }}
      </button>
    </div>

    <!-- Invitations List -->
    <div v-else class="invitations-content">
      <div v-if="invitations.length === 0" class="empty-state">
        <div class="empty-icon">📧</div>
        <p>{{ t('projectSettings.invitations.no_invitations') }}</p>
        <small>{{
          t('projectSettings.invitations.no_invitations_desc')
        }}</small>
      </div>

      <div v-else class="invitations-list">
        <div
          v-for="invitation in invitations"
          :key="invitation.invitation_id"
          class="invitation-card"
        >
          <div class="invitation-info">
            <div class="invitation-email">
              <span class="email-icon">📧</span>
              <div class="email-details">
                <div class="email-address">{{ invitation.receiver_email }}</div>
                <div class="invitation-date">
                  {{ t('projectSettings.invitations.sent_on') }}
                  {{ formatDate(invitation.created_at) }}
                </div>
              </div>
            </div>
          </div>

          <div class="invitation-permission">
            <span
              class="permission-badge"
              :class="invitation.project_permission"
            >
              {{
                t(
                  `projectSettings.permissions.${invitation.project_permission}`
                )
              }}
            </span>
          </div>

          <div class="invitation-status">
            <span class="status-badge" :class="invitation.status">
              {{ t(`projectSettings.invitations.status.${invitation.status}`) }}
            </span>
          </div>

          <div class="invitation-actions">
            <button
              v-if="canCancelInvitation(invitation)"
              class="btn-resend"
              :disabled="processingInvitations.has(invitation.invitation_id)"
              :title="t('projectSettings.invitations.resend')"
              @click="resendInvitation(invitation)"
            >
              🔄
            </button>
            <button
              v-if="canCancelInvitation(invitation)"
              class="btn-cancel"
              :disabled="processingInvitations.has(invitation.invitation_id)"
              :title="t('projectSettings.invitations.cancel')"
              @click="confirmCancelInvitation(invitation)"
            >
              ×
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Project Share Modal -->
    <ProjectShareModal
      :show="showInviteModal"
      :project-name="projectName"
      @close="closeInviteModal"
      @success="onInvitationSuccess"
    />
  </div>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserConfirm } from '@/composables/useUserConfirm';
import {
  getProjectInvitations,
  resendInvitation as resendInvitationAPI,
  cancelInvitation as cancelInvitationAPI,
} from '@/api/service/invitationService';
import ProjectShareModal from '@/components/common/ProjectShareModal.vue';
import { reportClientError } from '@/utils/errorDiagnostics';

const { t } = useI18n();
const route = useRoute();
const eventMessageStore = useEventMessageStore();
const projectStore = useProjectStore();
const userConfirm = useUserConfirm();

const projectId = computed(() => Number(route.params.projectId));
const projectName = computed(() => {
  const project = projectStore.projects.find(
    (p) => p.project_id === projectId.value
  );
  return project ? project.project_name : '';
});

const currentUserRole = ref('admin');

// Reactive state
const invitations = ref([]);
const loading = ref(false);
const error = ref('');

// Modal states
const showInviteModal = ref(false);

// Operation states
const processingInvitations = ref(new Set());

// Computed properties
const canManageInvitations = computed(() => {
  return ['admin', 'owner'].includes(currentUserRole.value);
});

// Methods
const loadInvitations = async () => {
  loading.value = true;
  error.value = '';

  try {
    if (!projectId.value) {
      console.warn('No project ID available');
      invitations.value = [];
      return;
    }

    const response = await getProjectInvitations(projectId.value);
    invitations.value = response.data.invitations || [];
  } catch (err) {
    reportClientError('Error loading invitations', err);
    error.value = apiErrorMessage(
      err,
      t,
      t('projectSettings.invitations.load_error')
    );
    invitations.value = [];
  } finally {
    loading.value = false;
  }
};

const canCancelInvitation = (invitation) => {
  return (
    ['admin', 'owner'].includes(currentUserRole.value) &&
    ['pending'].includes(invitation.status)
  );
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const closeInviteModal = () => {
  showInviteModal.value = false;
};

const onInvitationSuccess = async () => {
  // Reload invitations when a new invitation is sent successfully
  await loadInvitations();
};

const resendInvitation = async (invitation) => {
  processingInvitations.value.add(invitation.invitation_id);

  try {
    await resendInvitationAPI(invitation.invitation_id);
    eventMessageStore.addMessage(
      'projectSettings.invitations.invitation_resent',
      'success'
    );
    await loadInvitations();
  } catch (err) {
    reportClientError('Error resending invitation', err);
    eventMessageStore.addMessage(
      apiErrorMessage(err, t, 'projectSettings.invitations.resend_error'),
      'error'
    );
  } finally {
    processingInvitations.value.delete(invitation.invitation_id);
  }
};

const confirmCancelInvitation = async (invitation) => {
  const confirmed = await userConfirm({
    title: t('projectSettings.invitations.cancel_modal.title'),
    message: t('projectSettings.invitations.cancel_modal.message', {
      email: invitation.receiver_email,
    }),
    confirmText: t('common.yes_cancel'),
    tone: 'danger',
    cancelText: t('common.no'),
  });

  if (confirmed) {
    await cancelInvitation(invitation);
  }
};

const cancelInvitation = async (invitation) => {
  if (!invitation) return;

  processingInvitations.value.add(invitation.invitation_id);

  try {
    await cancelInvitationAPI(invitation.invitation_id);
    eventMessageStore.addMessage(
      'projectSettings.invitations.invitation_canceled',
      'success'
    );
    await loadInvitations(); // Refresh the list
  } catch (err) {
    reportClientError('Error canceling invitation', err);
    eventMessageStore.addMessage(
      apiErrorMessage(err, t, 'projectSettings.invitations.cancel_error'),
      'error'
    );
  } finally {
    processingInvitations.value.delete(invitation.invitation_id);
  }
};

watch(
  projectId,
  async () => {
    await loadInvitations();
  },
  { immediate: true }
);
</script>

<style scoped>
.configure-pending-invitations {
  padding: 0;
}

.invitations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-border-subtle);
}

.invitations-header h3 {
  margin: 0;
  color: var(--color-gray-900);
  font-size: 1.125rem;
  font-weight: 600;
}

.btn-send-invitation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--color-blue-700-alt);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-send-invitation:hover {
  background: var(--color-blue-800-alt);
  transform: translateY(-1px);
}

.invite-icon {
  font-size: 1rem;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 2rem 1rem;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-gray-500-alt);
  border-top: 3px solid var(--color-emerald-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.error-message {
  color: var(--color-error-light);
  margin-bottom: 1rem;
}

.btn-retry {
  background: var(--color-gray-500-alt);
  color: var(--color-slate-700);
  border: 1px solid var(--color-gray-300);
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
}

.btn-retry:hover {
  background: var(--color-border-subtle);
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-gray-600);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state p {
  font-size: 1.125rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

.empty-state small {
  font-size: 0.875rem;
  color: var(--color-text-subtle);
}

.invitations-list {
  display: grid;
  gap: 1rem;
}

.invitation-card {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: center;
  gap: 1rem;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s ease;
}

.invitation-card:hover {
  background: var(--color-gray-500-alt);
  border-color: var(--color-gray-300);
}

.invitation-email {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.email-icon {
  font-size: 1.25rem;
}

.email-details {
  flex: 1;
}

.email-address {
  font-weight: 500;
  color: var(--color-gray-900);
  margin-bottom: 0.125rem;
}

.invitation-date {
  font-size: 0.875rem;
  color: var(--color-gray-600);
}

.permission-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.permission-badge.read {
  background: var(--color-info-bg);
  color: var(--color-info-dark);
}

.permission-badge.write {
  background: var(--color-success-bg-subtle);
  color: var(--color-emerald-700);
}

.permission-badge.admin {
  background: var(--color-warning-bg);
  color: var(--color-amber-900);
}

.status-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.status-badge.pending {
  background: var(--color-warning-bg);
  color: var(--color-amber-900);
}

.status-badge.accepted {
  background: var(--color-success-bg-subtle);
  color: var(--color-emerald-700);
}

.status-badge.declined {
  background: var(--color-error-bg);
  color: var(--color-error-light);
}

.status-badge.expired {
  background: var(--color-gray-500-alt);
  color: var(--color-gray-600);
}

.invitation-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.btn-resend,
.btn-cancel {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-resend {
  background: var(--color-info-bg);
  color: var(--color-info-dark);
}

.btn-resend:hover:not(:disabled) {
  background: var(--color-blue-200);
  transform: scale(1.1);
}

.btn-cancel {
  background: var(--color-error-bg);
  color: var(--color-error-light);
  font-weight: bold;
}

.btn-cancel:hover:not(:disabled) {
  background: var(--color-error-bg-light);
  transform: scale(1.1);
}

.btn-resend:disabled,
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
