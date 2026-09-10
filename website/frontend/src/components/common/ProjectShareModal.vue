<template>
  <div
    v-if="show"
    class="modal-overlay"
    role="presentation"
    @click="closeModal"
  >
    <div
      class="modal-content share-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-project-title"
      @click.stop
      @keydown.esc="closeModal"
    >
      <div class="modal-header">
        <span class="share-modal-icon">
          <font-awesome-icon icon="fa-regular fa-share-from-square" />
        </span>
        <div>
          <span class="share-modal-eyebrow">Project access</span>
          <h2 id="share-project-title">
            {{ t('project.share.title', { projectName }) }}
          </h2>
          <p>Invite a researcher and choose the access they need.</p>
        </div>
        <button
          type="button"
          class="close-btn"
          :aria-label="t('common.cancel')"
          @click="closeModal"
        >
          <font-awesome-icon icon="fa-solid fa-xmark" />
        </button>
      </div>

      <div class="share-options">
        <!-- Tab Selector -->
        <div class="tab-selector" role="tablist" aria-label="Invitation method">
          <button
            class="tab-button"
            :class="{ active: inviteMode === 'email' }"
            role="tab"
            :aria-selected="inviteMode === 'email'"
            @click="setInviteMode('email')"
          >
            {{ t('project.share.invite_by_email') }}
          </button>
          <button
            class="tab-button"
            :class="{ active: inviteMode === 'user' }"
            role="tab"
            :aria-selected="inviteMode === 'user'"
            @click="setInviteMode('user')"
          >
            {{ t('project.share.invite_existing_user') }}
          </button>
        </div>

        <!-- Email Invitation Form -->
        <div v-if="inviteMode === 'email'" class="tab-content">
          <form class="invitation-form" @submit.prevent="sendProjectInvitation">
            <div class="share-form-group">
              <label for="share-email" class="form-label">
                {{ t('project.share.email_label') }}
                <span class="share-required">*</span>
              </label>
              <input
                id="share-email"
                v-model="form.email"
                type="email"
                class="form-input"
                :class="{ error: emailError }"
                :placeholder="t('project.share.email_placeholder')"
                required
              />
              <div v-if="emailError" class="share-error-message">
                {{ emailError }}
              </div>
            </div>

            <div class="share-form-group">
              <label for="share-message" class="form-label">
                {{ t('project.share.message_label') }}
              </label>
              <textarea
                id="share-message"
                v-model="form.message"
                class="form-textarea share-form-textarea"
                :placeholder="t('project.share.message_placeholder')"
                rows="3"
              ></textarea>
            </div>

            <div class="share-form-group">
              <label for="share-language" class="form-label">
                {{ t('project.share.language_label') }}
              </label>
              <AppSelect
                id="share-language"
                v-model="form.language"
                :options="languageOptions"
              />
            </div>

            <div class="share-form-group">
              <label for="share-email-permission" class="form-label">
                {{ t('project.share.permission_label') }}
              </label>
              <AppSelect
                id="share-email-permission"
                v-model="form.emailPermission"
                :options="permissionOptions"
              />
            </div>

            <button
              type="submit"
              class="btn-primary send-btn"
              :disabled="sending || !form.email"
            >
              <span v-if="sending">{{ t('project.share.sending') }}</span>
              <span v-else>{{ t('project.share.send_invitation') }}</span>
            </button>
          </form>
        </div>

        <!-- User Selection Form -->
        <div v-if="inviteMode === 'user'" class="tab-content">
          <form class="invitation-form" @submit.prevent="sendUserInvitation">
            <div class="share-form-group">
              <label for="share-user" class="form-label">
                {{ t('project.share.select_user') }}
                <span class="share-required">*</span>
              </label>
              <AppSelect
                id="share-user"
                v-model="form.selectedUserId"
                :invalid="Boolean(userError)"
                :required="true"
                :disabled="loadingUsers"
                :placeholder="
                  loadingUsers
                    ? t('common.loading')
                    : t('project.share.choose_user')
                "
                :options="userOptions"
              />
              <div v-if="userError" class="share-error-message">
                {{ userError }}
              </div>
            </div>

            <div class="share-form-group">
              <label for="share-user-message" class="form-label">
                {{ t('project.share.message_label') }}
              </label>
              <textarea
                id="share-user-message"
                v-model="form.userMessage"
                class="form-textarea share-form-textarea"
                :placeholder="t('project.share.message_placeholder')"
                rows="3"
              ></textarea>
            </div>

            <div class="share-form-group">
              <label for="share-user-language" class="form-label">
                {{ t('project.share.language_label') }}
              </label>
              <AppSelect
                id="share-user-language"
                v-model="form.userLanguage"
                :options="languageOptions"
              />
            </div>

            <div class="share-form-group">
              <label for="share-permission" class="form-label">
                {{ t('project.share.permission_label') }}
              </label>
              <AppSelect
                id="share-permission"
                v-model="form.permission"
                :options="permissionOptions"
              />
            </div>

            <button
              type="submit"
              class="btn-primary send-btn"
              :disabled="sending || !form.selectedUserId"
            >
              <span v-if="sending">{{ t('project.share.sending') }}</span>
              <span v-else>{{ t('project.share.send_invitation') }}</span>
            </button>
          </form>
        </div>

        <!-- Success Message -->
        <div v-if="successMessage" class="share-success-message">
          {{ successMessage }}
        </div>

        <!-- Error Message -->
        <div v-if="errorMessage" class="share-error-message">
          {{ errorMessage }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEventMessageStore } from '@stores/eventMessage';
