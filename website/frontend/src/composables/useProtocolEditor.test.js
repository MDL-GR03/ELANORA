import { ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { emptyRules } from '@/utils/protocolRules';
import { useProtocolEditor } from './useProtocolEditor';

const api = vi.hoisted(() => ({
  createProtocol: vi.fn(),
  createProtocolVersion: vi.fn(),
  suggestProtocolFromCorpus: vi.fn(),
  updateProtocolDraft: vi.fn(),
}));
vi.mock('@/api/service/protocolService', () => api);

const protocol = { protocol_id: 1, name: 'Core' };
const version = {
  protocol_version_id: 10,
  rules: { ...emptyRules(), required_tiers: ['Gloss'] },
};

describe('useProtocolEditor', () => {
  let fail;
  let onSaved;

  function setup() {
    fail = vi.fn();
    onSaved = vi.fn();
    return useProtocolEditor({
      projectId: ref(5),
      translate: (key) => key,
      notify: vi.fn(),
      fail,
      onSaved,
    });
  }

  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.suggestProtocolFromCorpus.mockResolvedValue({
      data: { analyzed_files: 2, rules: emptyRules() },
    });
  });

  it('analyzes the corpus only once', async () => {
    const editor = setup();
    editor.start('create-protocol');
    await vi.waitFor(() => expect(editor.suggestion.value).not.toBeNull());
    editor.close();
    editor.start('create-protocol');
    expect(api.suggestProtocolFromCorpus).toHaveBeenCalledOnce();
  });

  it('saves through the API that matches the mode', async () => {
    const editor = setup();

    editor.start('create-protocol');
    editor.form.name = 'Core';
    await editor.submit();
    expect(api.createProtocol).toHaveBeenCalledWith(5, {
      name: 'Core',
      rules: emptyRules(),
    });

    editor.start('create-version', protocol, version);
    await editor.submit();
    expect(api.createProtocolVersion).toHaveBeenCalledWith(5, 1, {
      rules: expect.objectContaining({ required_tiers: ['Gloss'] }),
    });

    editor.start('edit-draft', protocol, version);
    expect(editor.versionId.value).toBe(10);
    await editor.submit();
    expect(api.updateProtocolDraft).toHaveBeenCalledWith(5, 10, {
      rules: expect.objectContaining({ required_tiers: ['Gloss'] }),
    });
    expect(onSaved).toHaveBeenCalledTimes(3);
    expect(editor.open.value).toBe(false);
  });

  it('keeps the editor open and reports a refused save', async () => {
    const refusal = new Error('refused');
    api.createProtocol.mockRejectedValue(refusal);
    const editor = setup();
    editor.start('create-protocol');
    await editor.submit();

    expect(fail).toHaveBeenCalledWith(refusal);
    expect(editor.open.value).toBe(true);
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('resets the form when closed', () => {
    const editor = setup();
    editor.start('edit-draft', protocol, version);
    editor.close();
    expect(editor.open.value).toBe(false);
    expect(editor.mode.value).toBe('create-protocol');
    expect(editor.versionId.value).toBeNull();
    expect(editor.form.name).toBe('');
    expect(editor.form.rules).toEqual(emptyRules());
  });
});
