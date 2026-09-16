import { describe, expect, it } from 'vitest';
import {
  REGISTRATION_FIELDS,
  passwordChecksOf,
  passwordStrengthOf,
  registrationFieldValue,
  validateRegistrationField,
  validateRegistrationForm,
} from './registrationValidation';

const translate = (key) => key;

function completeForm(overrides = {}) {
  const { address, ...rest } = overrides;
  return {
    firstName: 'Ada',
    lastName: 'Lovelace',
    username: 'ada_l',
    email: 'ada@example.org',
    confirmEmail: 'ada@example.org',
    password: 'Analytical1!',
    confirmPassword: 'Analytical1!',
    phoneNumber: '',
    affiliation: 'University of London',
    department: 'Linguistics',
    ...rest,
    address: {
      countryId: 'GB',
      cityName: 'London',
      streetName: 'Dorset Street',
      streetNumber: '12',
      postalCode: 'W1U 8AA',
      addressLine2: '',
      ...address,
    },
  };
}

describe('registrationValidation', () => {
  it('accepts a complete form', () => {
    const errors = validateRegistrationForm(completeForm(), translate);
    expect(Object.values(errors).every((message) => message === '')).toBe(true);
  });

  it('reports every field the form asks about', () => {
    const errors = validateRegistrationForm(completeForm(), translate);
    expect(Object.keys(errors)).toEqual([...REGISTRATION_FIELDS]);
  });

  it.each([
    ['', 'register.first_name_required'],
    ['A', 'register.first_name_too_short'],
    ['A'.repeat(51), 'register.first_name_too_long'],
    ['Ada9', 'register.first_name_invalid'],
    ["Marie-Ève d'Or", ''],
  ])('judges the first name %j', (firstName, expected) => {
    const form = completeForm({ firstName });
    expect(validateRegistrationField('firstName', form, translate)).toBe(
      expected
    );
  });

  it.each([
    ['', 'register.username_required'],
    ['ab', 'register.username_too_short'],
    ['a'.repeat(21), 'register.username_too_long'],
    ['ada lovelace', 'register.username_invalid'],
    ['ada_1', ''],
  ])('judges the username %j', (username, expected) => {
    const form = completeForm({ username });
    expect(validateRegistrationField('username', form, translate)).toBe(
      expected
    );
  });

  it('refuses an email that is not an address and a confirmation that differs', () => {
    expect(
      validateRegistrationField(
        'email',
        completeForm({ email: 'ada' }),
        translate
      )
    ).toBe('register.email_invalid');
    expect(
      validateRegistrationField(
        'confirmEmail',
        completeForm({ confirmEmail: 'other@example.org' }),
        translate
      )
    ).toBe('register.emails_no_match');
  });

  it.each([
    ['', 'register.password_required'],
    ['Ab1!', 'register.password_too_short'],
    ['alllowercase', 'register.password_weak'],
    ['Analytical1!', ''],
  ])('judges the password %j', (password, expected) => {
    const form = completeForm({ password, confirmPassword: password });
    expect(validateRegistrationField('password', form, translate)).toBe(
      expected
    );
  });

  it('accepts a blank optional phone number but refuses a malformed one', () => {
    expect(
      validateRegistrationField(
        'phoneNumber',
        completeForm({ phoneNumber: '' }),
        translate
      )
    ).toBe('');
    expect(
      validateRegistrationField(
        'phoneNumber',
        completeForm({ phoneNumber: '+33 (6) 12-34-56-78' }),
        translate
      )
    ).toBe('');
    expect(
      validateRegistrationField(
        'phoneNumber',
        completeForm({ phoneNumber: '12' }),
        translate
      )
    ).toBe('register.phone_invalid');
  });

  it.each([
    [{ countryId: '' }, 'countryId', 'register.country_required'],
    [{ cityName: '' }, 'cityName', 'register.city_required'],
    [{ cityName: 'L' }, 'cityName', 'register.city_too_short'],
    [{ cityName: 'L'.repeat(51) }, 'cityName', 'register.city_too_long'],
    [{ cityName: 'London 2' }, 'cityName', 'register.city_invalid'],
    [{ streetName: '' }, 'streetName', 'register.street_name_required'],
    [{ streetName: 'Do' }, 'streetName', 'register.street_name_too_short'],
    [
      { streetName: 'D'.repeat(101) },
      'streetName',
      'register.street_name_too_long',
    ],
    [{ postalCode: '' }, 'postalCode', 'register.postal_code_required'],
    [{ postalCode: '!!' }, 'postalCode', 'register.postal_code_invalid'],
  ])('judges the address field %j', (address, fieldName, expected) => {
    const form = completeForm({ address });
    expect(validateRegistrationField(fieldName, form, translate)).toBe(
      expected
    );
  });

  it('reads address fields from the nested address', () => {
    const form = completeForm();
    expect(registrationFieldValue(form, 'cityName')).toBe('London');
    expect(registrationFieldValue(form, 'username')).toBe('ada_l');
    expect(registrationFieldValue(form, 'unknown')).toBe('');
  });

  it('ignores a field the form does not render', () => {
    expect(
      validateRegistrationField('nickname', completeForm(), translate)
    ).toBe('');
  });

  it.each([
    ['', 'weak'],
    ['short', 'weak'],
    ['lowercaseonly', 'weak'],
    ['Lowercase1', 'medium'],
    ['Analytical1!', 'strong'],
  ])('rates the password %j as %s', (password, expected) => {
    expect(passwordStrengthOf(password)).toBe(expected);
  });

  it('reports which password requirements are met', () => {
    expect(passwordChecksOf('Analytical1!')).toEqual({
      length: true,
      lowercase: true,
      uppercase: true,
      number: true,
      special: true,
    });
    expect(passwordChecksOf('')).toEqual({
      length: false,
      lowercase: false,
      uppercase: false,
      number: false,
      special: false,
    });
  });
});
