import { computed, onScopeDispose, ref, toValue } from 'vue';

export function useAddressProfileEditor({
  profile,
  updateAddress,
  location,
  emit,
  translate: t,
}) {
  const {
    getCountries,
    validateCity,
    validatePostalCode,
    validatePostalCodeInCity,
    validateStreetInCity,
    validateStreetName,
  } = location;

  // Address editing
  const editAddressMode = ref(false);
  const editedAddress = ref({
    streetName: '',
    streetNumber: '',
    addressLine2: '',
    cityName: '',
    postalCode: '',
    countryId: '',
  });
  const savingAddress = ref(false);
  const countries = ref([]);
  const countryOptions = computed(() =>
    countries.value.map((country) => ({
      value: country.country_id,
      label: country.country_name,
    }))
  );
  const addressValidation = ref({
    city: { isValid: null, message: '', loading: false },
    postalCode: { isValid: null, message: '', loading: false },
    streetName: { isValid: null, message: '' },
    streetInCity: { isValid: null, message: '', loading: false },
    postalCodeInCity: { isValid: null, message: '', loading: false },
  });

  // Validation timeouts
  let cityValidationTimeout = null;
  let streetValidationTimeout = null;
  let postalCodeValidationTimeout = null;

  // Computed properties for validation messages
  const cityValidationMessage = computed(() => {
    if (addressValidation.value.city.loading) {
      return { type: 'info', text: t('register.validating_city') };
    }
    if (addressValidation.value.city.isValid === false) {
      return { type: 'error', text: addressValidation.value.city.message };
    }
    if (
      addressValidation.value.city.isValid === true &&
      addressValidation.value.city.message
    ) {
      return { type: 'success', text: addressValidation.value.city.message };
    }
    return null;
  });

  const streetValidationMessage = computed(() => {
    if (addressValidation.value.streetInCity.loading) {
      return { type: 'info', text: t('register.validating_street_in_city') };
    }
    if (addressValidation.value.streetInCity.isValid === false) {
      return {
        type: 'warning',
        text: addressValidation.value.streetInCity.message,
      };
    }
    if (addressValidation.value.streetInCity.isValid === true) {
      return {
        type: 'success',
        text: addressValidation.value.streetInCity.message,
      };
    }
    if (addressValidation.value.streetName.isValid === false) {
      return {
        type: 'error',
        text: addressValidation.value.streetName.message,
      };
    }
    if (
      addressValidation.value.streetName.isValid === true &&
      addressValidation.value.streetName.message
    ) {
      return {
        type: 'success',
        text: addressValidation.value.streetName.message,
      };
    }
    return null;
  });

  const postalCodeValidationMessage = computed(() => {
    if (addressValidation.value.postalCode.loading) {
      return { type: 'info', text: t('register.validating_postal_code') };
    }
    if (addressValidation.value.postalCodeInCity.loading) {
      return {
        type: 'info',
        text: t('register.validating_postal_code_in_city'),
      };
    }
    if (addressValidation.value.postalCodeInCity.isValid === false) {
      return {
        type: 'warning',
        text: addressValidation.value.postalCodeInCity.message,
      };
    }
    if (addressValidation.value.postalCodeInCity.isValid === true) {
      return {
        type: 'success',
        text: addressValidation.value.postalCodeInCity.message,
      };
    }
    if (addressValidation.value.postalCode.isValid === false) {
      return {
        type: 'error',
        text: addressValidation.value.postalCode.message,
      };
    }
    if (
      addressValidation.value.postalCode.isValid === true &&
      addressValidation.value.postalCode.message
    ) {
      return {
        type: 'success',
        text: addressValidation.value.postalCode.message,
      };
    }
    return null;
  });

  // Load countries when component mounts
  const loadCountries = async () => {
    try {
      const result = await getCountries();
      if (result.success) {
        countries.value = result.data;
      }
    } catch (error) {
      console.error('Error loading countries:', error);
    }
  };

  // Address validation functions (matching RegisterPage.vue)
  async function validateCityField() {
    if (!editedAddress.value.cityName || !editedAddress.value.countryId) {
      const message = editedAddress.value.cityName
        ? t('register.country_required')
        : t('register.city_required');
      addressValidation.value.city = {
        isValid: false,
        message,
        loading: false,
      };
      return;
    }

    addressValidation.value.city.loading = true;

    try {
      const result = await validateCity(
        editedAddress.value.cityName,
        editedAddress.value.countryId
      );

      await handleCityValidationResult(result);
    } catch (error) {
      console.error('Error validating city:', error);
      addressValidation.value.city = {
        isValid: false,
        message: t('register.city_validation_error'),
        loading: false,
      };
    }
  }

  async function handleCityValidationResult(result) {
    if (!result.success) {
      addressValidation.value.city = {
        isValid: false,
        message: t('register.city_validation_error'),
        loading: false,
      };
      return;
    }

    const message = result.data.isValid
      ? t('register.city_valid_in_country')
      : result.data.message || t('register.city_not_found_in_country');

    addressValidation.value.city = {
      isValid: result.data.isValid,
      message,
      loading: false,
    };

    if (result.data.isValid) {
      await performCrossValidations();
    } else {
      resetCrossValidations();
    }
  }

  async function performCrossValidations() {
    if (editedAddress.value.streetName) {
      await validateStreetInCityField();
    }
    if (editedAddress.value.postalCode) {
      await validatePostalCodeInCityField();
    }
  }

  function resetCrossValidations() {
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
  }

  async function validatePostalCodeField() {
    if (!editedAddress.value.postalCode || !editedAddress.value.countryId) {
      addressValidation.value.postalCode = {
        isValid: false,
        message: t('register.postal_code_required'),
        loading: false,
      };
      return;
    }

    addressValidation.value.postalCode.loading = true;

    try {
      const result = await validatePostalCode(
        editedAddress.value.postalCode,
        editedAddress.value.countryId
      );

      if (result.success) {
        const isFormatValid = result.data.isValid;

        addressValidation.value.postalCode = {
          isValid: isFormatValid,
          message: isFormatValid ? '' : result.data.message,
          loading: false,
        };

        if (
          isFormatValid &&
          editedAddress.value.cityName &&
          addressValidation.value.city.isValid === true
        ) {
          await validatePostalCodeInCityField();
        } else {
          addressValidation.value.postalCodeInCity = {
            isValid: null,
            message: '',
            loading: false,
          };
        }
      } else {
        addressValidation.value.postalCode = {
          isValid: false,
          message: t('register.postal_code_validation_error'),
          loading: false,
        };
      }
    } catch (error) {
      console.error('Error validating postal code:', error);
      addressValidation.value.postalCode = {
        isValid: false,
        message: t('register.postal_code_validation_error'),
        loading: false,
      };
    }
  }

  async function validateStreetNameField() {
    const result = validateStreetName(editedAddress.value.streetName);

    if (!result.isValid) {
      addressValidation.value.streetName = {
        isValid: false,
        message: result.message,
      };
      addressValidation.value.streetInCity = {
        isValid: null,
        message: '',
        loading: false,
      };
      return;
    }

    addressValidation.value.streetName = {
      isValid: true,
      message: '',
    };

    if (
      editedAddress.value.cityName &&
      editedAddress.value.countryId &&
      addressValidation.value.city.isValid === true
    ) {
      await validateStreetInCityField();
    } else {
      addressValidation.value.streetInCity = {
        isValid: null,
        message: '',
        loading: false,
      };
    }
  }

  async function validateStreetInCityField() {
    if (
      !editedAddress.value.streetName ||
      !editedAddress.value.cityName ||
      !editedAddress.value.countryId
    ) {
      addressValidation.value.streetInCity = {
        isValid: null,
        message: '',
        loading: false,
      };
      return;
    }

    addressValidation.value.streetInCity.loading = true;

    try {
      const result = await validateStreetInCity(
        editedAddress.value.streetName,
        editedAddress.value.cityName,
        editedAddress.value.countryId
      );

      if (result.success) {
        addressValidation.value.streetInCity = {
          isValid: result.data.isValid,
          message: result.data.message,
          loading: false,
          suggestions: result.data.suggestions || [],
        };
      } else {
        addressValidation.value.streetInCity = {
          isValid: false,
          message: t('register.street_validation_error'),
          loading: false,
        };
      }
    } catch (error) {
      console.error('Error validating street in city:', error);
      addressValidation.value.streetInCity = {
        isValid: false,
        message: t('register.street_validation_error'),
        loading: false,
      };
    }
  }

  async function validatePostalCodeInCityField() {
    if (
      !editedAddress.value.postalCode ||
      !editedAddress.value.cityName ||
      !editedAddress.value.countryId
    ) {
      addressValidation.value.postalCodeInCity = {
        isValid: null,
        message: '',
        loading: false,
      };
      return;
    }

    addressValidation.value.postalCodeInCity.loading = true;

    try {
      const result = await validatePostalCodeInCity(
        editedAddress.value.postalCode,
        editedAddress.value.cityName,
        editedAddress.value.countryId
      );

      if (result.success) {
        addressValidation.value.postalCodeInCity = {
          isValid: result.data.isValid,
          message: result.data.message,
          loading: false,
          suggestions: result.data.suggestions || [],
        };
      } else {
        addressValidation.value.postalCodeInCity = {
          isValid: false,
          message: t('register.postal_code_city_validation_error'),
          loading: false,
        };
      }
    } catch (error) {
      console.error('Error validating postal code in city:', error);
      addressValidation.value.postalCodeInCity = {
        isValid: false,
        message: t('register.postal_code_city_validation_error'),
        loading: false,
      };
    }
  }

  // Debounced validation handlers
  const onCityChange = async () => {
    addressValidation.value.city = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };

    clearTimeout(cityValidationTimeout);
    cityValidationTimeout = setTimeout(async () => {
      if (editedAddress.value.cityName && editedAddress.value.countryId) {
        await validateCityField();
      }
    }, 500);
  };

  const onStreetNameChange = async () => {
    addressValidation.value.streetName = { isValid: null, message: '' };
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };

    clearTimeout(streetValidationTimeout);
    streetValidationTimeout = setTimeout(async () => {
      if (editedAddress.value.streetName) {
        await validateStreetNameField();
      }
    }, 500);
  };

  const onPostalCodeChange = async () => {
    addressValidation.value.postalCode = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };

    clearTimeout(postalCodeValidationTimeout);
    postalCodeValidationTimeout = setTimeout(async () => {
      if (editedAddress.value.postalCode && editedAddress.value.countryId) {
        await validatePostalCodeField();
      }
    }, 500);
  };

  const onCountryChange = () => {
    addressValidation.value.city = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.postalCode = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.streetInCity = {
      isValid: null,
      message: '',
      loading: false,
    };
    addressValidation.value.postalCodeInCity = {
      isValid: null,
      message: '',
      loading: false,
    };

    if (editedAddress.value.cityName) {
      editedAddress.value.cityName = '';
    }
    if (editedAddress.value.postalCode) {
      editedAddress.value.postalCode = '';
    }
  };

  // Address editing functions
  async function startEditAddress() {
    editAddressMode.value = true;
    editedAddress.value = {
      streetName: toValue(profile)?.address?.street_name || '',
      streetNumber: toValue(profile)?.address?.street_number || '',
      addressLine2: toValue(profile)?.address?.address_line_2 || '',
      cityName: toValue(profile)?.address?.city?.name || '',
      postalCode: toValue(profile)?.address?.postal_code || '',
      countryId: toValue(profile)?.address?.city?.country || '',
    };

    // Reset validations
    addressValidation.value = {
      city: { isValid: null, message: '', loading: false },
      postalCode: { isValid: null, message: '', loading: false },
      streetName: { isValid: null, message: '' },
      streetInCity: { isValid: null, message: '', loading: false },
      postalCodeInCity: { isValid: null, message: '', loading: false },
    };

    // Load countries if not already loaded
    if (countries.value.length === 0) {
      await loadCountries();
    }
  }

  function cancelEditAddress() {
    editAddressMode.value = false;
    editedAddress.value = {
      streetName: toValue(profile)?.address?.street_name || '',
      streetNumber: toValue(profile)?.address?.street_number || '',
      addressLine2: toValue(profile)?.address?.address_line_2 || '',
      cityName: toValue(profile)?.address?.city?.name || '',
      postalCode: toValue(profile)?.address?.postal_code || '',
      countryId: toValue(profile)?.address?.city?.country || '',
    };

    addressValidation.value = {
      city: { isValid: null, message: '', loading: false },
      postalCode: { isValid: null, message: '', loading: false },
      streetName: { isValid: null, message: '' },
      streetInCity: { isValid: null, message: '', loading: false },
      postalCodeInCity: { isValid: null, message: '', loading: false },
    };
  }

  async function saveAddress() {
    if (savingAddress.value) return;

    // Validate required fields
    if (!editedAddress.value.streetName) {
      emit('show-message', { text: 'Le nom de rue est requis', type: 'error' });
      return;
    }

    if (!editedAddress.value.cityName) {
      emit('show-message', {
        text: 'Le nom de ville est requis',
        type: 'error',
      });
      return;
    }

    if (!editedAddress.value.postalCode) {
      emit('show-message', {
        text: 'Le code postal est requis',
        type: 'error',
      });
      return;
    }

    if (!editedAddress.value.countryId) {
      emit('show-message', { text: 'Le pays est requis', type: 'error' });
      return;
    }

    // Check validation states
    if (
      addressValidation.value.city.isValid === false ||
      addressValidation.value.postalCode.isValid === false ||
      addressValidation.value.streetName.isValid === false
    ) {
      emit('show-message', {
        text: 'Veuillez corriger les erreurs de validation avant de sauvegarder',
        type: 'error',
      });
      return;
    }

    // Check cross-validations
    if (
      addressValidation.value.streetInCity.isValid === false ||
      addressValidation.value.postalCodeInCity.isValid === false
    ) {
      emit('show-message', {
        text: "L'adresse ne semble pas correspondre. Veuillez vérifier les informations.",
        type: 'warning',
      });
      // Allow saving but with warning - user choice
    }

    try {
      savingAddress.value = true;

      const selectedCountry = countries.value.find(
        (country) => country.country_id === editedAddress.value.countryId
      );

      // Format address data according to backend schema
      const addressData = {
        street_name: editedAddress.value.streetName,
        street_number: editedAddress.value.streetNumber || null,
        city_name: editedAddress.value.cityName,
        country_code: editedAddress.value.countryId,
        country_name: selectedCountry?.country_name || '',
        postal_code: editedAddress.value.postalCode,
        address_line_2: editedAddress.value.addressLine2 || null,
      };

      const response = await updateAddress(addressData);

      if (response.data) {
        emit('show-message', {
          text: 'Adresse mise à jour avec succès',
          type: 'success',
        });
        emit('profile-updated');
        editAddressMode.value = false;
      }
    } catch (error) {
      console.error('Error updating address:', error);
      let errorMessage = "Erreur lors de la mise à jour de l'adresse";

      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.status === 400) {
        errorMessage =
          "Données d'adresse invalides. Veuillez vérifier les informations saisies.";
      } else if (error.response?.status === 500) {
        errorMessage =
          "Erreur serveur lors de la mise à jour de l'adresse. Veuillez réessayer.";
      }

      emit('show-message', { text: errorMessage, type: 'error' });
    } finally {
      savingAddress.value = false;
    }
  }

  function syncAddress() {
    if (editAddressMode.value) return;
    const current = toValue(profile);
    editedAddress.value = {
      streetName: current?.address?.street_name || '',
      streetNumber: current?.address?.street_number || '',
      addressLine2: current?.address?.address_line_2 || '',
      cityName: current?.address?.city?.name || '',
      postalCode: current?.address?.postal_code || '',
      countryId: current?.address?.city?.country || '',
    };
  }

  onScopeDispose(() => {
    clearTimeout(cityValidationTimeout);
    clearTimeout(streetValidationTimeout);
    clearTimeout(postalCodeValidationTimeout);
  });

  return {
    editAddressMode,
    editedAddress,
    savingAddress,
    countries,
    countryOptions,
    addressValidation,
    cityValidationMessage,
    streetValidationMessage,
    postalCodeValidationMessage,
    syncAddress,
    validateCityField,
    validatePostalCodeField,
    validateStreetNameField,
    onCityChange,
    onStreetNameChange,
    onPostalCodeChange,
    onCountryChange,
    startEditAddress,
    cancelEditAddress,
    saveAddress,
  };
}
