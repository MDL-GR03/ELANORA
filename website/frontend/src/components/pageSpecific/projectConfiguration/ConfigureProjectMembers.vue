<template>
  <div class="configure-project-members">
    <div class="members-header">
      <h3>{{ t('projectSettings.members.title') }}</h3>
      <button
        v-if="canAddUsers"
        ref="addMemberButton"
        type="button"
        class="btn-add-member"
        @click="openAddUserModal"
      >
        <span class="add-icon">+</span>
        {{ t('projectSettings.members.add_member') }}
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
      <button class="btn-retry" @click="loadUsers">
        {{ t('common.retry') }}
      </button>
    </div>

    <!-- Members List -->
    <div v-else class="members-content">
      <div v-if="users.length === 0" class="empty-state">
        <div class="empty-icon">👥</div>
        <p>{{ t('projectSettings.members.no_members') }}</p>
        <small>{{ t('projectSettings.members.no_members_desc') }}</small>
      </div>

      <div v-else class="members-grid">
        <div v-for="user in users" :key="user.user_id" class="member-card">
          <div class="member-info">
            <div class="member-avatar">
              {{ user.username.charAt(0).toUpperCase() }}
            </div>
            <div class="member-details">
              <div class="member-name">{{ user.username }}</div>
              <div class="member-email">{{ user.email }}</div>
            </div>
          </div>

          <div class="member-permission">
            <template v-if="canEditUser(user)">
              <div class="member-permission-row">
                <div class="permission-selector">
                  <AppSelect
                    :id="`member-permission-${user.user_id}`"
                    :model-value="user.permission"
                    :disabled="updatingUsers.has(user.user_id)"
                    class="permission-select-control"
                    size="small"
                    :options="permissionOptionsFor(user)"
                    @change="handlePermissionChange(user, $event)"
                  />
                  <div
                    v-if="updatingUsers.has(user.user_id)"
                    class="update-spinner"
                  >
                    <div class="spinner-small"></div>
                  </div>
                </div>
                <button
                  v-if="canRemoveUser(user)"
                  type="button"
                  class="btn-remove"
                  :disabled="updatingUsers.has(user.user_id) || removingUser"
                  @click="confirmRemoveUser(user)"
                >
                  <font-awesome-icon icon="trash" />
                  <span>{{ t('common.remove') }}</span>
                </button>
              </div>
            </template>
            <span v-else class="permission-badge" :class="user.permission">
              {{ t(`projectSettings.permissions.${user.permission}`) }}
            </span>
            <label
              v-if="canEditUser(user)"
              class="capability-toggle"
              :title="t('project.users.protocol_manager_help')"
            >
              <input
                type="checkbox"
                :checked="user.capabilities?.includes('manage_protocols')"
                :disabled="updatingCapabilities.has(user.user_id)"
                @change="handleProtocolCapabilityChange(user, $event)"
              />
              {{ t('project.users.protocol_manager') }}
            </label>
          </div>

          <div v-if="!canEditUser(user)" class="member-actions">
            <div class="no-actions">
              <span v-if="user.permission === 'owner'" class="owner-badge">
                {{ t('projectSettings.permissions.owner') }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add User Modal -->
    <div
      v-if="showAddUserModal"
      class="modal-overlay"
      role="presentation"
      @click.self="closeAddUserModal"
    >
      <div
        ref="addMemberDialog"
        class="modal-content"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-member-title"
        aria-describedby="add-member-description"
        tabindex="-1"
      >
        <div class="modal-header">
          <span class="modal-header-icon">
            <font-awesome-icon icon="fa-solid fa-circle-user" />
          </span>
          <div>
            <span class="modal-eyebrow">
              {{ t('projectSettings.members.add_modal.eyebrow') }}
            </span>
            <h4 id="add-member-title">
              {{ t('projectSettings.members.add_modal.title') }}
            </h4>
          </div>
          <button
            type="button"
            class="modal-close"
            :aria-label="t('common.cancel')"
            @click="closeAddUserModal"
          >
            <font-awesome-icon icon="fa-solid fa-xmark" />
          </button>
        </div>

        <form class="add-member-form" @submit.prevent="addUser">
          <p id="add-member-description" class="modal-description">
            {{ t('projectSettings.members.add_modal.description') }}
          </p>
          <div class="form-group">
            <label for="userId"
              >{{ t('project.share.select_user') }}
              <span class="share-required">*</span></label
            >
            <AppSelect
              id="userId"
              v-model="newUser.user_id"
              :disabled="loadingAvailableUsers"
              :required="true"
              :placeholder="
                loadingAvailableUsers
                  ? t('common.loading')
                  : t('project.share.choose_user')
              "
              :options="availableUserOptions"
              :aria-describedby="formError ? 'add-member-error' : undefined"
            />
          </div>

          <div class="form-group">
            <label for="permission">{{
              t('projectSettings.members.add_modal.permission')
            }}</label>
            <AppSelect
              id="permission"
              v-model="newUser.permission"
              :required="true"
              :options="permissionOptions"
            />
          </div>

          <p
            v-if="formError"
            id="add-member-error"
            class="add-member-error"
            role="alert"
          >
            {{ formError }}
          </p>

          <div class="form-actions">
            <button type="button" class="btn-cancel" @click="closeAddUserModal">
              {{ t('common.cancel') }}
            </button>
            <button
              type="submit"
              class="btn-submit"
              :disabled="addingUser || !newUser.user_id"
            >
              <span v-if="addingUser" class="loading-text"
                >{{ t('common.adding') }}...</span
              >
              <span v-else>{{ t('common.add') }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useUserConfirm } from '@/composables/useUserConfirm';
import { useModalDialog } from '@/composables/useModalDialog';
import AppSelect from '@/components/common/AppSelect.vue';
import { reportClientError } from '@/utils/errorDiagnostics';
import {
  getProjectUsers,
  getAvailableProjectUsers,
  addUserToProject,
  updateUserPermission,
  removeUserFromProject,
  grantProtocolManager,
  revokeProtocolManager,
} from '@/api/service/projectAssociationService';

const { t } = useI18n();
const route = useRoute();
const projectStore = useProjectStore();
const userStore = useUserStore();
const eventMessageStore = useEventMessageStore();
const userConfirm = useUserConfirm();

const projectId = computed(() => Number(route.params.projectId));

// Reactive state
const users = ref([]);
const loading = ref(false);
const error = ref('');
const formError = ref('');

// Modal states
const showAddUserModal = ref(false);
const addMemberButton = ref(null);
const addMemberDialog = ref(null);

// Operation states
const updatingUsers = ref(new Set());
const updatingCapabilities = ref(new Set());
const addingUser = ref(false);
const removingUser = ref(false);
const loadingAvailableUsers = ref(false);

// Form data
const newUser = reactive({
  user_id: '',
  permission: 'read',
});

// Available users list for Add Member modal
const availableUsers = ref([]);
const filteredAvailableUsers = computed(() => {
  const existingIds = new Set(users.value.map((u) => u.user_id));
  return availableUsers.value.filter((u) => !existingIds.has(u.user_id));
});
const permissionOptions = computed(() =>
  ['read', 'write', 'admin'].map((permission) => ({
    value: permission,
    label: t(`projectSettings.permissions.${permission}`),
  }))
);
const permissionOptionsFor = (user) =>
  getAvailablePermissions(user).map((permission) => ({
    value: permission,
    label: t(`projectSettings.permissions.${permission}`),
  }));
const availableUserOptions = computed(() =>
  filteredAvailableUsers.value.map((user) => ({
    value: user.user_id,
    label: `${user.first_name} ${user.last_name} (${user.username}) - ${user.email}`,
  }))
);

// Computed properties
const currentUserRole = computed(() => {
  if (!userStore.user) return null;
  if (userStore.user.role === 'admin') return 'owner';
  if (!users.value.length) return null;

  const currentUser = users.value.find(
    (user) => user.user_id === userStore.user.user_id
  );

  return currentUser?.permission || null;
});

const canAddUsers = computed(() => {
  return ['admin', 'owner'].includes(currentUserRole.value);
});

// Methods
const loadUsers = async () => {
  if (!projectId.value) {
    error.value = t('projectSettings.members.no_project_selected');
    return;
  }

  loading.value = true;
  error.value = '';

  try {
    const response = await getProjectUsers(projectId.value);
    if (response.data) {
      users.value = response.data.users || [];
    }
  } catch (err) {
    reportClientError('Error loading users', err);
    error.value =
      err.response?.data?.detail || t('projectSettings.members.load_error');
  } finally {
    loading.value = false;
  }
};

// Load active users for the Add Member modal (similar to ProjectShareModal)
const loadActiveUsers = async () => {
  if (loadingAvailableUsers.value) return;
  loadingAvailableUsers.value = true;
  try {
    const response = await getAvailableProjectUsers(projectId.value);
    if (response.data && response.data.users) {
      availableUsers.value = response.data.users;
    }
  } catch (err) {
    reportClientError('Error loading available users', err);
    eventMessageStore.addMessage('project.share.error_loading_users', 'error');
  } finally {
    loadingAvailableUsers.value = false;
  }
};

const canEditUser = (user) => {
  // Only admin and owner can edit permissions
  if (!['admin', 'owner'].includes(currentUserRole.value)) return false;

  // Owner cannot be edited
  if (user.permission === 'owner') return false;

  // Admin cannot edit other admins (only owner can)
  return !(user.permission === 'admin' && currentUserRole.value !== 'owner');
};

const canRemoveUser = (user) => {
  // Only admin and owner can remove users
  if (!['admin', 'owner'].includes(currentUserRole.value)) return false;

  // Owner cannot be removed
  if (user.permission === 'owner') return false;

  // Admins can remove read/write users, but only owner can remove admins
  if (user.permission === 'admin') {
    return currentUserRole.value === 'owner';
  }

  return true;
};

const getAvailablePermissions = () => {
  const allPermissions = ['read', 'write', 'admin'];

  // Filter permissions based on current user role
  if (currentUserRole.value === 'owner') {
    return allPermissions;
  } else if (currentUserRole.value === 'admin') {
    // Admins can only set read/write permissions
    return ['read', 'write'];
  }

  return [];
};

const handlePermissionChange = async (user, newPermission) => {
  if (user.permission === newPermission) return;

  const oldPermission = user.permission;
  const confirmed = await userConfirm({
    title: t('projectSettings.members.confirm_permission_change.title'),
    message: t('projectSettings.members.confirm_permission_change.message', {
      username: user.username,
      oldPermission: t(`projectSettings.permissions.${oldPermission}`),
      newPermission: t(`projectSettings.permissions.${newPermission}`),
    }),
    confirmText: t('common.confirm'),
    cancelText: t('common.cancel'),
  });

  if (confirmed) {
    await updateUserPermissionHandler(user, newPermission);
  }
};

const updateUserPermissionHandler = async (user, newPermission = null) => {
  const permission = newPermission || user.permission;
  const oldPermission = user.permission;

  // Optimistically update the UI
  user.permission = permission;
  updatingUsers.value.add(user.user_id);

  try {
    const response = await updateUserPermission(projectId.value, user.user_id, {
      permission,
    });

    if (response.data) {
      eventMessageStore.addMessage(
        'projectSettings.members.permission_updated',
        'success'
      );
    }
  } catch (err) {
    reportClientError('Error updating user permission', err);
    // Revert the change
    user.permission = oldPermission;
    eventMessageStore.addMessage(
      'projectSettings.members.permission_update_error',
      'error'
    );
  } finally {
    updatingUsers.value.delete(user.user_id);
  }
};

const handleProtocolCapabilityChange = async (user, changeEvent) => {
  const enabled = changeEvent.target.checked;
  updatingCapabilities.value.add(user.user_id);
  try {
    if (enabled) {
      await grantProtocolManager(projectId.value, user.user_id);
    } else {
      await revokeProtocolManager(projectId.value, user.user_id);
    }
    const capabilities = new Set(user.capabilities || []);
    if (enabled) capabilities.add('manage_protocols');
    else capabilities.delete('manage_protocols');
    user.capabilities = [...capabilities];
    eventMessageStore.addMessage(
      'projectSettings.members.capability_updated',
      'success'
    );
  } catch {
    changeEvent.target.checked = !enabled;
    eventMessageStore.addMessage(
      'projectSettings.members.capability_update_error',
      'error'
    );
  } finally {
    updatingCapabilities.value.delete(user.user_id);
  }
};

const confirmRemoveUser = async (user) => {
  const confirmed = await userConfirm({
    title: t('projectSettings.members.confirm_remove.title'),
    message: t('projectSettings.members.confirm_remove.message', {
      username: user.username,
    }),
    confirmText: t('common.remove'),
    cancelText: t('common.cancel'),
  });

  if (confirmed) {
    await removeUser(user);
  }
};

const closeAddUserModal = () => {
  showAddUserModal.value = false;
  newUser.user_id = '';
  newUser.permission = 'read';
  formError.value = '';
};

const openAddUserModal = () => {
  showAddUserModal.value = true;
};

const addUser = async () => {
  if (!newUser.user_id) {
    formError.value = t('projectSettings.members.add_modal.user_required');
    return;
  }
  addingUser.value = true;
  formError.value = '';

  try {
    const response = await addUserToProject(projectId.value, {
      user_id: parseInt(newUser.user_id, 10),
      permission: newUser.permission,
    });
    if (response.data) {
      eventMessageStore.addMessage(
        'projectSettings.members.user_added',
        'success'
      );
      closeAddUserModal();
      await loadUsers(); // Refresh the list
    }
  } catch (err) {
    reportClientError('Error adding user', err);
    eventMessageStore.addMessage(
      err.response?.data?.detail || 'projectSettings.members.add_error',
      'error'
    );
  } finally {
    addingUser.value = false;
  }
};

const removeUser = async (user) => {
  if (!user) return;

  removingUser.value = true;

  try {
    const response = await removeUserFromProject(projectId.value, user.user_id);

    if (response.data) {
      eventMessageStore.addMessage(
        'projectSettings.members.user_removed',
        'success'
      );
      await loadUsers(); // Refresh the list
    }
  } catch (err) {
    reportClientError('Error removing user', err);
    eventMessageStore.addMessage(
      'projectSettings.members.remove_error',
      'error'
    );
  } finally {
    removingUser.value = false;
  }
};

// Lifecycle
onMounted(() => {
  // Only load users if we have a project ID
  if (projectId.value) {
    loadUsers();
  }
  projectStore.initBroadcastChannel();
});

// When opening the Add Member modal, load available users
watch(showAddUserModal, (open) => {
  if (open) loadActiveUsers();
});

useModalDialog(addMemberDialog, {
  onClose: closeAddUserModal,
  isOpen: showAddUserModal,
  initialFocus: addMemberDialog,
});

// Watch for project changes
watch(projectId, (newProjectId) => {
  if (newProjectId) {
    loadUsers();
  } else {
    users.value = [];
    error.value = '';
  }
});

// Expose methods for parent components if needed
defineExpose({
  loadUsers,
  users,
});
</script>

<style scoped>
.configure-project-members {
  padding: 0;
}

.members-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e5e7eb;
}

