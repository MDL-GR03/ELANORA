import { ref, toValue } from 'vue';

const emptyValidation = () => ({
  affiliation: { isValid: null, message: '' },
  department: { isValid: null, message: '' },
});

export function useProfessionalProfileEditor({
  profile,
  updateProfile,
  emit,
  translate,
}) {
  const editProfessionalMode = ref(false);
  const editedProfessional = ref({ affiliation: '', department: '' });
  const savingProfessional = ref(false);
  const professionalValidation = ref(emptyValidation());

  const resetDraft = () => {
    const current = toValue(profile);
    editedProfessional.value = {
      affiliation: current?.affiliation || '',
      department: current?.department || '',
    };
    professionalValidation.value = emptyValidation();
  };

  function validateProfessionalField(fieldName) {
    const value = editedProfessional.value[fieldName];
    const requiredKey =
      fieldName === 'affiliation'
        ? 'register.affiliation_required'
        : 'register.department_required';
    const label = fieldName === 'affiliation' ? 'Affiliation' : 'Department';
    let validation = { isValid: true, message: '' };
    if (!value) {
      validation = { isValid: false, message: translate(requiredKey) };
    } else if (value.length < 2) {
      validation = {
        isValid: false,
        message: `${label} must be at least 2 characters`,
      };
    } else if (value.length > 100) {
      validation = {
        isValid: false,
        message: `${label} must be less than 100 characters`,
      };
    }
    professionalValidation.value[fieldName] = validation;
    return validation.isValid;
  }

  function startEditProfessional() {
    editProfessionalMode.value = true;
    resetDraft();
  }

  function cancelEditProfessional() {
    editProfessionalMode.value = false;
    resetDraft();
  }

  async function saveProfessional() {
    if (savingProfessional.value) return false;
    validateProfessionalField('affiliation');
    validateProfessionalField('department');
    if (
      professionalValidation.value.affiliation.isValid === false ||
      professionalValidation.value.department.isValid === false
    ) {
      emit('show-message', {
        text: 'Veuillez corriger les erreurs avant de sauvegarder',
        type: 'error',
      });
      return false;
    }

    const current = toValue(profile);
    const profileData = {};
    if (editedProfessional.value.affiliation !== current?.affiliation) {
      profileData.affiliation = editedProfessional.value.affiliation;
    }
    if (editedProfessional.value.department !== current?.department) {
      profileData.department = editedProfessional.value.department;
    }
    if (Object.keys(profileData).length === 0) {
      emit('show-message', {
        text: 'Aucune modification détectée',
        type: 'info',
      });
      editProfessionalMode.value = false;
      return false;
    }

    try {
      savingProfessional.value = true;
      const response = await updateProfile(profileData);
      if (!response.data) return false;
      emit('show-message', {
        text: 'Informations professionnelles mises à jour avec succès',
        type: 'success',
      });
      emit('profile-updated');
      editProfessionalMode.value = false;
      return true;
    } catch (error) {
      let errorMessage =
        'Erreur lors de la mise à jour des informations professionnelles';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.status === 400) {
        errorMessage =
          'Données invalides. Veuillez vérifier les informations saisies.';
      }
      emit('show-message', { text: errorMessage, type: 'error' });
      return false;
    } finally {
      savingProfessional.value = false;
    }
  }

  return {
    editProfessionalMode,
    editedProfessional,
    savingProfessional,
    professionalValidation,
    validateProfessionalField,
    startEditProfessional,
    cancelEditProfessional,
    saveProfessional,
  };
}
