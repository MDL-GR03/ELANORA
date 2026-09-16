import { computed, onScopeDispose, ref, toValue } from 'vue';

import { validateRegistrationField } from '@/utils/registrationValidation';

/** How long to wait after the last keystroke before asking the server. */
export const ADDRESS_VALIDATION_DELAY = 500;

const IDLE = () => ({ isValid: null, message: '', loading: false });

function idleState() {
  return {
    city: IDLE(),
    postalCode: IDLE(),
    streetName: { isValid: null, message: '' },
    streetInCity: IDLE(),
    postalCodeInCity: IDLE(),
  };
}

/**
 * Check an address against the location service while it is being typed.
 *
 * The city is checked against the country, then the street and the postal code
 * are checked against the city. A cross-check only runs once the city is known
 * to be real, and is cleared whenever the value it depended on changes, so the
 * form never shows a street confirmed against a city the researcher has since
 * replaced.
 */
export function useAddressVerification({
  address,
  translate,
  locationApi,
  reportError,
}) {
  const validation = ref(idleState());
  const timers = { city: null, street: null, postalCode: null };

  const current = () => toValue(address);

  function reset(...parts) {
    const blank = idleState();
    for (const part of parts) validation.value[part] = blank[part];
  }

  async function validateCity() {
    const { cityName, countryId } = current();
    if (!cityName || !countryId) {
      validation.value.city = {
        isValid: false,
        message: cityName
          ? translate('register.country_required')
          : translate('register.city_required'),
        loading: false,
      };
      return;
    }

    validation.value.city.loading = true;
    try {
      const result = await locationApi.validateCity(cityName, countryId);
      if (!result.success) {
        validation.value.city = {
          isValid: false,
          message: translate('register.city_validation_error'),
          loading: false,
        };
        return;
      }

      validation.value.city = {
        isValid: result.data.isValid,
        message: translate(
          result.data.isValid
            ? 'register.city_valid_in_country'
            : 'register.city_not_found_in_country'
        ),
        loading: false,
      };

      if (!result.data.isValid) {
        reset('streetInCity', 'postalCodeInCity');
        return;
      }
      if (current().streetName) await validateStreetInCity();
      if (current().postalCode) await validatePostalCodeInCity();
    } catch (error) {
      reportError('Error validating city', error);
      validation.value.city = {
        isValid: false,
        message: translate('register.city_validation_error'),
        loading: false,
      };
    }
  }

  async function validatePostalCode() {
    const { postalCode, countryId } = current();
    if (!postalCode || !countryId) {
      validation.value.postalCode = {
        isValid: false,
        message: translate('register.postal_code_required'),
        loading: false,
      };
      return;
    }

    validation.value.postalCode.loading = true;
    try {
      const result = await locationApi.validatePostalCode(
        postalCode,
        countryId
      );
      if (!result.success) {
        validation.value.postalCode = {
          isValid: false,
          message: translate('register.postal_code_validation_error'),
          loading: false,
        };
        return;
      }

      validation.value.postalCode = {
        isValid: result.data.isValid,
        message: result.data.isValid
          ? ''
          : translate('register.postal_code_invalid'),
        loading: false,
      };

      if (
        result.data.isValid &&
        current().cityName &&
        validation.value.city.isValid === true
      ) {
        await validatePostalCodeInCity();
      } else {
        reset('postalCodeInCity');
      }
    } catch (error) {
      reportError('Error validating postal code', error);
      validation.value.postalCode = {
        isValid: false,
        message: translate('register.postal_code_validation_error'),
        loading: false,
      };
    }
  }

  async function validateStreetName() {
    const message = validateRegistrationField(
      'streetName',
      { address: current() },
      translate
    );
    if (message) {
      validation.value.streetName = { isValid: false, message };
      reset('streetInCity');
      return;
    }

    validation.value.streetName = { isValid: true, message: '' };

    const { cityName, countryId } = current();
    if (cityName && countryId && validation.value.city.isValid === true) {
      await validateStreetInCity();
    } else {
      reset('streetInCity');
    }
  }

  async function validateStreetInCity() {
    const { streetName, cityName, countryId } = current();
    if (!streetName || !cityName || !countryId) {
      reset('streetInCity');
      return;
    }

    validation.value.streetInCity.loading = true;
    try {
      const result = await locationApi.validateStreetInCity(
        streetName,
        cityName,
        countryId
      );
      validation.value.streetInCity = result.success
        ? {
            isValid: result.data.isValid,
            message: translate(
              result.data.messageKey,
              result.data.messageParams
            ),
            loading: false,
            suggestions: result.data.suggestions || [],
          }
        : {
            isValid: false,
            message: translate('register.street_validation_error'),
            loading: false,
          };
    } catch (error) {
      reportError('Error validating street in city', error);
      validation.value.streetInCity = {
        isValid: false,
        message: translate('register.street_validation_error'),
        loading: false,
      };
    }
  }

  async function validatePostalCodeInCity() {
    const { postalCode, cityName, countryId } = current();
    if (!postalCode || !cityName || !countryId) {
      reset('postalCodeInCity');
      return;
    }

    validation.value.postalCodeInCity.loading = true;
    try {
      const result = await locationApi.validatePostalCodeInCity(
        postalCode,
        cityName,
        countryId
      );
      validation.value.postalCodeInCity = result.success
        ? {
            isValid: result.data.isValid,
            message: translate(
              result.data.messageKey,
              result.data.messageParams
            ),
            loading: false,
            suggestions: result.data.suggestions || [],
          }
        : {
            isValid: false,
            message: translate('register.postal_code_city_validation_error'),
            loading: false,
          };
    } catch (error) {
      reportError('Error validating postal code in city', error);
      validation.value.postalCodeInCity = {
        isValid: false,
        message: translate('register.postal_code_city_validation_error'),
        loading: false,
      };
    }
  }

  onScopeDispose(() => {
    Object.values(timers).forEach(clearTimeout);
  });

  function debounce(name, run) {
    clearTimeout(timers[name]);
    timers[name] = setTimeout(run, ADDRESS_VALIDATION_DELAY);
  }

  /** The country changed, so nothing checked against the old one still holds. */
  function onCountryChange() {
    validation.value = idleState();
    const addressFields = current();
    addressFields.cityName = '';
    addressFields.postalCode = '';
  }

  function onCityChange() {
    reset('city', 'streetInCity', 'postalCodeInCity');
    debounce('city', () => {
      const { cityName, countryId } = current();
      if (cityName && countryId) validateCity();
    });
  }

  function onStreetNameChange() {
    reset('streetName', 'streetInCity');
    debounce('street', () => {
      if (current().streetName) validateStreetName();
    });
  }

  function onPostalCodeChange() {
    reset('postalCode', 'postalCodeInCity');
    debounce('postalCode', () => {
      const { postalCode, countryId } = current();
      if (postalCode && countryId) validatePostalCode();
    });
  }

  const cityMessage = computed(() => {
    const city = validation.value.city;
    if (city.loading)
      return { type: 'info', text: translate('register.validating_city') };
    if (city.isValid === false) return { type: 'error', text: city.message };
    if (city.isValid === true && city.message)
      return { type: 'success', text: city.message };
    return null;
  });

  const streetMessage = computed(() => {
    const { streetInCity, streetName } = validation.value;
    if (streetInCity.loading)
      return {
        type: 'info',
        text: translate('register.validating_street_in_city'),
      };
    if (streetInCity.isValid === false)
      return { type: 'warning', text: streetInCity.message };
    if (streetInCity.isValid === true)
      return { type: 'success', text: streetInCity.message };
    if (streetName.isValid === false)
      return { type: 'error', text: streetName.message };
    if (streetName.isValid === true && streetName.message)
      return { type: 'success', text: streetName.message };
    return null;
  });

  const postalCodeMessage = computed(() => {
    const { postalCode, postalCodeInCity } = validation.value;
    if (postalCode.loading)
      return {
        type: 'info',
        text: translate('register.validating_postal_code'),
      };
    if (postalCodeInCity.loading)
      return {
        type: 'info',
        text: translate('register.validating_postal_code_in_city'),
      };
    if (postalCodeInCity.isValid === false)
      return { type: 'warning', text: postalCodeInCity.message };
    if (postalCodeInCity.isValid === true)
      return { type: 'success', text: postalCodeInCity.message };
    if (postalCode.isValid === false)
      return { type: 'error', text: postalCode.message };
    if (postalCode.isValid === true && postalCode.message)
      return { type: 'success', text: postalCode.message };
    return null;
  });

  /**
   * Whether the address is free of refusals.
   *
   * A check that has not run yet does not block submission; only one that came
   * back negative does.
   */
  const addressAccepted = computed(() => {
    const state = validation.value;
    if (
      state.city.isValid === false ||
      state.postalCode.isValid === false ||
      state.streetName.isValid === false
    ) {
      return false;
    }
    const { streetName, cityName, countryId, postalCode } = current();
    if (streetName && cityName && countryId) {
      if (state.streetInCity.isValid === false) return false;
    }
    if (postalCode && cityName && countryId) {
      if (state.postalCodeInCity.isValid === false) return false;
    }
    return true;
  });

  return {
    validation,
    cityMessage,
    streetMessage,
    postalCodeMessage,
    addressAccepted,
    validateCity,
    validatePostalCode,
    validateStreetName,
    validateStreetInCity,
    validatePostalCodeInCity,
    onCountryChange,
    onCityChange,
    onStreetNameChange,
    onPostalCodeChange,
  };
}
