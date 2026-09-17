// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import messages from '@/locales/en.json';
import { emptyRules } from '@/utils/protocolRules';
import ComplianceScanPanel from './ComplianceScanPanel.vue';
import ConfigureProtocols from './ConfigureProtocols.vue';
import ProtocolEditorForm from './ProtocolEditorForm.vue';
import ProtocolVersionList from './ProtocolVersionList.vue';

const api = vi.hoisted(() => ({
  archiveProtocolVersion: vi.fn(),
  createProtocol: vi.fn(),
  createProtocolVersion: vi.fn(),
  deleteProtocolDraft: vi.fn(),
  listComplianceScans: vi.fn(),
  listProtocols: vi.fn(),
  pinProtocolVersion: vi.fn(),
  publishProtocolVersion: vi.fn(),
  purgeProtocolVersion: vi.fn(),
  runComplianceScan: vi.fn(),
  suggestProtocolFromCorpus: vi.fn(),
  updateProtocolDraft: vi.fn(),
}));
const confirm = vi.hoisted(() => vi.fn());
vi.mock('@/api/service/protocolService', () => api);
vi.mock('@/api/service/reviewService', () => ({
  default: { create: vi.fn() },
}));
vi.mock('@/composables/useUserConfirm', () => ({
  useUserConfirm: () => confirm,
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { projectId: '5' } }),
}));

const global = () => ({
  plugins: [
    createPinia(),
    createI18n({ legacy: false, locale: 'en', messages: { en: messages } }),
  ],
  stubs: {
    AppSelect: true,
    ProtocolRuleBuilder: true,
    CorpusProtocolSuggestion: true,
  },
});

const draft = {
  protocol_version_id: 11,
  version_number: 2,
  status: 'draft',
  rules: emptyRules(),
};
const archived = {
  protocol_version_id: 10,
  version_number: 1,
  status: 'published',
  archived_at: '2026-09-01T00:00:00Z',
  rules: emptyRules(),
};
const protocol = {
  protocol_id: 1,
  name: 'Core',
  versions: [draft, archived],
};

describe('ProtocolVersionList', () => {
  it('hides archived versions until asked', async () => {
    const wrapper = mount(ProtocolVersionList, {
      props: { protocols: [protocol] },
      global: global(),
    });
    expect(wrapper.findAll('.version-row')).toHaveLength(1);
    await wrapper.get('.archive-toolbar button').trigger('click');
    expect(wrapper.findAll('.version-row')).toHaveLength(2);

    await wrapper
      .findAll('.version-row')[1]
      .get('button.danger')
      .trigger('click');
    expect(wrapper.emitted('purge')[0]).toEqual([protocol, archived]);
  });
});

describe('ComplianceScanPanel', () => {
  it('lists findings and asks for a correction', async () => {
    const file = {
      scan_file_id: 1,
      filename: 'a.eaf',
      outcome: 'failed',
      issues: [
        {
          issue_number: 1,
          message: 'Missing tier',
          location: '/ANNOTATION_DOCUMENT/TIER',
        },
      ],
    };
    const wrapper = mount(ComplianceScanPanel, {
      props: {
        scan: {
          total_files: 1,
          passed_files: 0,
          failed_files: 1,
          protocol_version_number: 2,
          protocol_name: 'Core',
          trigger: 'preview',
          started_at: '2026-09-01T00:00:00Z',
          files: [file],
        },
      },
      global: global(),
    });
    expect(wrapper.get('.findings small').text()).toBe('TIER');
    await wrapper.get('.findings .text-button').trigger('click');
    expect(wrapper.emitted('create-correction')[0]).toEqual([
      file,
      file.issues[0],
    ]);
  });
});

describe('ProtocolEditorForm', () => {
  it('only lets a new protocol be named', () => {
    const props = { name: 'Core', rules: emptyRules() };
    const creating = mount(ProtocolEditorForm, {
      props: { ...props, mode: 'create-protocol' },
      global: global(),
    });
    const editing = mount(ProtocolEditorForm, {
      props: { ...props, mode: 'edit-draft' },
      global: global(),
    });
    expect(creating.get('input').attributes('disabled')).toBeUndefined();
    expect(editing.get('input').attributes('disabled')).toBeDefined();
    expect(editing.get('h4').text()).toBe(messages.protocols.editor.edit_title);
  });
});

describe('ConfigureProtocols', () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.listProtocols.mockResolvedValue({ data: [protocol] });
    api.listComplianceScans.mockResolvedValue({ data: [] });
    api.suggestProtocolFromCorpus.mockResolvedValue({
      data: { analyzed_files: 0 },
    });
    confirm.mockResolvedValue(true);
  });

  it('closes the editor when the draft being edited is deleted', async () => {
    const wrapper = mount(ConfigureProtocols, { global: global() });
    await flushPromises();

    await wrapper.get('.version-row button.secondary').trigger('click');
    await flushPromises();
    expect(wrapper.find('.protocol-form').exists()).toBe(true);

    await wrapper.get('.version-row button.danger').trigger('click');
    await flushPromises();

    expect(api.deleteProtocolDraft).toHaveBeenCalledWith(5, 11);
    expect(wrapper.find('.protocol-form').exists()).toBe(false);
  });
});
