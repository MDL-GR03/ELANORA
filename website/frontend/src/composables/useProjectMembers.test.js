import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  actingProjectRole,
  assignablePermissions,
  canManageMember,
  useProjectMembers,
} from './useProjectMembers';

const api = vi.hoisted(() => ({
  addUserToProject: vi.fn(),
  getProjectUsers: vi.fn(),
  grantProtocolManager: vi.fn(),
  removeUserFromProject: vi.fn(),
  revokeProtocolManager: vi.fn(),
  updateUserPermission: vi.fn(),
}));
vi.mock('@/api/service/projectAssociationService', () => api);
vi.mock('@/utils/errorDiagnostics', () => ({ reportClientError: vi.fn() }));

const member = (user_id, permission, capabilities = []) => ({
  user_id,
  username: `user${user_id}`,
  permission,
  capabilities,
});

describe('project member rules', () => {
  it('lets an institution administrator act as owner', () => {
    expect(actingProjectRole({ user_id: 1, role: 'admin' }, [])).toBe('owner');
    expect(
      actingProjectRole({ user_id: 2, role: 'user' }, [member(2, 'write')])
    ).toBe('write');
    expect(actingProjectRole(null, [])).toBeNull();
  });

  it('keeps the owner out of reach and admins out of reach of other admins', () => {
    expect(canManageMember('owner', member(3, 'owner'))).toBe(false);
    expect(canManageMember('owner', member(3, 'admin'))).toBe(true);
    expect(canManageMember('admin', member(3, 'admin'))).toBe(false);
    expect(canManageMember('admin', member(3, 'read'))).toBe(true);
    expect(canManageMember('write', member(3, 'read'))).toBe(false);
    expect(assignablePermissions('admin')).toEqual(['read', 'write']);
    expect(assignablePermissions('read')).toEqual([]);
  });
});

describe('useProjectMembers', () => {
  let messages;

  function setup() {
    messages = { addMessage: vi.fn() };
    return useProjectMembers({
      projectId: ref(42),
      account: ref({ user_id: 1, role: 'user' }),
      messages,
      translate: (key) => `t:${key}`,
    });
  }

  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.getProjectUsers.mockResolvedValue({
      data: { users: [member(1, 'admin'), member(2, 'read')] },
    });
  });

  it('derives the acting role from the loaded members', async () => {
    const members = setup();
    expect(members.canAddMembers.value).toBe(false);
    await members.load();
    expect(members.role.value).toBe('admin');
    expect(members.canAddMembers.value).toBe(true);
  });

  it('restores the previous permission when the change is refused', async () => {
    api.updateUserPermission.mockRejectedValue({
      response: { data: { code: 'project_admin_change_forbidden' } },
    });
    const members = setup();
    await members.load();
    const target = members.members.value[1];

    await members.changePermission(target, 'write');

    expect(target.permission).toBe('read');
    expect(members.updating.value.size).toBe(0);
    expect(messages.addMessage).toHaveBeenCalledWith(
      't:apiErrors.project_admin_change_forbidden',
      'error'
    );
  });

  it('grants and revokes protocol management', async () => {
    const members = setup();
    await members.load();
    const target = members.members.value[1];

    await members.setProtocolManager(target, true);
    expect(api.grantProtocolManager).toHaveBeenCalledWith(42, 2);
    expect(target.capabilities).toEqual(['manage_protocols']);

    await members.setProtocolManager(target, false);
    expect(api.revokeProtocolManager).toHaveBeenCalledWith(42, 2);
    expect(target.capabilities).toEqual([]);
  });

  it('keeps capabilities unchanged when a grant fails', async () => {
    api.grantProtocolManager.mockRejectedValue(new Error('down'));
    const members = setup();
    await members.load();
    const target = members.members.value[1];

    await members.setProtocolManager(target, true);

    expect(target.capabilities).toEqual([]);
    expect(messages.addMessage).toHaveBeenCalledWith(
      't:projectSettings.members.capability_update_error',
      'error'
    );
  });

  it('reloads after adding or removing a member', async () => {
    const members = setup();
    await members.add({ userId: '7', permission: 'write' });
    expect(api.addUserToProject).toHaveBeenCalledWith(42, {
      user_id: 7,
      permission: 'write',
    });
    await members.remove(member(2, 'read'));
    expect(api.removeUserFromProject).toHaveBeenCalledWith(42, 2);
    expect(api.getProjectUsers).toHaveBeenCalledTimes(2);
    expect(members.removing.value).toBe(false);
  });
});
