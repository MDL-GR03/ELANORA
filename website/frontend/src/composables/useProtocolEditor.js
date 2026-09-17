import { reactive, ref } from 'vue';

import {
  createProtocol,
  createProtocolVersion,
  suggestProtocolFromCorpus,
  updateProtocolDraft,
} from '@/api/service/protocolService';
import {
  cloneRules,
  emptyRules,
  normalizeRules,
  withSuggestedRules,
} from '@/utils/protocolRules';

/**
 * The protocol editor: a new protocol, a new draft version from an existing
 * version, or changes to a draft. Opening it analyzes the corpus once so the
 * manager can adopt rules the project's files already follow.
 */
export function useProtocolEditor({
  projectId,
  translate,
  notify,
  fail,
  onSaved,
}) {
  const open = ref(false);
  const mode = ref('create-protocol');
  const protocolId = ref(null);
  const versionId = ref(null);
  const form = reactive({ name: '', rules: emptyRules() });
  const saving = ref(false);
  const suggesting = ref(false);
  const suggestion = ref(null);

  async function analyzeCorpus() {
    suggesting.value = true;
    try {
      const { data } = await suggestProtocolFromCorpus(projectId.value);
      suggestion.value = data;
      notify(
        data.analyzed_files
          ? translate('protocols.messages.analyzed', data.analyzed_files)
          : translate('protocols.messages.nothing_to_analyze'),
        data.analyzed_files ? 'success' : 'warning'
      );
    } catch (reason) {
      fail(reason);
    } finally {
      suggesting.value = false;
    }
  }

  function start(nextMode, protocol = null, version = null) {
    mode.value = nextMode;
    protocolId.value = protocol?.protocol_id ?? null;
    versionId.value =
      nextMode === 'edit-draft' ? version.protocol_version_id : null;
    form.name = protocol?.name ?? '';
    form.rules = version ? normalizeRules(version.rules) : emptyRules();
    open.value = true;
    if (!suggestion.value) void analyzeCorpus();
  }

  function close() {
    open.value = false;
    mode.value = 'create-protocol';
    protocolId.value = null;
    versionId.value = null;
    form.name = '';
    form.rules = emptyRules();
  }

  function applySuggestion(suggestedRules) {
    form.rules = withSuggestedRules(form.rules, suggestedRules);
    notify(translate('protocols.messages.suggestions_added'));
  }

  async function submit() {
    saving.value = true;
    const rules = cloneRules(form.rules);
    try {
      if (mode.value === 'edit-draft') {
        await updateProtocolDraft(projectId.value, versionId.value, { rules });
        notify(translate('protocols.messages.draft_saved'));
      } else if (mode.value === 'create-version') {
        await createProtocolVersion(projectId.value, protocolId.value, {
          rules,
        });
        notify(translate('protocols.messages.version_created'));
      } else {
        await createProtocol(projectId.value, { name: form.name, rules });
        notify(translate('protocols.messages.draft_created'));
      }
      open.value = false;
      await onSaved();
    } catch (reason) {
      fail(reason);
    } finally {
      saving.value = false;
    }
  }

  return {
    open,
    mode,
    versionId,
    form,
    saving,
    suggesting,
    suggestion,
    start,
    close,
    applySuggestion,
    submit,
  };
}
