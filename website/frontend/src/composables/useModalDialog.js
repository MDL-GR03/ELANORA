import { nextTick, onBeforeUnmount, onMounted, unref, watch } from 'vue';

/** Resolve a plain value, a ref, or a getter function to its current value. */
function read(source) {
  return typeof source === 'function' ? source() : unref(source);
}

/**
 * Keyboard and focus behavior shared by every ELANORA modal dialog.
 *
 * Dialogs previously repeated this logic in each component, which meant a fix
 * to one dialog never reached the others. The listener is attached in script
 * rather than through a template handler so the dialog container stays a plain
 * labelled region for assistive technology.
 */

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  'input:not([disabled])',
  'textarea:not([disabled])',
  'select:not([disabled])',
  'a[href]',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

function focusableWithin(container, selector) {
  if (!container) return [];
  // `offsetParent` is deliberately not consulted: it is null for the
  // position-fixed surfaces these dialogs use, and always null under jsdom.
  return Array.from(container.querySelectorAll(selector)).filter(
    (element) => !element.hidden
  );
}

export function useModalDialog(dialogRef, options = {}) {
  const {
    onClose,
    isOpen = null,
    initialFocus = null,
    focusableSelector = FOCUSABLE_SELECTOR,
  } = options;

  let previouslyFocused = null;
  let attachedElement = null;

  function rememberOpener() {
    previouslyFocused =
      typeof document !== 'undefined' &&
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
  }

  function restoreOpener() {
    if (previouslyFocused?.isConnected) previouslyFocused.focus();
    previouslyFocused = null;
  }

  async function focusInitial() {
    await nextTick();
    const target = read(initialFocus);
    if (target?.focus) {
      target.focus();
      return;
    }
    const [first] = focusableWithin(read(dialogRef), focusableSelector);
    (first ?? read(dialogRef))?.focus?.();
  }

  function trapTab(event) {
    const container = read(dialogRef);
    const focusable = focusableWithin(container, focusableSelector);
    if (!focusable.length) {
      event.preventDefault();
      container?.focus?.();
      return;
    }
    const first = focusable[0];
    const last = focusable.at(-1);
    const active = document.activeElement;
    if (event.shiftKey && (active === first || active === container)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      event.stopPropagation();
      onClose?.();
      return;
    }
    if (event.key === 'Tab') trapTab(event);
  }

  function attach(element) {
    if (attachedElement === element) return;
    detach();
    if (!element?.addEventListener) return;
    element.addEventListener('keydown', handleKeydown);
    attachedElement = element;
  }

  function detach() {
    attachedElement?.removeEventListener('keydown', handleKeydown);
    attachedElement = null;
  }

  // Dialogs rendered behind `v-if` swap their element in and out, so the
  // listener follows the element rather than being bound once at mount.
  watch(
    () => read(dialogRef),
    (element) => attach(element),
    { immediate: true, flush: 'post' }
  );

  if (isOpen) {
    watch(
      () => Boolean(read(isOpen)),
      async (open, wasOpen) => {
        if (open === wasOpen) return;
        if (open) {
          rememberOpener();
          await focusInitial();
        } else {
          await nextTick();
          restoreOpener();
        }
      },
      { immediate: true }
    );
  } else {
    // A dialog created only while it is open records its opener during setup,
    // before Vue moves focus into the newly mounted content.
    rememberOpener();
    onMounted(focusInitial);
  }

  onBeforeUnmount(() => {
    detach();
    restoreOpener();
  });

  return { handleKeydown, focusInitial, restoreOpener };
}

export default useModalDialog;
