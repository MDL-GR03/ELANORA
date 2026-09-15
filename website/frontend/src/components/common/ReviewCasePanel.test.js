// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia } from 'pinia';

import { createI18n } from 'vue-i18n';

import ja from '@/locales/ja.json';
import { englishI18n } from '@/testing/i18n';
import ReviewCasePanel from './ReviewCasePanel.vue';
import reviewService from '@/api/service/reviewService';

vi.mock('@/api/service/reviewService', () => ({
  default: {
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    updateTask: vi.fn(),
    transition: vi.fn(),
    comment: vi.fn(),
    requestRevision: vi.fn(),
  },
}));
vi.mock('@/api/service/projectAssociationService', () => ({
  getProjectUsers: vi.fn().mockResolvedValue({ data: { users: [] } }),
}));

describe('ReviewCasePanel correction composer', () => {
  beforeEach(() => vi.clearAllMocks());

  it('submits multiple independently targeted changes for one selected file', async () => {
    reviewService.create.mockResolvedValue({
      case_id: 'case-1',
      state: 'changes_requested',
      tasks: [],
    });
    const wrapper = mount(ReviewCasePanel, {
      props: {
        projectId: 12,
        uploadId: 9,
        filenames: ['elan_files/subject.eaf'],
        composerOnly: true,
        requestChangesOnCreate: true,
      },
      global: {
        plugins: [createPinia(), englishI18n()],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: true,
          ArchivedReviewList: true,
          RouterLink: true,
        },
      },
    });

    await wrapper.get('input[maxlength="200"]').setValue('Precise review');
    await wrapper.get('.file-selector input').setValue(true);
    await wrapper.get('.change-request-draft textarea').setValue('Fix A1');
    const firstInputs = wrapper.findAll('.change-target-grid input');
    await firstInputs[0].setValue('translation');
    await firstInputs[1].setValue('A1');
    await firstInputs[2].setValue('100');
    await firstInputs[3].setValue('250');

    await wrapper.get('.add-change').trigger('click');
    const changes = wrapper.findAll('.change-request-draft');
    await changes[1].get('textarea').setValue('Fix A2');
    const secondInputs = changes[1].findAll('.change-target-grid input');
    await secondInputs[1].setValue('A2');
    await wrapper.get('form').trigger('submit');

    expect(reviewService.create).toHaveBeenCalledWith(
      12,
      expect.objectContaining({
        initial_comment: null,
        tasks: [
          expect.objectContaining({
            filename: 'elan_files/subject.eaf',
            instruction: 'Fix A1',
            tier_id: 'translation',
            annotation_id: 'A1',
            start_ms: 100,
            end_ms: 250,
          }),
          expect.objectContaining({
            filename: 'elan_files/subject.eaf',
            instruction: 'Fix A2',
            annotation_id: 'A2',
          }),
        ],
      })
    );
  });

  it('stages a needs-more-work selection without changing server state', async () => {
    reviewService.list.mockResolvedValueOnce([
      {
        case_id: 'case-2',
        project_id: 12,
        upload_id: 9,
        resubmitted_upload_id: 10,
        contributor_id: 4,
        response_branch: 'correction-10',
        title: 'Review correction',
        state: 'resubmitted',
        assigned_to: 2,
        creator_name: 'MDL',
        comments: [],
        tasks: [
          {
            task_id: 'task-1',
            filename: 'elan_files/subject.eaf',
            instruction: 'Correct this annotation',
            status: 'addressed',
          },
        ],
      },
    ]);
    const wrapper = mount(ReviewCasePanel, {
      props: { projectId: 12, projectName: 'test', canManage: true },
      global: {
        plugins: [createPinia(), englishI18n()],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: true,
          ArchivedReviewList: true,
          RouterLink: true,
        },
      },
    });
    await flushPromises();

    await wrapper.get('.reopen-action').trigger('click');

    expect(reviewService.updateTask).not.toHaveBeenCalled();
    expect(wrapper.get('.reopen-action').text()).toContain(
      'Cancel correction request'
    );
    expect(wrapper.find('.accept-action').exists()).toBe(false);
    expect(
      wrapper.get('.revision-feedback textarea').attributes()
    ).toHaveProperty('required');
    expect(wrapper.get('.request-another-revision').text()).toContain(
      'Send revision request (1)'
    );
    expect(wrapper.find('.reply').exists()).toBe(false);

    await wrapper.get('.comparison-disclosure').trigger('click');
    wrapper
      .getComponent({ name: 'ConflictMergeView' })
      .vm.$emit('open-review', {
        annotation_id: 'A1',
        tier_id: 'translation',
        start_ms: 100,
        end_ms: 250,
        change_kinds: ['removed'],
      });
    await wrapper.vm.$nextTick();

    expect(wrapper.get('.revision-feedback textarea').element.value).toBe('');
    expect(wrapper.get('.revision-targets-heading').text()).toContain(
      'Selected corrections1'
    );
    expect(wrapper.get('.revision-target').text()).toContain('A1');
    expect(wrapper.get('.revision-target').text()).toContain('translation');
    expect(
      wrapper.get('.request-another-revision').attributes('disabled')
    ).toBe(undefined);
  });

  it('presents a legacy reopened task as one recoverable reviewer decision', async () => {
    reviewService.list.mockResolvedValueOnce([
      {
        case_id: 'case-legacy',
        project_id: 12,
        upload_id: 9,
        resubmitted_upload_id: 10,
        contributor_id: 4,
        title: 'Review correction',
        state: 'resubmitted',
        assigned_to: 2,
        creator_name: 'MDL',
        comments: [],
        tasks: [
          {
            task_id: 'task-legacy',
            filename: 'elan_files/subject.eaf',
            instruction: 'Correct this annotation',
            status: 'reopened',
          },
        ],
      },
    ]);
    const wrapper = mount(ReviewCasePanel, {
      props: { projectId: 12, canManage: true },
      global: {
        plugins: [createPinia(), englishI18n()],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: true,
          ArchivedReviewList: true,
          RouterLink: true,
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).not.toContain('Revision not sent');
    expect(wrapper.text()).not.toContain('Reviewer reconsidering');
    expect(wrapper.get('.task-status').text()).toBe('Decision needed');
    expect(wrapper.get('.reopen-action').text()).toContain(
      'Cancel correction request'
    );
    expect(wrapper.find('.accept-action').exists()).toBe(false);

    await wrapper.get('.reopen-action').trigger('click');

    expect(wrapper.find('.case-next-step').exists()).toBe(false);
    expect(wrapper.get('.reopen-action').text()).toContain(
      'Request another revision'
    );
    expect(wrapper.get('.accept-action').text()).toContain(
      'Approve correction'
    );
    expect(reviewService.updateTask).not.toHaveBeenCalled();
  });

  it('finishes the review in the task approval request and reports no project changes', async () => {
    const item = {
      case_id: 'case-no-change',
      project_id: 12,
      upload_id: 9,
      resubmitted_upload_id: 10,
      contributor_id: 4,
      title: 'Review correction',
      state: 'resubmitted',
      assigned_to: 2,
      creator_name: 'MDL',
      comments: [],
      tasks: [
        {
          task_id: 'task-1',
          filename: 'elan_files/subject.eaf',
          instruction: 'Restore the annotation',
          status: 'addressed',
        },
      ],
    };
    reviewService.list.mockResolvedValueOnce([item]);
    reviewService.updateTask.mockResolvedValueOnce({
      ...item,
      state: 'resolved',
      resubmitted_upload_status: 'no_changes',
      tasks: [{ ...item.tasks[0], status: 'accepted' }],
    });
    const wrapper = mount(ReviewCasePanel, {
      props: { projectId: 12, canManage: true },
      global: {
        plugins: [createPinia(), englishI18n()],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: true,
          ArchivedReviewList: true,
          RouterLink: true,
        },
      },
    });
    await flushPromises();

    await wrapper.get('.accept-action').trigger('click');
    await flushPromises();

    expect(reviewService.updateTask).toHaveBeenCalledWith(
      12,
      'case-no-change',
      'task-1',
      'accepted'
    );
    expect(reviewService.transition).not.toHaveBeenCalled();
  });

  it('shows an active review in Japanese without untranslated keys', async () => {
    reviewService.list.mockResolvedValueOnce([
      {
        case_id: 'case-ja',
        project_id: 12,
        upload_id: 9,
        resubmitted_upload_id: null,
        contributor_id: 4,
        title: 'グロスの修正',
        state: 'changes_requested',
        assigned_to: 2,
        creator_name: 'MDL',
        comments: [],
        tasks: [
          {
            task_id: 'task-ja',
            filename: 'elan_files/subject.eaf',
            instruction: 'A1 を修正してください',
            status: 'requested',
            tier_id: 'gloss',
            start_ms: 100,
            end_ms: null,
          },
        ],
      },
    ]);
    const i18n = createI18n({
      legacy: false,
      locale: 'ja',
      fallbackLocale: 'en',
      messages: { ja },
    });
    const wrapper = mount(ReviewCasePanel, {
      props: { projectId: 12, canManage: true },
      global: {
        plugins: [createPinia(), i18n],
        stubs: {
          FontAwesomeIcon: true,
          ConflictMergeView: true,
          ArchivedReviewList: true,
          RouterLink: true,
        },
      },
    });
    await flushPromises();

    expect(wrapper.get('#review-cases-title').text()).toBe('修正依頼');
    expect(wrapper.get('.state-badge').text()).toBe('変更依頼中');
    expect(wrapper.get('.task-status').text()).toBe('変更が必要');
    expect(wrapper.get('.task-targets').text()).toContain('時間：100–終了 ms');
    expect(wrapper.text()).toContain('修正版ファイルを待っています');
    expect(wrapper.text()).not.toMatch(/reviewCases\./);
  });
});