.members-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.125rem;
  font-weight: 600;
}

.btn-add-member {
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

.btn-add-member:hover {
  background: #1565c0;
  transform: translateY(-1px);
}

.add-icon {
  font-size: 1rem;
  font-weight: bold;
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
  border-top: 3px solid #6366f1;
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

.members-grid {
  display: grid;
  gap: 1rem;
}

.member-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 18rem) auto;
  align-items: center;
  gap: 1rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s ease;
}

.capability-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.5rem;
  color: #4b5563;
  font-size: 0.8rem;
  cursor: pointer;
}

.member-card:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.member-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.member-details {
  flex: 1;
  min-width: 0;
}

.member-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 0.125rem;
}

.member-email {
  font-size: 0.875rem;
  color: #6b7280;
  overflow-wrap: anywhere;
}

.member-permission-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.permission-selector {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  width: min(17rem, 100%);
}

.permission-select-control {
  min-width: 8rem;
}

.update-spinner {
  display: flex;
  align-items: center;
}

.spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top: 2px solid #6366f1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
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

.permission-badge.owner {
  background: #ede9fe;
  color: #6b21a8;
}

.btn-remove {
  min-height: 2.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.7rem;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  background: #fff;
  color: #dc2626;
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 700;
  transition: all 0.2s ease;
}

