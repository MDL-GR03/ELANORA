import { computed, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { useUsernameProfileEditor } from './useUsernameProfileEditor';

function createEditor() {
  const profile = ref({ username: 'researcher' });
  const updateProfile = vi.fn().mockResolvedValue({ data: { ok: true } });
  const emit = vi.fn();
  const editor = useUsernameProfileEditor({
    profile: computed(() => profile.value),
    updateProfile,
    emit,
    translate: (key) => `translated:${key}`,
  });
  return { profile, updateProfile, emit, editor };
}

describe('useUsernameProfileEditor', () => {
  it('synchronizes, starts, and cancels from the current profile', () => {
    const { profile, editor } = createEditor();
    editor.syncUsername();
    expect(editor.editedUsername.value).toBe('researcher');
    editor.startEditUsername();
    profile.value.username = 'updated-remotely';
    editor.editedUsername.value = 'draft';
    editor.cancelEditUsername();
    expect(editor.editedUsername.value).toBe('updated-remotely');
    expect(editor.editUsernameMode.value).toBe(false);
  });

  it('rejects blank and unchanged usernames without an API request', async () => {
    const { updateProfile, emit, editor } = createEditor();
    editor.startEditUsername();
    editor.editedUsername.value = '   ';
    await expect(editor.saveUsername()).resolves.toBe(false);
    expect(updateProfile).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith(
      'show-message',
      expect.objectContaining({ type: 'error' })
    );

    editor.editedUsername.value = 'researcher';
    await expect(editor.saveUsername()).resolves.toBe(false);
    expect(updateProfile).not.toHaveBeenCalled();
    expect(editor.editUsernameMode.value).toBe(false);
  });

  it('trims and saves a changed username', async () => {
    const { updateProfile, emit, editor } = createEditor();
    editor.startEditUsername();
    editor.editedUsername.value = '  new_researcher  ';

    await expect(editor.saveUsername()).resolves.toBe(true);
    expect(updateProfile).toHaveBeenCalledWith({ username: 'new_researcher' });
    expect(emit).toHaveBeenCalledWith('profile-updated');
    expect(editor.savingUsername.value).toBe(false);
  });

  it('restores the current username after a duplicate response', async () => {
    const { updateProfile, emit, editor } = createEditor();
    updateProfile.mockRejectedValue({
      response: {
        data: {
          detail: 'This username is already taken',
          code: 'username_taken',
        },
      },
    });
    editor.startEditUsername();
    editor.editedUsername.value = 'duplicate';

    await expect(editor.saveUsername()).resolves.toBe(false);
    expect(editor.editedUsername.value).toBe('researcher');
    expect(emit).toHaveBeenCalledWith('show-message', {
      text: 'translated:apiErrors.username_taken',
      type: 'error',
    });
    expect(editor.savingUsername.value).toBe(false);
  });
});
