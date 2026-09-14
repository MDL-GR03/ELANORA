// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import ProfileAddressCard from './ProfileAddressCard.vue';
import ProfilePersonalCard from './ProfilePersonalCard.vue';
import ProfileProfessionalCard from './ProfileProfessionalCard.vue';

vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key) => key }) }));

const userProfile = {
  first_name: 'Ada',
  last_name: 'Lovelace',
  username: 'ada',
  email: 'ada@example.test',
  is_verified_account: true,
  phone_number: '+32 123',
  affiliation: 'Research Institute',
  department: 'Linguistics',
  role: 'Researcher',
  address: {
    street_name: 'Main Street',
    street_number: '12',
    address_line_2: 'Office 4',
    postal_code: '1000',
    city: { name: 'Brussels', country: 'BE' },
  },
};

describe('profile presentation cards', () => {
  it('renders personal evidence and delegates username editing', async () => {
    const startEditUsername = vi.fn();
    const wrapper = mount(ProfilePersonalCard, {
      props: {
        userProfile,
        editedUsername: 'ada',
        editUsernameMode: false,
        saving: false,
        startEditUsername,
        cancelEditUsername: vi.fn(),
        saveUsername: vi.fn(),
      },
    });

    expect(wrapper.text()).toContain('Ada Lovelace');
    expect(wrapper.text()).toContain('ada@example.test');
    expect(wrapper.text()).toContain('profile.overview.personal_info.verified');
    await wrapper.get('.modern-edit-btn').trigger('click');
    expect(startEditUsername).toHaveBeenCalledOnce();
  });

  it('renders professional evidence and delegates validation and saving', async () => {
    const validateProfessionalField = vi.fn();
    const saveProfessional = vi.fn();
    const wrapper = mount(ProfileProfessionalCard, {
      props: {
        userProfile,
        editedProfessional: {
          affiliation: 'Research Institute',
          department: 'Linguistics',
        },
        editProfessionalMode: true,
        savingProfessional: false,
        professionalValidation: {
          affiliation: { isValid: true, message: '' },
          department: { isValid: true, message: '' },
        },
        editProfessionalInfo: vi.fn(),
        validateProfessionalField,
        saveProfessional,
        cancelEditProfessional: vi.fn(),
      },
    });

    await wrapper.get('#edit-affiliation').trigger('blur');
    await wrapper.get('.modern-save-btn').trigger('click');
    expect(validateProfessionalField).toHaveBeenCalledWith('affiliation');
    expect(saveProfessional).toHaveBeenCalledOnce();
  });

  it('renders address evidence and delegates editable field validation', async () => {
    const validateCityField = vi.fn();
    const saveAddress = vi.fn();
    const wrapper = mount(ProfileAddressCard, {
      props: {
        userProfile,
        editedAddress: {
          streetName: 'Main Street',
          streetNumber: '12',
          addressLine2: 'Office 4',
          cityName: 'Brussels',
          postalCode: '1000',
          countryId: 'BE',
        },
        editAddressMode: true,
        savingAddress: false,
        countryOptions: [{ value: 'BE', label: 'Belgium' }],
        addressValidation: {
          city: { isValid: true, loading: false },
          postalCode: { isValid: true, loading: false },
          streetName: { isValid: true },
          streetInCity: { isValid: true, loading: false },
        },
        cityValidationMessage: null,
        streetValidationMessage: null,
        postalCodeValidationMessage: null,
        editAddress: vi.fn(),
        onCountryChange: vi.fn(),
        validateCityField,
        onCityChange: vi.fn(),
        validatePostalCodeField: vi.fn(),
        onPostalCodeChange: vi.fn(),
        validateStreetNameField: vi.fn(),
        onStreetNameChange: vi.fn(),
        saveAddress,
        cancelEditAddress: vi.fn(),
      },
      global: {
        stubs: {
          AppSelect: { template: '<div class="country-select" />' },
        },
      },
    });

    await wrapper.get('#edit-city').trigger('blur');
    await wrapper.get('.modern-save-btn').trigger('click');
    expect(validateCityField).toHaveBeenCalledOnce();
    expect(saveAddress).toHaveBeenCalledOnce();
  });
});