import { sendInvitation as sendInvitationAPI } from '@/api/service/invitationService';
import { getAvailableProjectUsers } from '@/api/service/projectAssociationService';
import AppSelect from '@/components/common/AppSelect.vue';
import '@/assets/css/ProjectShareModal.css';

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  projectName: {
    type: String,
    required: true,
  },
  projectId: {
    type: Number,
    required: true,
  },
});

const emit = defineEmits(['close', 'success']);

const { t } = useI18n();
const eventMessageStore = useEventMessageStore();

// Invitation mode: 'email' or 'user'
const inviteMode = ref('email');

// Form data
const form = ref({
  email: '',
  message: '',
  language: 'fr',
  emailPermission: 'read',
  selectedUserId: '',
  userMessage: '',
  userLanguage: 'fr',
  permission: 'read',
});

// States
const sending = ref(false);
const emailError = ref('');
const userError = ref('');
const successMessage = ref('');
const errorMessage = ref('');
const loadingUsers = ref(false);
const availableUsers = ref([]);

const projectName = computed(() => props.projectName);
const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
];
const permissionOptions = computed(() => [
  { value: 'read', label: t('project.share.permission_read') },
  { value: 'write', label: t('project.share.permission_write') },
  { value: 'admin', label: t('project.share.permission_admin') },
]);
const userOptions = computed(() =>
  availableUsers.value.map((user) => ({
    value: user.user_id,
    label: `${user.first_name} ${user.last_name} (${user.username}) - ${user.email}`,
  }))
);

// Get selected user's email
const selectedUserEmail = computed(() => {
  if (!form.value.selectedUserId) return '';
  const user = availableUsers.value.find(
    (u) => u.user_id == form.value.selectedUserId
  );
  return user ? user.email : '';
});

// Load users when modal opens and user mode is selected
const loadActiveUsers = async () => {
  if (loadingUsers.value) return;

  loadingUsers.value = true;
  try {
    const response = await getAvailableProjectUsers(props.projectId);
    if (response.data && response.data.users) {
      availableUsers.value = response.data.users;
    }
  } catch (error) {
    console.error('Error loading users:', error);
    eventMessageStore.addMessage('project.share.error_loading_users', 'error');
  } finally {
    loadingUsers.value = false;
  }
};

// Watch for mode changes and modal visibility
watch(
  () => props.show,
  (newShow) => {
    if (newShow && inviteMode.value === 'user') {
      loadActiveUsers();
    }
  }
);

watch(inviteMode, (newMode) => {
  if (newMode === 'user' && props.show) {
    loadActiveUsers();
  }
});

// Load users on component mount if needed
onMounted(() => {
  if (props.show && inviteMode.value === 'user') {
    loadActiveUsers();
  }
});

