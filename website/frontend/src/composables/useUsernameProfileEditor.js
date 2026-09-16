import { ref, toValue } from 'vue';

import { apiErrorMessage } from '@/utils/apiError';

export function useUsernameProfileEditor({
  profile,
  updateProfile,
  emit,
  translate,
}) {
  const editUsernameMode = ref(false);
  const editedUsername = ref('');
  const savingUsername = ref(false);

  const currentUsername = () => toValue(profile)?.username || '';

  function syncUsername() {
    if (!editUsernameMode.value) editedUsername.value = currentUsername();
  }

  function startEditUsername() {
    editUsernameMode.value = true;
    editedUsername.value = currentUsername();
  }

  function cancelEditUsername() {
    editUsernameMode.value = false;
    editedUsername.value = currentUsername();
  }

  async function saveUsername() {
    if (savingUsername.value) return false;
    const username = editedUsername.value.trim();
    if (!username) {
      emit('show-message', {
        text: translate('register.username_required'),
        type: 'error',
      });
      return false;
    }
    if (username === currentUsername()) {
      editUsernameMode.value = false;
      return false;
    }

    try {
      savingUsername.value = true;
      const response = await updateProfile({ username });
      if (!response.data) return false;
      emit('show-message', {
        text: translate('profile.username.saved'),
        type: 'success',
      });
      emit('profile-updated');
      editUsernameMode.value = false;
      return true;
    } catch (error) {
      emit('show-message', {
        text: apiErrorMessage(
          error,
          translate,
          translate('profile.username.save_failed')
        ),
        type: 'error',
      });
      editedUsername.value = currentUsername();
      return false;
    } finally {
      savingUsername.value = false;
    }
  }

  return {
    editUsernameMode,
    editedUsername,
    savingUsername,
    syncUsername,
    startEditUsername,
    cancelEditUsername,
    saveUsername,
  };
}