.btn-remove:hover:not(:disabled) {
  background: #fef2f2;
  transform: scale(1.1);
}

@media (width <= 760px) {
  .member-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .member-permission-row {
    align-items: stretch;
  }

  .permission-selector {
    width: auto;
    flex: 1;
    min-width: 0;
  }

  .member-actions {
    justify-self: start;
  }
}

@media (width <= 460px) {
  .member-permission-row {
    flex-direction: column;
  }

  .btn-remove {
    width: 100%;
  }
}

.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-actions {
  width: 32px;
  text-align: center;
}

.owner-badge {
  font-size: 0.75rem;
  color: #6b21a8;
  font-weight: 500;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  inset: 0;
  padding: 24px;
  background: rgb(18 35 64 / 58%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(3px);
}

.modal-content {
  background: white;
  border: 1px solid #d7e1f0;
  border-radius: 18px;
  padding: 0;
  width: min(520px, 100%);
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  box-shadow: 0 24px 70px rgb(15 35 70 / 28%);
}

.modal-header {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.85rem;
  align-items: center;
  margin: 0;
  padding: 1.4rem 1.5rem 1.15rem;
  background: linear-gradient(145deg, #fff, #f7faff);
  border-bottom: 1px solid #e2e8f2;
}

.modal-header h4 {
  margin: 0;
  color: #1f2937;
  font-size: 1.15rem;
  font-weight: 700;
}

.modal-header-icon {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  color: #2864e8;
  background: #e8f0ff;
  border-radius: 11px;
}

.modal-eyebrow {
  display: block;
  margin-bottom: 0.15rem;
  color: #2864e8;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.075em;
  text-transform: uppercase;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  transition: all 0.2s ease;
}

.modal-close:hover {
  color: #374151;
  background: #f3f4f6;
}

.add-member-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  padding: 1.4rem 1.5rem 1.5rem;
}

.modal-description {
  margin: 0;
  color: #647595;
  font-size: 0.9rem;
  line-height: 1.55;
}

.add-member-error {
  margin: -0.25rem 0 0;
  padding: 0.7rem 0.8rem;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 0.875rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 500;
  color: #374151;
  font-size: 0.875rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin: 0.4rem -1.5rem -1.5rem;
  padding: 1rem 1.5rem;
  background: #f7f9fc;
  border-top: 1px solid #e2e8f2;
}

.btn-cancel,
.btn-submit {
  padding: 0.625rem 1.25rem;
  border: none;
  min-height: 42px;
  border-radius: 10px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

@media (width <= 560px) {
  .modal-overlay {
    align-items: end;
    padding: 12px;
  }

  .modal-content {
    border-radius: 16px;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions button {
    width: 100%;
  }
}

.btn-cancel {
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-cancel:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-submit {
  background: #6366f1;
  color: white;
}

.btn-submit:hover:not(:disabled) {
  background: #4f46e5;
}

.btn-cancel:disabled,
.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-text::after {
  content: '';
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentcolor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
</style>
