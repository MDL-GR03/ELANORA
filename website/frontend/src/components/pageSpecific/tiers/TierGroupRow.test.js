// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import { describe, expect, it } from 'vitest';

import messages from '@/locales/en.json';
import TierGroupRow from './TierGroupRow.vue';
import AppSelect from '@/components/common/AppSelect.vue';

function renderRow(currentSectionId = 1) {
  return mount(TierGroupRow, {
    props: {
      group: {
        tier_group_id: 7,
        elan_file_name: 'research-session.eaf',
        tiers: [],
      },
      sections: [
        { section_id: 1, name: 'Prosody' },
        { section_id: 2, name: 'Lexicon' },
      ],
      currentSectionId,
    },
    global: {
      plugins: [
        createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
      ],
      stubs: {
        FontAwesomeIcon: true,
        TierTree: true,
      },
    },
  });
}

describe('TierGroupRow', () => {
  it('offers a keyboard-operable alternative to dragging', async () => {
    const wrapper = renderRow();
    const select = wrapper.getComponent(AppSelect);

    expect(select.props('modelValue')).toBe(1);
    select.vm.$emit('change', 2);
    select.vm.$emit('change', '');
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted('move')).toEqual([[2], [null]]);
  });

  it('provides an accessible name for the drag handle', () => {
    const wrapper = renderRow();

    expect(
      wrapper.get('.tier-group-drag-handle').attributes('aria-label')
    ).toContain('research-session.eaf');
  });
});
