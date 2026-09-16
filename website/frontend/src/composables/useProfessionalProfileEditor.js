import { apiErrorMessage } from '@/utils/apiError';
import { ref, toValue } from 'vue';

import { validateRegistrationField } from '@/utils/registrationValidation';

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
    const message = validateRegistrationField(
      fieldName,
      editedProfessional.value,
      translate
    );
    professionalValidation.value[fieldName] = { isValid: !message, message };
    return !message;
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
        text: translate('profile.professional.fix_errors'),
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
        text: translate('profile.no_changes'),
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
        text: translate('profile.professional.saved'),
        type: 'success',
      });
      emit('profile-updated');
      editProfessionalMode.value = false;
      return true;
    } catch (error) {
      emit('show-message', {
        text: apiErrorMessage(
          error,
          translate,
          translate('profile.professional.save_failed')
        ),
        type: 'error',
      });
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
