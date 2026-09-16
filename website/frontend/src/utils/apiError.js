/**
 * Explain a failed API request in the researcher's language.
 *
 * The API identifies every refusal with a stable `code` and the `params` its
 * message needs (app/core/errors.py). Password refusals have their own wording
 * under passwordPolicy.errors, and arrive either as a code or, when a request
 * body fails validation, as a validation error whose type names the rule.
 */

import {
  PASSWORD_MAXIMUM_BYTES,
  PASSWORD_MINIMUM_LENGTH,
} from '@/utils/passwordPolicy';

const PASSWORD_RULES = new Set([
  'too_short',
  'too_long',
  'common',
  'repetitive',
  'personal',
  'breached',
]);

function translated(translate, key, params) {
  const text = translate(key, params);
  return text && text !== key ? text : null;
}

function passwordRule(code) {
  if (typeof code !== 'string' || !code.startsWith('password_')) return null;
  const rule = code.slice('password_'.length);
  return PASSWORD_RULES.has(rule) ? rule : null;
}

/** The password rule a failed request broke, or null. */
export function passwordRefusal(error) {
  const body = error?.response?.data;
  const direct = passwordRule(body?.code);
  if (direct) return direct;
  if (!Array.isArray(body?.detail)) return null;
  for (const item of body.detail) {
    const rule = passwordRule(item?.type);
    if (rule) return rule;
  }
  return null;
}

/**
 * The message to show for a failed request: the translation of its code when
 * this interface knows it, the server's own sentence otherwise, and the
 * fallback when there is neither.
 */
export function apiErrorMessage(error, translate, fallback) {
  const rule = passwordRefusal(error);
  if (rule) {
    return (
      translated(translate, `passwordPolicy.errors.${rule}`, {
        min: PASSWORD_MINIMUM_LENGTH,
        max: PASSWORD_MAXIMUM_BYTES,
      }) || fallback
    );
  }
  const body = error?.response?.data;
  if (typeof body?.code === 'string') {
    const message = translated(
      translate,
      `apiErrors.${body.code}`,
      body.params || {}
    );
    if (message) return message;
  }
  if (typeof body?.detail === 'string' && body.detail) return body.detail;
  return fallback;
}

/** The error code of a failed request, or null. */
export function apiErrorCode(error) {
  const code = error?.response?.data?.code;
  return typeof code === 'string' ? code : null;
}
