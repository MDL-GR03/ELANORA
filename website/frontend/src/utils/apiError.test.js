import { describe, expect, it } from 'vitest';
import { createI18n } from 'vue-i18n';

import en from '@/locales/en.json';
import fr from '@/locales/fr.json';
import { apiErrorCode, apiErrorMessage, passwordRefusal } from './apiError';

const failure = (data) => ({ response: { data } });
const translator = (locale) =>
  createI18n({ legacy: false, locale, messages: { en, fr } }).global.t;

describe('apiErrorMessage', () => {
  it('translates a coded refusal with its parameters', () => {
    const error = failure({
      detail: 'File too large. Maximum size is 50 MB per file',
      code: 'upload_file_too_large',
      params: { max_mb: 50 },
    });
    expect(apiErrorMessage(error, translator('fr'), 'fallback')).toBe(
      'Fichier trop volumineux. Taille maximale : 50 Mo par fichier'
    );
  });

  it("shows the server's sentence for a code this interface does not know", () => {
    const error = failure({ detail: 'Something new', code: 'brand_new_code' });
    expect(apiErrorMessage(error, translator('fr'), 'fallback')).toBe(
      'Something new'
    );
  });

  it('never shows a validation list as text', () => {
    const error = failure({
      detail: [{ type: 'missing', loc: ['body', 'email'] }],
      code: 'validation_error',
    });
    expect(apiErrorMessage(error, translator('en'), 'fallback')).toBe(
      'fallback'
    );
  });

  it('falls back when the request never reached the server', () => {
    expect(apiErrorMessage(new Error('offline'), translator('en'), 'x')).toBe(
      'x'
    );
  });

  it('explains a password refusal whichever way it arrives', () => {
    const coded = failure({ code: 'password_breached' });
    const validated = failure({
      detail: [{ type: 'password_too_short', loc: ['body', 'password'] }],
      code: 'validation_error',
    });
    expect(passwordRefusal(coded)).toBe('breached');
    expect(passwordRefusal(validated)).toBe('too_short');
    expect(apiErrorMessage(validated, translator('en'), 'x')).toBe(
      en.passwordPolicy.errors.too_short.replace('{min}', '15')
    );
  });

  it('does not mistake other password errors for policy refusals', () => {
    expect(passwordRefusal(failure({ code: 'password_change_failed' }))).toBe(
      null
    );
  });

  it('reads the code of a failed request', () => {
    expect(apiErrorCode(failure({ code: 'file_type_in_use' }))).toBe(
      'file_type_in_use'
    );
    expect(apiErrorCode({})).toBeNull();
  });
});

describe('apiErrors translations', () => {
  it('translates every code in every language', () => {
    expect(Object.keys(fr.apiErrors).sort()).toEqual(
      Object.keys(en.apiErrors).sort()
    );
  });
});
