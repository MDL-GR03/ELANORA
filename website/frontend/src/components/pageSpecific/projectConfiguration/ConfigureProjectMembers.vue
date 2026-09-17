<template>
  <div class="configure-project-members">
    <div class="members-header">
      <h3>{{ t('projectSettings.members.title') }}</h3>
      <button
        v-if="canAddMembers"
        type="button"
        class="btn-add-member"
        @click="addDialogOpen = true"
      >
        <span class="add-icon">+</span>
        {{ t('projectSettings.members.add_member') }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="error" class="error-state">
      <p class="error-message">{{ error }}</p>
      <button class="btn-retry" @click="load">
        {{ t('common.retry') }}
      </button>
    </div>

    <div v-else class="members-content">
      <div v-if="members.length === 0" class="empty-state">
        <div class="empty-icon">👥</div>
        <p>{{ t('projectSettings.members.no_members') }}</p>
        <small>{{ t('projectSettings.members.no_members_desc') }}</small>
      </div>

      <div v-else class="members-grid">
        <ProjectMemberCard
          v-for="member in members"
          :key="member.user_id"
          :member="member"
          :can-manage="canManageMember(role, member)"
          :permissions="assignablePermissions(role)"
          :busy="updating.has(member.user_id)"
          :removing="removing"
          @change-permission="confirmPermissionChange(member, $event)"
          @toggle-protocol-manager="toggleProtocolManager(member, $event)"
          @remove="confirmRemoval(member)"
        />
      </div>
    </div>

    <AddProjectMemberDialog
      v-if="addDialogOpen"
      :project-id="projectId"
      :member-ids="memberIds"
      :permissions="assignablePermissions(role)"
      :add="add"
      @close="addDialogOpen = false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';

import { useUserConfirm } from '@/composables/useUserConfirm';
import {
  assignablePermissions,
  canManageMember,
  isProtocolManager,
  useProjectMembers,
} from '@/composables/useProjectMembers';
import { useEventMessageStore } from '@/stores/eventMessage';
import { useProjectStore } from '@/stores/project';
import { useUserStore } from '@/stores/user';
import AddProjectMemberDialog from './AddProjectMemberDialog.vue';
import ProjectMemberCard from './ProjectMemberCard.vue';

const { t } = useI18n();
const route = useRoute();
const projectStore = useProjectStore();
const userStore = useUserStore();
const confirmAction = useUserConfirm();

const projectId = computed(() => Number(route.params.projectId));
const addDialogOpen = ref(false);
const {
  members,
  loading,
  error,
  updating,
  removing,
  role,
  canAddMembers,
  load,
  changePermission,
  setProtocolManager,
  add,
  remove,
} = useProjectMembers({
  projectId,
  account: computed(() => userStore.user),
  messages: useEventMessageStore(),
  translate: t,
});
const memberIds = computed(
  () => new Set(members.value.map((member) => member.user_id))
);

async function confirmPermissionChange(member, permission) {
  if (member.permission === permission) return;
  const confirmed = await confirmAction({
    title: t('projectSettings.members.confirm_permission_change.title'),
    message: t('projectSettings.members.confirm_permission_change.message', {
      username: member.username,
      oldPermission: t(`projectSettings.permissions.${member.permission}`),
      newPermission: t(`projectSettings.permissions.${permission}`),
    }),
    confirmText: t('common.confirm'),
    cancelText: t('common.cancel'),
  });
  if (confirmed) await changePermission(member, permission);
}

async function toggleProtocolManager(member, event) {
  await setProtocolManager(member, event.target.checked);
  // A refused change leaves the member as it was; show that state again.
  event.target.checked = isProtocolManager(member);
}

async function confirmRemoval(member) {
  const confirmed = await confirmAction({
    title: t('projectSettings.members.confirm_remove.title'),
    message: t('projectSettings.members.confirm_remove.message', {
      username: member.username,
    }),
    confirmText: t('common.remove'),
    cancelText: t('common.cancel'),
    tone: 'danger',
  });
  if (confirmed) await remove(member);
}

watch(projectId, () => void load());
onMounted(() => {
  if (projectId.value) void load();
  projectStore.initBroadcastChannel();
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
  border-bottom: 2px solid var(--color-border-subtle);
}

.members-header h3 {
  margin: 0;
  color: var(--color-gray-900);
  font-size: 1.125rem;
  font-weight: 600;
}

.btn-add-member {
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

.btn-add-member:hover {
  background: var(--color-blue-800-alt);
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
  border: 3px solid var(--color-gray-500-alt);
  border-top: 3px solid var(--color-indigo-500);
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

.members-grid {
  display: grid;
  gap: 1rem;
}
</style>
