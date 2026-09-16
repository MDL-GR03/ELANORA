import { computed, ref } from 'vue';

import {
  addUserToProject,
  getProjectUsers,
  grantProtocolManager,
  removeUserFromProject,
  revokeProtocolManager,
  updateUserPermission,
} from '@/api/service/projectAssociationService';
import { apiErrorMessage } from '@/utils/apiError';
import { reportClientError } from '@/utils/errorDiagnostics';

export const PROJECT_PERMISSIONS = ['read', 'write', 'admin'];
const PROTOCOL_MANAGER = 'manage_protocols';

/**
 * The project role the signed-in user acts with. An institution administrator
 * acts as the owner of every project.
 */
export function actingProjectRole(account, members) {
  if (!account) return null;
  if (account.role === 'admin') return 'owner';
  return (
    members.find((member) => member.user_id === account.user_id)?.permission ??
    null
  );
}

/**
 * Whether a role may change or remove a member: owners manage everyone but
 * the owner, and project administrators manage readers and writers.
 */
export function canManageMember(role, member) {
  if (!['admin', 'owner'].includes(role)) return false;
  if (member.permission === 'owner') return false;
  return member.permission !== 'admin' || role === 'owner';
}

export function assignablePermissions(role) {
  if (role === 'owner') return PROJECT_PERMISSIONS;
  if (role === 'admin') return ['read', 'write'];
  return [];
}

/** Members of one project and the changes a manager can make to them. */
export function useProjectMembers({ projectId, account, messages, translate }) {
  const members = ref([]);
  const loading = ref(false);
  const error = ref('');
  const updating = ref(new Set());
  const removing = ref(false);

  const role = computed(() => actingProjectRole(account.value, members.value));
  const canAddMembers = computed(() => ['admin', 'owner'].includes(role.value));

  function withBusy(userId, task) {
    updating.value = new Set(updating.value).add(userId);
    return task().finally(() => {
      const next = new Set(updating.value);
      next.delete(userId);
      updating.value = next;
    });
  }

  async function load() {
    if (!projectId.value) {
      members.value = [];
      error.value = translate('projectSettings.members.no_project_selected');
      return;
    }
    loading.value = true;
    error.value = '';
    try {
      const response = await getProjectUsers(projectId.value);
      members.value = response.data?.users ?? [];
    } catch (err) {
      reportClientError('Error loading project members', err);
      error.value = apiErrorMessage(
        err,
        translate,
        translate('projectSettings.members.load_error')
      );
    } finally {
      loading.value = false;
    }
  }

  function changePermission(member, permission) {
    if (member.permission === permission) return Promise.resolve();
    const previous = member.permission;
    member.permission = permission;
    return withBusy(member.user_id, async () => {
      try {
        await updateUserPermission(projectId.value, member.user_id, {
          permission,
        });
        messages.addMessage(
          'projectSettings.members.permission_updated',
          'success'
        );
      } catch (err) {
        reportClientError('Error updating member permission', err);
        member.permission = previous;
        messages.addMessage(
          apiErrorMessage(
            err,
            translate,
            translate('projectSettings.members.permission_update_error')
          ),
          'error'
        );
      }
    });
  }

  function setProtocolManager(member, enabled) {
    return withBusy(member.user_id, async () => {
      try {
        if (enabled)
          await grantProtocolManager(projectId.value, member.user_id);
        else await revokeProtocolManager(projectId.value, member.user_id);
        const capabilities = new Set(member.capabilities ?? []);
        if (enabled) capabilities.add(PROTOCOL_MANAGER);
        else capabilities.delete(PROTOCOL_MANAGER);
        member.capabilities = [...capabilities];
        messages.addMessage(
          'projectSettings.members.capability_updated',
          'success'
        );
      } catch (err) {
        reportClientError('Error updating member capability', err);
        messages.addMessage(
          apiErrorMessage(
            err,
            translate,
            translate('projectSettings.members.capability_update_error')
          ),
          'error'
        );
      }
    });
  }

  async function add({ userId, permission }) {
    await addUserToProject(projectId.value, {
      user_id: Number(userId),
      permission,
    });
    messages.addMessage('projectSettings.members.user_added', 'success');
    await load();
  }

  async function remove(member) {
    removing.value = true;
    try {
      await removeUserFromProject(projectId.value, member.user_id);
      messages.addMessage('projectSettings.members.user_removed', 'success');
      await load();
    } catch (err) {
      reportClientError('Error removing project member', err);
      messages.addMessage(
        apiErrorMessage(
          err,
          translate,
          translate('projectSettings.members.remove_error')
        ),
        'error'
      );
    } finally {
      removing.value = false;
    }
  }

  return {
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
  };
}

export function isProtocolManager(member) {
  return Boolean(member.capabilities?.includes(PROTOCOL_MANAGER));
}
