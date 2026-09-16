import { ref } from 'vue';

/** How long to wait after the last keystroke before asking the server. */
export const AVAILABILITY_CHECK_DELAY = 500;

/**
 * Ask the server whether a username or an email address is still free.
 *
 * The question is only worth asking once the value could plausibly be
 * accepted, so a request is skipped while the field fails its own rules, and
 * a pending request is dropped as soon as the value changes again. A failing
 * check leaves the answer unknown rather than claiming the value is taken.
 */
export function useAvailabilityCheck({
  check,
  translate,
  errorKey,
  minimumLength = 1,
  reportError,
}) {
  const available = ref(null);
  const checking = ref(false);
  const message = ref('');
  let timer = null;

  /** Forget the last answer and abandon any request waiting to be sent. */
  function reset() {
    clearTimeout(timer);
    timer = null;
    available.value = null;
    message.value = '';
  }

  /**
   * The value changed. Ask about it once typing stops, unless `skip` says the
   * field is already known to be unacceptable.
   */
  function request(value, { skip = false } = {}) {
    reset();
    if (skip || !value || value.length < minimumLength) {
      checking.value = false;
      return;
    }

    checking.value = true;
    timer = setTimeout(async () => {
      try {
        const result = await check(value);
        available.value = result.available;
        message.value = result.message;
      } catch (error) {
        reportError('Availability check error', error);
        available.value = null;
        message.value = translate(errorKey);
      } finally {
        checking.value = false;
      }
    }, AVAILABILITY_CHECK_DELAY);
  }

  return { available, checking, message, reset, request };
}
