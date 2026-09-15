import { nextTick, reactive, ref } from 'vue';
import { describe, expect, it, vi } from 'vitest';

import { useContributionWorkspace } from './useContributionWorkspace';

function setup({ query = {}, uploads = [], loaded = true, admin = true } = {}) {
  const route = reactive({ query: { ...query } });
  const router = {
    replace: vi.fn(async ({ query: next }) => {
      route.query = next;
    }),
  };
  const pendingUploads = ref(uploads);
  const uploadsLoaded = ref(loaded);
  const notify = vi.fn();
  const workspace = useContributionWorkspace({
    route,
    router,
    pendingUploads,
    uploadsLoaded,
    canAdminister: ref(admin),
    translate: (key) => key,
    notify,
  });
  return { route, router, pendingUploads, uploadsLoaded, notify, workspace };
}

const five = { upload_id: 5 };
const seven = { upload_id: 7 };

describe('useContributionWorkspace', () => {
  it('derives the view, keeping history to administrators', () => {
    expect(
      setup({ query: { view: 'reviews' } }).workspace.activeView.value
    ).toBe('reviews');
    expect(
      setup({ query: { view: 'history' }, admin: false }).workspace.activeView
        .value
    ).toBe('queue');
    expect(
      setup({ query: { view: 'history' } }).workspace.activeView.value
    ).toBe('history');
  });

  it('opens a workspace on the contribution named in the URL', async () => {
    const { route, workspace } = setup({ uploads: [five, seven] });

    await workspace.openWorkspace('details', seven);

    expect(route.query).toMatchObject({
      view: 'queue',
      workspace: 'details',
      upload: 7,
    });
    expect(workspace.selectedUpload.value).toStrictEqual(seven);
    expect(workspace.workspaceTitle.value).toBe(
      'contributionWorkspace.modes.details.title'
    );
  });

  it('ignores an unknown workspace mode', () => {
    const { workspace } = setup({
      query: { workspace: 'delete-everything', upload: '5' },
      uploads: [five],
    });
    expect(workspace.workspaceMode.value).toBe('');
    expect(workspace.selectedUpload.value).toBeNull();
  });

  it('closes a workspace whose contribution is no longer pending, and says so', async () => {
    const { route, pendingUploads, notify } = setup({
      query: { view: 'queue', workspace: 'details', upload: '5' },
      uploads: [five, seven],
    });
    expect(route.query.workspace).toBe('details');

    // Another administrator accepted #5; the next refresh no longer lists it.
    pendingUploads.value = [seven];
    await nextTick();
    await nextTick();

    expect(route.query.workspace).toBeUndefined();
    expect(route.query.upload).toBeUndefined();
    expect(notify).toHaveBeenCalledWith(
      'contributionWorkspace.messages.noLongerPending',
      'info',
      { id: 5 }
    );
  });

  it('does not close a deep-linked workspace before the queue has loaded', async () => {
    const { route, uploadsLoaded, pendingUploads, notify } = setup({
      query: { workspace: 'resolution', upload: '5' },
      uploads: [],
      loaded: false,
    });
    await nextTick();
    expect(route.query.workspace).toBe('resolution');

    pendingUploads.value = [five];
    uploadsLoaded.value = true;
    await nextTick();

    expect(route.query.workspace).toBe('resolution');
    expect(notify).not.toHaveBeenCalled();
  });

  it('closes a workspace that names no contribution at all', async () => {
    const { route } = setup({
      query: { workspace: 'details' },
      uploads: [five],
    });
    await nextTick();
    expect(route.query.workspace).toBeUndefined();
  });

  it('leaves no workspace behind when switching views', async () => {
    const { route, workspace } = setup({
      query: {
        view: 'reviews',
        case: 'c1',
        resubmission: '9',
        workspace: 'details',
        upload: '5',
      },
      uploads: [five],
    });

    await workspace.setActiveView('queue');

    expect(route.query).toEqual({ view: 'queue' });
  });

  it('shows a correction case without a lingering workspace', async () => {
    const { route, workspace } = setup({
      query: { workspace: 'correction', upload: '5' },
      uploads: [five],
    });

    await workspace.showReviewCase('case-3');

    expect(route.query).toEqual({ view: 'reviews', case: 'case-3' });
  });
});
