import { ref, toValue } from 'vue';

export function useUsernameProfileEditor({ profile, updateProfile, emit }) {
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
        text: "Le nom d'utilisateur ne peut pas être vide",
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
        text: "Nom d'utilisateur mis à jour avec succès",
        type: 'success',
      });
      emit('profile-updated');
      editUsernameMode.value = false;
      return true;
    } catch (error) {
      let errorMessage = "Erreur lors de la mise à jour du nom d'utilisateur";
      if (error.response?.data?.detail?.includes('already taken')) {
        errorMessage = "Ce nom d'utilisateur est déjà pris";
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      emit('show-message', { text: errorMessage, type: 'error' });
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
