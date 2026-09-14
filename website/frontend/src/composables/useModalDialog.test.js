// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { defineComponent, h, nextTick, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { useModalDialog } from './useModalDialog';

function makeDialog({
  isOpen = null,
  onClose = vi.fn(),
  initialFocus = null,
  openAsGetter = false,
}) {
  return defineComponent({
    setup(_, { expose }) {
      const dialogElement = ref(null);
      const firstButton = ref(null);
      const lastButton = ref(null);
      useModalDialog(dialogElement, {
        onClose,
        isOpen: openAsGetter && isOpen ? () => isOpen.value : isOpen,
        initialFocus: initialFocus === 'last' ? lastButton : null,
      });
      expose({ dialogElement, firstButton, lastButton });
      return () =>
        (isOpen === null || isOpen.value) &&
        h('div', { ref: dialogElement, role: 'dialog', tabindex: '-1' }, [
          h('button', { ref: firstButton }, 'first'),
          h('input', { ref: null }),
          h('button', { ref: lastButton }, 'last'),
        ]);
    },
  });
}

function press(element, key, shiftKey = false) {
  const event = new KeyboardEvent('keydown', {
    key,
    shiftKey,
    bubbles: true,
    cancelable: true,
  });
  element.dispatchEvent(event);
  return event;
}

describe('useModalDialog', () => {
  it('closes on Escape and stops the event from escaping the dialog', async () => {
    const onClose = vi.fn();
    const wrapper = mount(makeDialog({ onClose }), { attachTo: document.body });
    await nextTick();

    const event = press(wrapper.vm.dialogElement, 'Escape');

    expect(onClose).toHaveBeenCalledOnce();
    expect(event.defaultPrevented).toBe(true);
    wrapper.unmount();
  });

  it('focuses the first control when the dialog is mounted open', async () => {
    const wrapper = mount(makeDialog({}), { attachTo: document.body });
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(wrapper.vm.firstButton);
    wrapper.unmount();
  });

  it('honours an explicit initial focus target', async () => {
    const wrapper = mount(makeDialog({ initialFocus: 'last' }), {
      attachTo: document.body,
    });
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(wrapper.vm.lastButton);
    wrapper.unmount();
  });

  it('wraps Tab from the last control back to the first', async () => {
    const wrapper = mount(makeDialog({}), { attachTo: document.body });
    await nextTick();
    wrapper.vm.lastButton.focus();

    const event = press(wrapper.vm.lastButton, 'Tab');

    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(wrapper.vm.firstButton);
    wrapper.unmount();
  });

  it('wraps Shift+Tab from the first control to the last', async () => {
    const wrapper = mount(makeDialog({}), { attachTo: document.body });
    await nextTick();
    wrapper.vm.firstButton.focus();

    const event = press(wrapper.vm.firstButton, 'Tab', true);

    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(wrapper.vm.lastButton);
    wrapper.unmount();
  });

  it('leaves Tab alone in the middle of the dialog', async () => {
    const wrapper = mount(makeDialog({}), { attachTo: document.body });
    await nextTick();
    const input = wrapper.vm.dialogElement.querySelector('input');
    input.focus();

    const event = press(input, 'Tab');

    expect(event.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(input);
    wrapper.unmount();
  });

  it('returns focus to the opener when a toggled dialog closes', async () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();

    const isOpen = ref(false);
    const wrapper = mount(makeDialog({ isOpen }), { attachTo: document.body });

    isOpen.value = true;
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(wrapper.vm.firstButton);

    isOpen.value = false;
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
    opener.remove();
  });

  // A getter is the natural way to pass `props.visible`, and `unref` does not
  // resolve one, so an open state expressed this way must be watched correctly.
  it('accepts the open state as a getter function', async () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();

    const isOpen = ref(false);
    const wrapper = mount(makeDialog({ isOpen, openAsGetter: true }), {
      attachTo: document.body,
    });

    isOpen.value = true;
    await nextTick();
    await nextTick();
    expect(document.activeElement).toBe(wrapper.vm.firstButton);

    isOpen.value = false;
    await nextTick();
    await nextTick();

    expect(document.activeElement).toBe(opener);
    wrapper.unmount();
    opener.remove();
  });

  it('returns focus to the opener when a dialog is unmounted', async () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();

    const wrapper = mount(makeDialog({}), { attachTo: document.body });
    await nextTick();
    await nextTick();

    wrapper.unmount();

    expect(document.activeElement).toBe(opener);
    opener.remove();
  });

  it('stops handling keys once the dialog is unmounted', async () => {
    const onClose = vi.fn();
    const wrapper = mount(makeDialog({ onClose }), { attachTo: document.body });
    await nextTick();
    const element = wrapper.vm.dialogElement;

    wrapper.unmount();
    press(element, 'Escape');

    expect(onClose).not.toHaveBeenCalled();
  });
});