// Helper function to handle invitation errors
const handleInvitationError = (error) => {
  console.error('Error sending invitation:', error);

  // Check if it's a server response with a specific message
  if (error.response?.data?.message) {
    const message = error.response.data.message.toLowerCase();

    if (message.includes('active invitation already exists')) {
      eventMessageStore.addMessage(
        'project.share.invitation_send_error_already_invited',
        'warning'
      );
    } else if (message.includes('already a member')) {
      eventMessageStore.addMessage(
        'project.share.invitation_send_error_already_member',
        'warning'
      );
    } else if (message.includes('project not found')) {
      eventMessageStore.addMessage(
        'project.share.invitation_send_error_project_not_found',
        'error'
      );
    } else {
      // Generic error with server message
      eventMessageStore.addMessage(error.response.data.message, 'error');
    }
  } else if (error.response?.status === 409) {
    // Conflict status usually means already invited or already member
    eventMessageStore.addMessage(
      'project.share.invitation_send_error_already_invited',
      'warning'
    );
  } else if (error.response?.status === 400) {
    // Bad request - could be validation error
    eventMessageStore.addMessage(
      error.response?.data?.detail ||
        'project.share.invitation_send_error_generic',
      'error'
    );
  } else {
    // Generic network or unknown error
    eventMessageStore.addMessage(
      'project.share.invitation_send_error_generic',
      'error'
    );
  }
};

const setInviteMode = (mode) => {
  inviteMode.value = mode;
  // Clear errors when switching modes
  emailError.value = '';
  userError.value = '';
  successMessage.value = '';
  errorMessage.value = '';
};

const closeModal = () => {
  // Reset form and states
  form.value = {
    email: '',
    message: '',
    language: 'fr',
    emailPermission: 'read',
    selectedUserId: '',
    userMessage: '',
    userLanguage: 'fr',
    permission: 'read',
  };
  emailError.value = '';
  userError.value = '';
  successMessage.value = '';
  errorMessage.value = '';
  inviteMode.value = 'email';
  emit('close');
};

const sendProjectInvitation = async () => {
  emailError.value = '';

  if (!form.value.email) {
    emailError.value = t('project.share.email_required');
    return;
  }

  sending.value = true;

  try {
    const invitationData = {
      receiver_email: form.value.email,
      project_name: projectName.value,
      message: form.value.message,
      language: form.value.language,
      expires_in_days: 7,
      project_permission: form.value.emailPermission,
    };

    const response = await sendInvitationAPI(invitationData);

    if (response.data.success) {
      eventMessageStore.addMessage(
        'project.share.invitation_sent_success',
        'success'
      );
      form.value.email = '';
      form.value.message = '';
      emit('success');
    } else if (response.data.message) {
      // Handle specific error from server response
      const message = response.data.message.toLowerCase();
      if (message.includes('active invitation already exists')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_already_invited',
          'warning'
        );
      } else if (message.includes('already a member')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_already_member',
          'warning'
        );
      } else if (message.includes('project not found')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_project_not_found',
          'error'
        );
      } else {
        eventMessageStore.addMessage(response.data.message, 'error');
      }
    } else {
      eventMessageStore.addMessage(
        'project.share.invitation_send_error',
        'error'
      );
    }
  } catch (error) {
    handleInvitationError(error, form.value.email);
  } finally {
    sending.value = false;
  }
};

const sendUserInvitation = async () => {
  userError.value = '';

  if (!form.value.selectedUserId) {
    userError.value = t('project.share.user_required');
    return;
  }

  const userEmail = selectedUserEmail.value;
  if (!userEmail) {
    userError.value = t('project.share.user_email_not_found');
    return;
  }

  sending.value = true;

  try {
    const invitationData = {
      receiver_email: userEmail,
      project_name: projectName.value,
      message: form.value.userMessage,
      language: form.value.userLanguage,
      expires_in_days: 7,
      project_permission: form.value.permission,
    };

    const response = await sendInvitationAPI(invitationData);

    if (response.data.success) {
      eventMessageStore.addMessage(
        'project.share.invitation_sent_success',
        'success'
      );
      form.value.selectedUserId = '';
      form.value.userMessage = '';
      emit('success');
    } else if (response.data.message) {
      // Handle specific error from server response
      const message = response.data.message.toLowerCase();
      if (message.includes('active invitation already exists')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_already_invited',
          'warning'
        );
      } else if (message.includes('already a member')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_already_member',
          'warning'
        );
      } else if (message.includes('project not found')) {
        eventMessageStore.addMessage(
          'project.share.invitation_send_error_project_not_found',
          'error'
        );
      } else {
        eventMessageStore.addMessage(response.data.message, 'error');
      }
    } else {
      eventMessageStore.addMessage(
        'project.share.invitation_send_error',
        'error'
      );
    }
  } catch (error) {
    handleInvitationError(error, userEmail);
  } finally {
    sending.value = false;
  }
};
</script>
