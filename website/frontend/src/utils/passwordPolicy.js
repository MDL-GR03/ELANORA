/**
 * The rules a chosen password must satisfy, following NIST SP 800-63B rev. 4.
 *
 * Length does the work; there are no rules about capitals, digits or symbols.
 * The API (app/core/password_policy.py) also refuses passwords known from
 * breaches and ones built from the account's own details, which the browser
 * cannot check, and reports each refusal with a stable error type.
 */

export const PASSWORD_MINIMUM_LENGTH = 15;
// bcrypt ignores everything after 72 bytes.
export const PASSWORD_MAXIMUM_BYTES = 72;
const STRONG_LENGTH = 20;

/** The rules checked while typing, in the order they are listed. */
export const PASSWORD_REQUIREMENTS = Object.freeze(['length', 'pattern']);

function isRepetitive(password) {
  const lowered = password.toLowerCase();
  if (/^(.{1,4}?)\1+$/su.test(lowered)) return true;
  const steps = new Set();
  for (let index = 1; index < lowered.length; index += 1) {
    steps.add(lowered.charCodeAt(index) - lowered.charCodeAt(index - 1));
  }
  return steps.size === 1 && (steps.has(1) || steps.has(-1));
}

/** Which rules the typed password currently meets. */
export function passwordChecksOf(password) {
  const typed = password || '';
  return {
    length:
      typed.length >= PASSWORD_MINIMUM_LENGTH &&
      new TextEncoder().encode(typed).length <= PASSWORD_MAXIMUM_BYTES,
    pattern: typed.length > 0 && !isRepetitive(typed),
  };
}

/** Whether a password satisfies every rule the browser can check. */
export function meetsPasswordPolicy(password) {
  return Object.values(passwordChecksOf(password)).every(Boolean);
}

/** A rough measure for the strength meter: longer is stronger. */
export function passwordStrengthOf(password) {
  if (!meetsPasswordPolicy(password)) return 'weak';
  return password.length >= STRONG_LENGTH ? 'strong' : 'medium';
}

/** The requirement list a form displays, translated. */
export function passwordRequirementList(password, translate) {
  const checks = passwordChecksOf(password);
  return PASSWORD_REQUIREMENTS.map((key) => ({
    key,
    text: translate(`passwordPolicy.${key}`, {
      min: PASSWORD_MINIMUM_LENGTH,
    }),
    valid: checks[key],
  }));
}

/**
 * The translated reason the API refused a password, or null.
 *
 * Refusals arrive as validation errors whose type is `password_<rule>`.
 */
export function passwordRefusalMessage(error, translate) {
  const detail = error?.response?.data?.detail;
  if (!Array.isArray(detail)) return null;
  const refusal = detail.find((item) =>
    String(item?.type || '').startsWith('password_')
  );
  if (!refusal) return null;
  const rule = refusal.type.slice('password_'.length);
  return translate(`passwordPolicy.errors.${rule}`, {
    min: PASSWORD_MINIMUM_LENGTH,
    max: PASSWORD_MAXIMUM_BYTES,
  });
}

/**
 * What to tell the researcher when a request that sets a password fails: the
 * password refusal if there is one, the server's message if it sent a
 * sentence, otherwise the fallback.
 */
export function passwordRequestError(error, translate, fallback) {
  const detail = error?.response?.data?.detail;
  return (
    passwordRefusalMessage(error, translate) ||
    (typeof detail === 'string' && detail) ||
    fallback
  );
}
