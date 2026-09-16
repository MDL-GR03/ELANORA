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
    error.value =
      err.response?.data?.detail || t('projectSettings.invitations.load_error');
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
      err.response?.data?.detail || 'projectSettings.invitations.resend_error',
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
      err.response?.data?.detail || 'projectSettings.invitations.cancel_error',
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
  border-bottom: 2px solid #e5e7eb;
}

.invitations-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.125rem;
  font-weight: 600;
}

.btn-send-invitation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #1976d2;
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
  background: #1565c0;
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
  border: 3px solid #f3f4f6;
  border-top: 3px solid #10b981;
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
  color: #dc2626;
  margin-bottom: 1rem;
}

.btn-retry {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
}

.btn-retry:hover {
  background: #e5e7eb;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #6b7280;
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
  color: #9ca3af;
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
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s ease;
}

.invitation-card:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
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
  color: #1f2937;
  margin-bottom: 0.125rem;
}

.invitation-date {
  font-size: 0.875rem;
  color: #6b7280;
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
  background: #dbeafe;
  color: #1e40af;
}

.permission-badge.write {
  background: #d1fae5;
  color: #047857;
}

.permission-badge.admin {
  background: #fef3c7;
  color: #92400e;
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
  background: #fef3c7;
  color: #92400e;
}

.status-badge.accepted {
  background: #d1fae5;
  color: #047857;
}

.status-badge.declined {
  background: #fee2e2;
  color: #dc2626;
}

.status-badge.expired {
  background: #f3f4f6;
  color: #6b7280;
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
  background: #dbeafe;
  color: #1e40af;
}

.btn-resend:hover:not(:disabled) {
  background: #bfdbfe;
  transform: scale(1.1);
}

.btn-cancel {
  background: #fee2e2;
  color: #dc2626;
  font-weight: bold;
}

.btn-cancel:hover:not(:disabled) {
  background: #fecaca;
  transform: scale(1.1);
}

.btn-resend:disabled,
.btn-cancel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
