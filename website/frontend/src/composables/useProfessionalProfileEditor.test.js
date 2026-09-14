import { computed, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { useProfessionalProfileEditor } from './useProfessionalProfileEditor';

function createEditor(profileValue = {}) {
  const profile = ref({
    affiliation: 'University',
    department: 'Linguistics',
    ...profileValue,
  });
  const updateProfile = vi.fn().mockResolvedValue({ data: { ok: true } });
  const emit = vi.fn();
  const editor = useProfessionalProfileEditor({
    profile: computed(() => profile.value),
    updateProfile,
    emit,
    translate: (key) => `translated:${key}`,
  });
  return { editor, updateProfile, emit };
}

describe('useProfessionalProfileEditor', () => {
  it('initializes and cancels editing from the current profile', () => {
    const { editor } = createEditor();

    editor.startEditProfessional();
    expect(editor.editProfessionalMode.value).toBe(true);
    expect(editor.editedProfessional.value).toEqual({
      affiliation: 'University',
      department: 'Linguistics',
    });

    editor.editedProfessional.value.affiliation = 'Changed';
    editor.cancelEditProfessional();
    expect(editor.editProfessionalMode.value).toBe(false);
    expect(editor.editedProfessional.value.affiliation).toBe('University');
  });

  it('rejects invalid fields without calling the API', async () => {
    const { editor, updateProfile, emit } = createEditor();
    editor.startEditProfessional();
    editor.editedProfessional.value.affiliation = '';

    await expect(editor.saveProfessional()).resolves.toBe(false);
    expect(updateProfile).not.toHaveBeenCalled();
    expect(editor.professionalValidation.value.affiliation).toEqual({
      isValid: false,
      message: 'translated:register.affiliation_required',
    });
    expect(emit).toHaveBeenCalledWith(
      'show-message',
      expect.objectContaining({ type: 'error' })
    );
  });

  it('closes unchanged drafts without calling the API', async () => {
    const { editor, updateProfile, emit } = createEditor();
    editor.startEditProfessional();

    await expect(editor.saveProfessional()).resolves.toBe(false);
    expect(updateProfile).not.toHaveBeenCalled();
    expect(editor.editProfessionalMode.value).toBe(false);
    expect(emit).toHaveBeenCalledWith(
      'show-message',
      expect.objectContaining({ type: 'info' })
    );
  });

  it('sends only changed fields and emits completion', async () => {
    const { editor, updateProfile, emit } = createEditor();
    editor.startEditProfessional();
    editor.editedProfessional.value.department = 'Language Sciences';

    await expect(editor.saveProfessional()).resolves.toBe(true);
    expect(updateProfile).toHaveBeenCalledWith({
      department: 'Language Sciences',
    });
    expect(emit).toHaveBeenCalledWith('profile-updated');
    expect(editor.savingProfessional.value).toBe(false);
    expect(editor.editProfessionalMode.value).toBe(false);
  });

  it('surfaces API details and always releases the saving state', async () => {
    const { editor, updateProfile, emit } = createEditor();
    updateProfile.mockRejectedValue({
      response: { status: 400, data: { detail: 'Rejected by server' } },
    });
    editor.startEditProfessional();
    editor.editedProfessional.value.department = 'Language Sciences';

    await expect(editor.saveProfessional()).resolves.toBe(false);
    expect(emit).toHaveBeenCalledWith('show-message', {
      text: 'Rejected by server',
      type: 'error',
    });
    expect(editor.savingProfessional.value).toBe(false);
  });
});
