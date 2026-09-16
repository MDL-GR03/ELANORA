import { computed, ref, toValue } from 'vue';

import { useAddressVerification } from '@/composables/useAddressVerification';
import { addressPayload } from '@/composables/useInvitationRegistration';
import { reportClientError } from '@/utils/errorDiagnostics';

/** The draft address for a profile, in the shape the form edits. */
function draftFrom(profile) {
  const address = profile?.address;
  return {
    streetName: address?.street_name || '',
    streetNumber: address?.street_number || '',
    addressLine2: address?.address_line_2 || '',
    cityName: address?.city?.name || '',
    postalCode: address?.postal_code || '',
    countryId: address?.city?.country || '',
  };
}

const REQUIRED_FIELDS = [
  ['streetName', 'register.street_name_required'],
  ['cityName', 'register.city_required'],
  ['postalCode', 'register.postal_code_required'],
  ['countryId', 'register.country_required'],
];

/**
 * Edit the address on a researcher's profile.
 *
 * The checks against the location service are the ones registration uses. A
 * street or postal code the service cannot place in the city is saved after a
 * warning, because a real address can be missing from OpenStreetMap; a value
 * that fails its own format is not.
 */
export function useAddressProfileEditor({
  profile,
  updateAddress,
  location,
  emit,
  translate: t,
}) {
  const editAddressMode = ref(false);
  const editedAddress = ref(draftFrom(toValue(profile)));
  const savingAddress = ref(false);
  const countries = ref([]);
  const countryOptions = computed(() =>
    countries.value.map((country) => ({
      value: country.country_id,
      label: country.country_name,
    }))
  );

  const verification = useAddressVerification({
    address: editedAddress,
    translate: t,
    locationApi: location,
    reportError: reportClientError,
  });
  const addressValidation = verification.validation;

  function resetDraft() {
    editedAddress.value = draftFrom(toValue(profile));
    addressValidation.value = {
      city: { isValid: null, message: '', loading: false },
      postalCode: { isValid: null, message: '', loading: false },
      streetName: { isValid: null, message: '' },
      streetInCity: { isValid: null, message: '', loading: false },
      postalCodeInCity: { isValid: null, message: '', loading: false },
    };
  }

  async function loadCountries() {
    try {
      const result = await location.getCountries();
      if (result.success) countries.value = result.data;
    } catch (error) {
      reportClientError('Error loading countries', error);
    }
  }

  async function startEditAddress() {
    editAddressMode.value = true;
    resetDraft();
    if (countries.value.length === 0) await loadCountries();
  }

  function cancelEditAddress() {
    editAddressMode.value = false;
    resetDraft();
  }

  function syncAddress() {
    if (!editAddressMode.value)
      editedAddress.value = draftFrom(toValue(profile));
  }

  const notify = (key, type) => emit('show-message', { text: t(key), type });

  async function saveAddress() {
    if (savingAddress.value) return;

    const missing = REQUIRED_FIELDS.find(
      ([field]) => !editedAddress.value[field]
    );
    if (missing) {
      notify(missing[1], 'error');
      return;
    }

    const state = addressValidation.value;
    if (
      state.city.isValid === false ||
      state.postalCode.isValid === false ||
      state.streetName.isValid === false
    ) {
      notify('profile.address.fix_errors', 'error');
      return;
    }
    if (
      state.streetInCity.isValid === false ||
      state.postalCodeInCity.isValid === false
    ) {
      notify('profile.address.unconfirmed', 'warning');
    }

    try {
      savingAddress.value = true;
      const response = await updateAddress(
        addressPayload(editedAddress.value, countries.value)
      );
      if (response.data) {
        notify('profile.address.saved', 'success');
        emit('profile-updated');
        editAddressMode.value = false;
      }
    } catch (error) {
      reportClientError('Error updating address', error);
      emit('show-message', {
        text: error.response?.data?.detail || t('profile.address.save_failed'),
        type: 'error',
      });
    } finally {
      savingAddress.value = false;
    }
  }

  return {
    editAddressMode,
    editedAddress,
    savingAddress,
    countries,
    countryOptions,
    addressValidation,
    cityValidationMessage: verification.cityMessage,
    streetValidationMessage: verification.streetMessage,
    postalCodeValidationMessage: verification.postalCodeMessage,
    syncAddress,
    validateCityField: verification.validateCity,
    validatePostalCodeField: verification.validatePostalCode,
    validateStreetNameField: verification.validateStreetName,
    onCityChange: verification.onCityChange,
    onStreetNameChange: verification.onStreetNameChange,
    onPostalCodeChange: verification.onPostalCodeChange,
    onCountryChange: verification.onCountryChange,
    startEditAddress,
    cancelEditAddress,
    saveAddress,
  };
}
