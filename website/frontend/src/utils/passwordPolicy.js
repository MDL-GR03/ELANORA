/**
 * The rules a chosen password must satisfy.
 *
 * The API enforces the same rules (app/core/password_policy.py); these let a
 * researcher see which ones a password meets while it is typed.
 */

export const PASSWORD_MINIMUM_LENGTH = 8;
// bcrypt ignores everything after 72 bytes.
export const PASSWORD_MAXIMUM_BYTES = 72;

/** The rules, in the order they are listed to the researcher. */
export const PASSWORD_REQUIREMENTS = Object.freeze([
  'length',
  'uppercase',
  'lowercase',
  'number',
  'special',
]);

/** Which password requirements the typed password currently meets. */
export function passwordChecksOf(password) {
  const typed = password || '';
  return {
    length:
      typed.length >= PASSWORD_MINIMUM_LENGTH &&
      new TextEncoder().encode(typed).length <= PASSWORD_MAXIMUM_BYTES,
    uppercase: /[A-Z]/.test(typed),
    lowercase: /[a-z]/.test(typed),
    number: /\d/.test(typed),
    special: /[^A-Za-z0-9]/.test(typed),
  };
}

/** Whether a password satisfies every rule. */
export function meetsPasswordPolicy(password) {
  return Object.values(passwordChecksOf(password)).every(Boolean);
}

/** How close a password is to meeting the policy, for the strength meter. */
export function passwordStrengthOf(password) {
  if (!password) return 'weak';
  const met = Object.values(passwordChecksOf(password)).filter(Boolean).length;
  if (met < 3) return 'weak';
  if (met < PASSWORD_REQUIREMENTS.length) return 'medium';
  return 'strong';
}

/** The requirement list a form displays, translated. */
export function passwordRequirementList(password, translate) {
  const checks = passwordChecksOf(password);
  return PASSWORD_REQUIREMENTS.map((key) => ({
    key,
    text: translate(`passwordPolicy.${key}`),
    valid: checks[key],
  }));
}
