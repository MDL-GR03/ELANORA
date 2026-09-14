import { describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import {
  buildNamingStandardPayload,
  useNamingStandardMutations,
} from './useNamingStandardMutations';

function createSubject(overrides = {}) {
  const draft = ref({
    name: ' Session standard ',
    project_file_type_id: 7,
    pattern: '{prefix_EAF}_{session}',
    description: ' Session files ',
    components: [
      {
        name: 'session',
        regex: '\\p{N}{3}',
        description: 'Session number',
        order: 1,
        accepted_values: ['001'],
      },
    ],
  });
  const dependencies = {
    projectId: ref(42),
    draft,
    standards: ref([]),
    extractionError: ref(''),
    store: {
      addNamingStandard: vi.fn().mockResolvedValue(undefined),
      deleteNamingStandard: vi.fn().mockResolvedValue(undefined),
    },
    confirmAction: vi.fn().mockResolvedValue(true),
    eventMessages: { addMessage: vi.fn() },
    translate: (key) => `translated:${key}`,
    clearExampleCache: vi.fn(),
    resetDraft: vi.fn(),
    ...overrides,
  };
  return {
    dependencies,
    mutations: useNamingStandardMutations(dependencies),
  };
}

describe('buildNamingStandardPayload', () => {
  it('normalizes outer text and maps component ownership', () => {
    const { dependencies } = createSubject();

    expect(buildNamingStandardPayload(dependencies.draft.value, 42)).toEqual({
      name: 'Session standard',
      project_id: 42,
      project_file_type_id: 7,
      pattern: '{prefix_EAF}_{session}',
      description: 'Session files',
      components: [
        {
          name: 'session',
          regex: '\\p{N}{3}',
          description: 'Session number',
          order: 1,
          accepted_values: ['001'],
          project_file_type_id: 7,
        },
      ],
    });
  });
});

describe('useNamingStandardMutations', () => {
  it('rejects a case-insensitive duplicate for the same file type', async () => {
    const standards = ref([
      { name: 'session STANDARD', project_file_type_id: 7 },
    ]);
    const { dependencies, mutations } = createSubject({ standards });

    await expect(mutations.addStandard()).resolves.toBe(false);
    expect(dependencies.store.addNamingStandard).not.toHaveBeenCalled();
    expect(dependencies.eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.addFailedDuplicate',
      'error',
      7000
    );
  });

  it('rejects components without a usable regex', async () => {
    const { dependencies, mutations } = createSubject();
    dependencies.draft.value.components[0].regex = '   ';

    await expect(mutations.addStandard()).resolves.toBe(false);
    expect(dependencies.store.addNamingStandard).not.toHaveBeenCalled();
    expect(dependencies.eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.addFailedEmptyRegex',
      'error',
      7000
    );
  });

  it('adds a valid standard and resets transient state', async () => {
    const { dependencies, mutations } = createSubject();

    await expect(mutations.addStandard()).resolves.toBe(true);
    expect(dependencies.store.addNamingStandard).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Session standard', project_id: 42 }),
      42
    );
    expect(dependencies.clearExampleCache).toHaveBeenCalledOnce();
    expect(dependencies.resetDraft).toHaveBeenCalledOnce();
    expect(dependencies.eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.addSuccess',
      'success',
      4000
    );
  });

  it('does not delete when confirmation is declined', async () => {
    const confirmAction = vi.fn().mockResolvedValue(false);
    const { dependencies, mutations } = createSubject({ confirmAction });

    await expect(mutations.deleteStandard(9)).resolves.toBe(false);
    expect(dependencies.store.deleteNamingStandard).not.toHaveBeenCalled();
    expect(dependencies.clearExampleCache).not.toHaveBeenCalled();
  });

  it('deletes a confirmed standard and reports success', async () => {
    const { dependencies, mutations } = createSubject();

    await expect(mutations.deleteStandard(9)).resolves.toBe(true);
    expect(dependencies.store.deleteNamingStandard).toHaveBeenCalledWith(9, 42);
    expect(dependencies.clearExampleCache).toHaveBeenCalledOnce();
    expect(dependencies.eventMessages.addMessage).toHaveBeenCalledWith(
      'translated:configureNamingStandards.eventMessages.deleteSuccess',
      'success',
      4000
    );
  });
});
