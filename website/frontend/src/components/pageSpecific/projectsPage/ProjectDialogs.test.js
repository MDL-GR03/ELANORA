// @vitest-environment jsdom

import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { afterEach, describe, expect, it, vi } from 'vitest';

import ProjectCreateDialog from './ProjectCreateDialog.vue';
import ProjectEditDialog from './ProjectEditDialog.vue';

vi.mock('vue-i18n', () => ({
  useI18n: () => ({ t: (key) => key }),
}));
vi.mock('@stores/project', () => ({
  useProjectStore: () => ({ projects: [], initBroadcastChannel: vi.fn() }),
}));
vi.mock('@api/service/gitService', () => ({
  default: {
    createProject: vi.fn(),
    initProjectFromFolderUpload: vi.fn(),
    editProject: vi.fn(),
  },
}));

const global = {
  stubs: {
    UploadFolder: { template: '<button type="button">Upload files</button>' },
  },
};

afterEach(() => {
  document.body.innerHTML = '';
});

function mountFromOpener(component, props = {}) {
  const opener = document.createElement('button');
  document.body.append(opener);
  opener.focus();
  const wrapper = mount(component, {
    attachTo: document.body,
    props,
    global,
  });
  return { opener, wrapper };
}

describe.each([
  ['create', ProjectCreateDialog, {}],
  [
    'edit',
    ProjectEditDialog,
    {
      project: {
        project_id: 1,
        project_name: 'Corpus',
        project_description: '',
      },
    },
  ],
])('Project %s dialog', (_name, component, props) => {
  it('has labelled dialog and form controls with managed focus', async () => {
    const { opener, wrapper } = mountFromOpener(component, props);
    await nextTick();

    const dialog = wrapper.get('[role="dialog"]');
    const nameInput = wrapper.get('input');
    const description = wrapper.get('textarea');
    expect(dialog.attributes('aria-modal')).toBe('true');
    expect(dialog.attributes('aria-labelledby')).toBe(
      wrapper.get('h2').attributes('id')
    );
    expect(
      wrapper.get(`label[for="${nameInput.attributes('id')}"]`).exists()
    ).toBe(true);
    expect(
      wrapper.get(`label[for="${description.attributes('id')}"]`).exists()
    ).toBe(true);
    expect(document.activeElement).toBe(nameInput.element);

    await dialog.trigger('keydown', { key: 'Escape' });
    expect(wrapper.emitted('close')).toHaveLength(1);
    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
  });

  it('connects an invalid project name to an announced error', async () => {
    const wrapper = mount(component, { props, global });
    const input = wrapper.get('input');
    await input.setValue('');
    await input.trigger('input');
    await nextTick();

    const error = wrapper.get('[role="alert"]');
    expect(input.attributes('aria-invalid')).toBe('true');
    expect(input.attributes('aria-describedby')).toBe(error.attributes('id'));
    wrapper.unmount();
  });
});
