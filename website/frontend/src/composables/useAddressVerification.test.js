import { ref } from 'vue';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';

import {
  ADDRESS_VALIDATION_DELAY,
  useAddressVerification,
} from './useAddressVerification';

const translate = (key, params) =>
  params && Object.keys(params).length
    ? `${key}:${JSON.stringify(params)}`
    : key;

function ok(data) {
  return { success: true, data };
}

function createVerification(address = {}) {
  const addressFields = ref({
    countryId: 'FR',
    cityName: 'Lyon',
    streetName: 'Rue Garibaldi',
    postalCode: '69003',
    ...address,
  });
  const locationApi = {
    validateCity: vi.fn().mockResolvedValue(ok({ isValid: true })),
    validatePostalCode: vi.fn().mockResolvedValue(ok({ isValid: true })),
    validateStreetInCity: vi
      .fn()
      .mockResolvedValue(
        ok({ isValid: true, messageKey: 'register.location.street_in_city' })
      ),
    validatePostalCodeInCity: vi.fn().mockResolvedValue(
      ok({
        isValid: true,
        messageKey: 'register.location.postal_code_in_city',
      })
    ),
  };
  const reportError = vi.fn();
  const verification = useAddressVerification({
    address: addressFields,
    translate,
    locationApi,
    reportError,
  });
  return { addressFields, locationApi, reportError, verification };
}

describe('useAddressVerification', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('cross-checks the street and postal code once the city is known', async () => {
    const { locationApi, verification } = createVerification();
    await verification.validateCity();
    expect(locationApi.validateStreetInCity).toHaveBeenCalledWith(
      'Rue Garibaldi',
      'Lyon',
      'FR'
    );
    expect(locationApi.validatePostalCodeInCity).toHaveBeenCalledWith(
      '69003',
      'Lyon',
      'FR'
    );
    expect(verification.streetMessage.value).toEqual({
      type: 'success',
      text: 'register.location.street_in_city',
    });
  });

  it('clears the cross-checks when the city is not found', async () => {
    const { locationApi, verification } = createVerification();
    locationApi.validateCity.mockResolvedValue(ok({ isValid: false }));
    await verification.validateCity();
    expect(locationApi.validateStreetInCity).not.toHaveBeenCalled();
    expect(verification.validation.value.streetInCity.isValid).toBeNull();
    expect(verification.cityMessage.value).toEqual({
      type: 'error',
      text: 'register.city_not_found_in_country',
    });
  });

  it('asks for a country before checking a city against one', async () => {
    const { locationApi, verification } = createVerification({
      countryId: '',
    });
    await verification.validateCity();
    expect(locationApi.validateCity).not.toHaveBeenCalled();
    expect(verification.cityMessage.value).toEqual({
      type: 'error',
      text: 'register.country_required',
    });
  });

  it('reports a failing location service instead of leaving the field blank', async () => {
    const { reportError, locationApi, verification } = createVerification();
    locationApi.validateCity.mockRejectedValue(new Error('offline'));
    await verification.validateCity();
    expect(reportError).toHaveBeenCalled();
    expect(verification.cityMessage.value).toEqual({
      type: 'error',
      text: 'register.city_validation_error',
    });
  });

  it('does not cross-check a street while the city is unverified', async () => {
    const { locationApi, verification } = createVerification();
    await verification.validateStreetName();
    expect(locationApi.validateStreetInCity).not.toHaveBeenCalled();
    expect(verification.validation.value.streetName.isValid).toBe(true);
  });

  it('refuses a street that fails its own rule without asking the service', async () => {
    const { locationApi, verification } = createVerification({
      streetName: '123',
    });
    await verification.validateStreetName();
    expect(locationApi.validateStreetInCity).not.toHaveBeenCalled();
    expect(verification.streetMessage.value).toEqual({
      type: 'error',
      text: 'register.street_name_invalid',
    });
  });

  it('shows the service answer in the reader language, with its details', async () => {
    const { locationApi, verification } = createVerification();
    locationApi.validatePostalCodeInCity.mockResolvedValue(
      ok({
        isValid: false,
        messageKey: 'register.location.postal_code_belongs_to',
        messageParams: { cities: 'Villeurbanne' },
        suggestions: ['Villeurbanne'],
      })
    );
    await verification.validateCity();
    expect(verification.postalCodeMessage.value).toEqual({
      type: 'warning',
      text: 'register.location.postal_code_belongs_to:{"cities":"Villeurbanne"}',
    });
  });

  it('shows a failed cross-check as a warning, not a refusal', async () => {
    const { locationApi, verification } = createVerification();
    locationApi.validateStreetInCity.mockResolvedValue(
      ok({ isValid: false, messageKey: 'register.location.street_not_in_city' })
    );
    await verification.validateCity();
    expect(verification.streetMessage.value).toEqual({
      type: 'warning',
      text: 'register.location.street_not_in_city',
    });
  });

  it('waits for typing to stop before asking the server', async () => {
    const { locationApi, verification } = createVerification();
    verification.onCityChange();
    verification.onCityChange();
    expect(locationApi.validateCity).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(ADDRESS_VALIDATION_DELAY);
    expect(locationApi.validateCity).toHaveBeenCalledTimes(1);
  });

  it('forgets the city and postal code when the country changes', () => {
    const { addressFields, verification } = createVerification();
    verification.validation.value.city = {
      isValid: true,
      message: 'confirmed',
      loading: false,
    };
    verification.onCountryChange();
    expect(addressFields.value.cityName).toBe('');
    expect(addressFields.value.postalCode).toBe('');
    expect(verification.validation.value.city.isValid).toBeNull();
    expect(verification.cityMessage.value).toBeNull();
  });

  it('blocks submission only on a check that came back negative', async () => {
    const { verification } = createVerification();
    expect(verification.addressAccepted.value).toBe(true);
    verification.validation.value.city.isValid = false;
    expect(verification.addressAccepted.value).toBe(false);
  });

  it('blocks submission when the street is not in the city', async () => {
    const { locationApi, verification } = createVerification();
    locationApi.validateStreetInCity.mockResolvedValue(
      ok({ isValid: false, messageKey: 'register.location.street_not_in_city' })
    );
    await verification.validateCity();
    expect(verification.addressAccepted.value).toBe(false);
  });

  it('cross-checks the postal code only against a confirmed city', async () => {
    const { locationApi, verification } = createVerification();
    await verification.validatePostalCode();
    expect(locationApi.validatePostalCodeInCity).not.toHaveBeenCalled();
    await verification.validateCity();
    locationApi.validatePostalCodeInCity.mockClear();
    await verification.validatePostalCode();
    expect(locationApi.validatePostalCodeInCity).toHaveBeenCalled();
  });

  it('prefers the loading message over an earlier result', async () => {
    const { verification } = createVerification();
    verification.validation.value.postalCode.loading = true;
    expect(verification.postalCodeMessage.value).toEqual({
      type: 'info',
      text: 'register.validating_postal_code',
    });
  });
});
