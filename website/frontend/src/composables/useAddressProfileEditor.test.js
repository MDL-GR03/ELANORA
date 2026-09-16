import { computed, effectScope, ref } from 'vue';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useAddressProfileEditor } from './useAddressProfileEditor';

function createEditor(profileValue = {}) {
  const profile = ref({
    address: {
      street_name: 'Main Street',
      street_number: '12',
      address_line_2: null,
      postal_code: '1000',
      city: { name: 'Brussels', country: 'BE' },
    },
    ...profileValue,
  });
  const location = {
    getCountries: vi.fn().mockResolvedValue({
      success: true,
      data: [{ country_id: 'BE', country_name: 'Belgium' }],
    }),
    validateCity: vi.fn().mockResolvedValue({
      success: true,
      data: { isValid: true },
    }),
    validatePostalCode: vi.fn().mockResolvedValue({
      success: true,
      data: { isValid: true },
    }),
    validatePostalCodeInCity: vi.fn().mockResolvedValue({
      success: true,
      data: {
        isValid: true,
        messageKey: 'register.location.postal_code_in_city',
      },
    }),
    validateStreetInCity: vi.fn().mockResolvedValue({
      success: true,
      data: { isValid: true, messageKey: 'register.location.street_in_city' },
    }),
  };
  const updateAddress = vi.fn().mockResolvedValue({ data: { ok: true } });
  const emit = vi.fn();
  const scope = effectScope();
  const editor = scope.run(() =>
    useAddressProfileEditor({
      profile: computed(() => profile.value),
      updateAddress,
      location,
      emit,
      translate: (key) => `translated:${key}`,
    })
  );
  return { profile, location, updateAddress, emit, editor, scope };
}

afterEach(() => {
  vi.useRealTimers();
});

describe('useAddressProfileEditor', () => {
  it('loads countries and initializes the draft when editing starts', async () => {
    const { editor, location, scope } = createEditor();

    await editor.startEditAddress();
    expect(location.getCountries).toHaveBeenCalledOnce();
    expect(editor.editAddressMode.value).toBe(true);
    expect(editor.editedAddress.value).toEqual({
      streetName: 'Main Street',
      streetNumber: '12',
      addressLine2: '',
      cityName: 'Brussels',
      postalCode: '1000',
      countryId: 'BE',
    });
    expect(editor.countryOptions.value).toEqual([
      { value: 'BE', label: 'Belgium' },
    ]);
    scope.stop();
  });

  it('debounces city validation and performs its dependent checks', async () => {
    vi.useFakeTimers();
    const { editor, location, scope } = createEditor();
    await editor.startEditAddress();

    editor.onCityChange();
    expect(location.validateCity).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(500);

    expect(location.validateCity).toHaveBeenCalledWith('Brussels', 'BE');
    expect(location.validateStreetInCity).toHaveBeenCalledWith(
      'Main Street',
      'Brussels',
      'BE'
    );
    expect(location.validatePostalCodeInCity).toHaveBeenCalledWith(
      '1000',
      'Brussels',
      'BE'
    );
    expect(editor.addressValidation.value.city.isValid).toBe(true);
    scope.stop();
  });

  it('clears dependent location fields when the country changes', async () => {
    const { editor, scope } = createEditor();
    await editor.startEditAddress();

    editor.onCountryChange();
    expect(editor.editedAddress.value.cityName).toBe('');
    expect(editor.editedAddress.value.postalCode).toBe('');
    expect(editor.addressValidation.value.city.isValid).toBeNull();
    scope.stop();
  });

  it('rejects an incomplete address before persistence', async () => {
    const { editor, updateAddress, emit, scope } = createEditor();
    await editor.startEditAddress();
    editor.editedAddress.value.streetName = '';

    await expect(editor.saveAddress()).resolves.toBeUndefined();
    expect(updateAddress).not.toHaveBeenCalled();
    expect(emit).toHaveBeenCalledWith('show-message', {
      text: 'translated:register.street_name_required',
      type: 'error',
    });
    scope.stop();
  });

  it('warns on cross-check mismatch but still saves the normalized payload', async () => {
    const { editor, updateAddress, emit, scope } = createEditor();
    await editor.startEditAddress();
    editor.addressValidation.value.streetInCity.isValid = false;

    await editor.saveAddress();
    expect(emit).toHaveBeenCalledWith(
      'show-message',
      expect.objectContaining({ type: 'warning' })
    );
    expect(updateAddress).toHaveBeenCalledWith({
      street_name: 'Main Street',
      street_number: '12',
      city_name: 'Brussels',
      country_code: 'BE',
      country_name: 'Belgium',
      postal_code: '1000',
      address_line_2: null,
    });
    expect(emit).toHaveBeenCalledWith('profile-updated');
    expect(editor.editAddressMode.value).toBe(false);
    scope.stop();
  });

  it('explains a failed save in the reader language when the server gives no detail', async () => {
    const { editor, updateAddress, emit, scope } = createEditor();
    updateAddress.mockRejectedValue({ response: { status: 500 } });
    await editor.startEditAddress();

    await editor.saveAddress();
    expect(emit).toHaveBeenCalledWith('show-message', {
      text: 'translated:profile.address.save_failed',
      type: 'error',
    });
    scope.stop();
  });

  it('stops waiting to check a city once the editor is gone', async () => {
    vi.useFakeTimers();
    const { editor, location, scope } = createEditor();
    await editor.startEditAddress();
    editor.onCityChange();
    scope.stop();
    await vi.advanceTimersByTimeAsync(500);
    expect(location.validateCity).not.toHaveBeenCalled();
  });

  it('surfaces persistence details and releases saving state', async () => {
    const { editor, updateAddress, emit, scope } = createEditor();
    updateAddress.mockRejectedValue({
      response: { status: 400, data: { detail: 'Invalid address' } },
    });
    await editor.startEditAddress();

    await editor.saveAddress();
    expect(emit).toHaveBeenCalledWith('show-message', {
      text: 'Invalid address',
      type: 'error',
    });
    expect(editor.savingAddress.value).toBe(false);
    scope.stop();
  });
});
