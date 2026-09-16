// @vitest-environment jsdom

import { createApp, defineComponent, h, nextTick } from 'vue';
import { createI18n } from 'vue-i18n';
import { afterEach, describe, expect, it } from 'vitest';

import messages from '@/locales/fr.json';
import { useUserConfirm } from './useUserConfirm';

describe('useUserConfirm', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('renders the dialog in the language of the app that asked', async () => {
    let confirm;
    const Caller = defineComponent({
      setup() {
        confirm = useUserConfirm();
        return () => h('div');
      },
    });
    const host = document.createElement('div');
    document.body.appendChild(host);
    createApp(Caller)
      .use(
        createI18n({ legacy: false, locale: 'fr', messages: { fr: messages } })
      )
      .mount(host);

    const answer = confirm({ title: 'Supprimer ?', message: 'Définitif.' });
    await nextTick();

    expect(document.body.textContent).toContain(
      messages.dialogs.confirmationRequired
    );
    expect(document.body.textContent).toContain(messages.common.cancel);
    document.querySelector('.confirm-button.primary').click();
    expect(await answer).toBe(true);
  });
});
