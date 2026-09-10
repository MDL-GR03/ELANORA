<template>
  <div class="admin-invitation-page">
    <div class="admin-container">
      <WorkspaceHeader
        :title="t('invitation.send_title')"
        :description="t('invitation.send_description')"
        :context="t('invitation.context')"
      />

      <!-- Send Invitation Form -->
      <div class="invitation-form-card">
        <form class="invitation-form" @submit.prevent="handleSendInvitation">
          <div class="form-group">
            <label for="email" class="form-label">
              {{ t('invitation.email_label') }}
              <span class="required">*</span>
            </label>
            <input
              id="email"
              v-model="form.email"
              type="email"
              class="form-input"
              :class="{ error: emailError }"
              :placeholder="t('invitation.email_placeholder')"
              required
            />
            <div v-if="emailError" class="error-message">{{ emailError }}</div>
          </div>

          <div class="form-group">
            <label for="project" class="form-label">
              {{ t('invitation.project_label') }}
              <span class="required">*</span>
            </label>
            <AppSelect
              id="project"
              v-model="form.projectName"
              :invalid="Boolean(projectError)"
              :required="true"
              :placeholder="t('invitation.selectProject')"
              :options="projectOptions"
            />
            <div v-if="projectError" class="error-message">
              {{ projectError }}
            </div>
          </div>

          <div class="form-group">
            <label for="message" class="form-label">
              {{ t('invitation.message_label') }}
            </label>
            <textarea
              id="message"
              v-model="form.message"
              class="form-textarea"
              :placeholder="t('invitation.message_placeholder')"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label for="language" class="form-label">
              {{ t('invitation.language_label') }}
            </label>
            <AppSelect
              id="language"
              v-model="form.language"
              :options="languageOptions"
            />
          </div>

          <button
            type="submit"
            class="btn-primary send-btn"
            :disabled="sending || !form.email || !form.projectName"
          >
            <span v-if="sending">{{ t('invitation.sending') }}</span>
            <span v-else>{{ t('invitation.send_button') }}</span>
          </button>
        </form>
      </div>

      <!-- Sent Invitations List -->
      <div class="sent-invitations-card">
        <h2 class="section-title">Recently Sent Invitations</h2>

        <div v-if="loadingInvitations" class="loading-message">
          Loading invitations...
        </div>

        <div v-else-if="sentInvitations.length === 0" class="empty-message">
          No invitations sent yet.
        </div>

        <div v-else class="invitations-list">
          <div
            v-for="invitation in sentInvitations"
            :key="invitation.invitation_id"
            class="invitation-item"
          >
            <div class="invitation-details">
              <div class="invitation-email">
                {{ invitation.receiver_email }}
              </div>
              <div class="invitation-meta">
                <span class="invitation-status" :class="invitation.status">
                  {{ invitation.status }}
                </span>
                <span class="invitation-date">
                  {{ formatDate(invitation.created_at) }}
                </span>
              </div>
            </div>
            <div class="invitation-code">
              <code>{{ invitation.invitation_id }}</code>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import WorkspaceHeader from '@/components/layout/WorkspaceHeader.vue';
import AppSelect from '@/components/common/AppSelect.vue';
import { computed, ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEventMessageStore } from '@stores/eventMessage';
import {
  sendInvitation,
  getSentInvitations,
} from '@/api/service/invitationService';
import gitService from '@/api/service/gitService';

const { t } = useI18n();
const eventMessageStore = useEventMessageStore();

// Reactive data
const form = ref({
  email: '',
  projectName: '',
  message: '',
  language: 'en',
});

const sending = ref(false);
const emailError = ref('');
const projectError = ref('');
const sentInvitations = ref([]);
const loadingInvitations = ref(false);
const projects = ref([]);
const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
];
const projectOptions = computed(() =>
  projects.value.map((project) => ({
    value: project.project_name || project,
    label: project.project_name || project,
  }))
);

// Load data on mount
onMounted(async () => {
  await Promise.all([loadSentInvitations(), loadProjects()]);
});

const loadProjects = async () => {
  try {
    const response = await gitService.listProjects();
    projects.value = response.projects || [];
  } catch (error) {
    console.error('Failed to load projects:', error);
    eventMessageStore.addMessage(
      t('appHeader.projectSection.loadError'),
      'error'
    );
  }
};

const validateEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const handleSendInvitation = async () => {
  emailError.value = '';
  projectError.value = '';

  // Validate email
  if (!validateEmail(form.value.email)) {
    emailError.value = t('invitation.invalid_email');
    return;
  }

  // Validate project selection
  if (!form.value.projectName) {
    projectError.value = t('invitation.project_required');
    return;
  }

  sending.value = true;

  try {
    const response = await sendInvitation({
      receiver_email: form.value.email,
      project_name: form.value.projectName, // Utiliser directement le nom du projet
      message: form.value.message || null,
      expires_in_days: 7,
      language: form.value.language || 'en',
    });

    if (response.data.success) {
      eventMessageStore.addMessage(t('invitation.success'), 'success');

      // Reset form
      form.value.email = '';
      form.value.projectName = '';
      form.value.message = '';

      // Reload sent invitations
      await loadSentInvitations();
    } else {
      eventMessageStore.addMessage(
        response.data.message || t('invitation.error'),
        'error'
      );
    }
  } catch (error) {
    console.error('Failed to send invitation:', error);
    eventMessageStore.addMessage(
      error.response?.data?.detail || t('invitation.error'),
      'error'
    );
  } finally {
    sending.value = false;
  }
};

const loadSentInvitations = async () => {
  loadingInvitations.value = true;

  try {
    const response = await getSentInvitations();
    const invitations = response.data.invitations || [];

    // Sort invitations by creation date, newest first
    sentInvitations.value = invitations.sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  } catch (error) {
    console.error('Failed to load sent invitations:', error);
    sentInvitations.value = [];
  } finally {
    loadingInvitations.value = false;
  }
};

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
};
</script>

<style src="@/assets/css/admin-invitations.css"></style>
