/**
 * Field rules for the registration form.
 *
 * These are pure functions: they read a plain form object and return a
 * translated message, or an empty string when the field is acceptable. Keeping
 * them out of the component lets the rules be tested directly, and makes it
 * obvious that every message comes from the locale files rather than being
 * written in English in the middle of the markup.
 */

import {
  PASSWORD_MINIMUM_LENGTH,
  meetsPasswordPolicy,
} from '@/utils/passwordPolicy';

const NAME_PATTERN = /^[a-zA-ZÀ-ÿ\s-']+$/;
const USERNAME_PATTERN = /^\w+$/;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const POSTAL_CODE_PATTERN = /^[A-Za-z0-9\s-]{3,10}$/;
const PHONE_PATTERN = /^(\+?[1-9]\d{7,15}|0\d{8,15})$/;
const PHONE_SEPARATORS = /[\s\-()]/g;

/** Fields validated when the form is submitted, in the order they appear. */
export const REGISTRATION_FIELDS = Object.freeze([
  'firstName',
  'lastName',
  'username',
  'email',
  'confirmEmail',
  'password',
  'confirmPassword',
  'phoneNumber',
  'affiliation',
  'department',
  'countryId',
  'cityName',
  'streetName',
  'postalCode',
]);

/** Fields a researcher must fill before the form can be submitted. */
export const REQUIRED_REGISTRATION_FIELDS = Object.freeze([
  'firstName',
  'lastName',
  'username',
  'email',
  'confirmEmail',
  'password',
  'confirmPassword',
  'affiliation',
  'department',
]);

/** Address fields a researcher must fill before the form can be submitted. */
export const REQUIRED_ADDRESS_FIELDS = Object.freeze([
  'countryId',
  'cityName',
  'streetName',
  'postalCode',
]);

const ADDRESS_FIELDS = new Set(REQUIRED_ADDRESS_FIELDS);

/** Read a field from the form, whether it lives at the top level or in the address. */
export function registrationFieldValue(form, fieldName) {
  const source = ADDRESS_FIELDS.has(fieldName) ? form?.address : form;
  return source?.[fieldName] ?? '';
}

function personName(value, translate, prefix) {
  if (!value) return translate(`register.${prefix}_required`);
  if (value.length < 2) return translate(`register.${prefix}_too_short`);
  if (value.length > 50) return translate(`register.${prefix}_too_long`);
  if (!NAME_PATTERN.test(value)) return translate(`register.${prefix}_invalid`);
  return '';
}

function boundedText(value, translate, prefix, { minimum, maximum }) {
  if (!value) return translate(`register.${prefix}_required`);
  if (value.length < minimum) return translate(`register.${prefix}_too_short`);
  if (value.length > maximum) return translate(`register.${prefix}_too_long`);
  return '';
}

const RULES = {
  firstName: (form, translate) =>
    personName(form.firstName, translate, 'first_name'),
  lastName: (form, translate) =>
    personName(form.lastName, translate, 'last_name'),
  username: (form, translate) => {
    const value = form.username;
    if (!value) return translate('register.username_required');
    if (value.length < 3) return translate('register.username_too_short');
    if (value.length > 20) return translate('register.username_too_long');
    if (!USERNAME_PATTERN.test(value))
      return translate('register.username_invalid');
    return '';
  },
  email: (form, translate) => {
    if (!form.email) return translate('register.email_required');
    if (!EMAIL_PATTERN.test(form.email))
      return translate('register.email_invalid');
    return '';
  },
  confirmEmail: (form, translate) => {
    if (!form.confirmEmail) return translate('register.email_required');
    if (form.email !== form.confirmEmail)
      return translate('register.emails_no_match');
    return '';
  },
  password: (form, translate) => {
    const value = form.password;
    if (!value) return translate('register.password_required');
    if (value.length < PASSWORD_MINIMUM_LENGTH)
      return translate('register.password_too_short');
    if (!meetsPasswordPolicy(value)) return translate('register.password_weak');
    return '';
  },
  confirmPassword: (form, translate) => {
    if (!form.confirmPassword) return translate('register.password_required');
    if (form.password !== form.confirmPassword)
      return translate('register.passwords_no_match');
    return '';
  },
  phoneNumber: (form, translate) => {
    if (!form.phoneNumber) return '';
    const cleaned = form.phoneNumber.replace(PHONE_SEPARATORS, '');
    return PHONE_PATTERN.test(cleaned)
      ? ''
      : translate('register.phone_invalid');
  },
  affiliation: (form, translate) =>
    boundedText(form.affiliation, translate, 'affiliation', {
      minimum: 2,
      maximum: 100,
    }),
  department: (form, translate) =>
    boundedText(form.department, translate, 'department', {
      minimum: 2,
      maximum: 100,
    }),
  countryId: (form, translate) =>
    form.address?.countryId ? '' : translate('register.country_required'),
  cityName: (form, translate) => {
    const value = form.address?.cityName;
    const bounded = boundedText(value, translate, 'city', {
      minimum: 2,
      maximum: 50,
    });
    if (bounded) return bounded;
    return NAME_PATTERN.test(value) ? '' : translate('register.city_invalid');
  },
  streetName: (form, translate) => {
    const value = form.address?.streetName;
    const bounded = boundedText(value, translate, 'street_name', {
      minimum: 3,
      maximum: 100,
    });
    if (bounded) return bounded;
    return /^\d+$/.test(value.trim())
      ? translate('register.street_name_invalid')
      : '';
  },
  postalCode: (form, translate) => {
    const value = form.address?.postalCode;
    if (!value) return translate('register.postal_code_required');
    return POSTAL_CODE_PATTERN.test(value)
      ? ''
      : translate('register.postal_code_invalid');
  },
};

/**
 * Validate one field.
 *
 * Returns the message to show, or an empty string when the field is fine. An
 * unknown field name is not an error: the form only ever asks about fields it
 * renders.
 */
export function validateRegistrationField(fieldName, form, translate) {
  const rule = RULES[fieldName];
  return rule ? rule(form, translate) : '';
}

/** Validate every field, returning a map of field name to message. */
export function validateRegistrationForm(form, translate) {
  const errors = {};
  for (const fieldName of REGISTRATION_FIELDS) {
    errors[fieldName] = validateRegistrationField(fieldName, form, translate);
  }
  return errors;
}
