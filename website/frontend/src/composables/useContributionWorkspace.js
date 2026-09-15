import { computed, watch } from 'vue';

const WORKSPACE_MODES = ['details', 'correction', 'resolution'];

/**
 * Which part of the contribution page is showing, kept in the URL.
 *
 * The URL is the only source of truth for the view and the open workspace, so
 * links and the back button work. The workspace's contribution is derived from
 * the loaded queue rather than copied into separate state, so it always refers
 * to the contribution the URL names.
 */
export function useContributionWorkspace({
  route,
  router,
  pendingUploads,
  uploadsLoaded,
  canAdminister,
  translate,
  notify = () => {},
}) {
  const activeView = computed(() => {
    if (route.query.view === 'reviews') return 'reviews';
    if (route.query.view === 'history' && canAdminister.value) return 'history';
    return 'queue';
  });
  const highlightedCaseId = computed(() => String(route.query.case || ''));
  const resubmissionUploadId = computed(() =>
    route.query.resubmission ? Number(route.query.resubmission) : null
  );
  const workspaceMode = computed(() => {
    const mode = String(route.query.workspace || '');
    return WORKSPACE_MODES.includes(mode) ? mode : '';
  });
  const workspaceUploadId = computed(() =>
    route.query.upload ? Number(route.query.upload) : null
  );
  const selectedUpload = computed(() => {
    if (!workspaceMode.value || workspaceUploadId.value === null) return null;
    return (
      pendingUploads.value.find(
        (upload) => upload.upload_id === workspaceUploadId.value
      ) || null
    );
  });
  const workspaceTitle = computed(() =>
    translate(
      `contributionWorkspace.modes.${workspaceMode.value || 'default'}.title`
    )
  );
  const workspaceDescription = computed(() =>
    workspaceMode.value
      ? translate(
          `contributionWorkspace.modes.${workspaceMode.value}.description`
        )
      : ''
  );

  function replaceQuery(changes, removals = []) {
    const query = { ...route.query, ...changes };
    for (const key of removals) delete query[key];
    return router.replace({ query });
  }

  function setActiveView(view) {
    const removals = ['workspace', 'upload'];
    if (view !== 'reviews') removals.push('case', 'resubmission');
    return replaceQuery({ view }, removals);
  }

  function openWorkspace(mode, upload) {
    return replaceQuery({
      view: 'queue',
      workspace: mode,
      upload: upload.upload_id,
    });
  }

  function closeWorkspace() {
    return replaceQuery({}, ['workspace', 'upload']);
  }

  function openLinkedReview(reviewCase) {
    const changes = { view: 'reviews', case: reviewCase.case_id };
    const removals = ['workspace', 'upload', 'resubmission'];
    if (reviewCase.resubmitted_upload_id) {
      changes.resubmission = reviewCase.resubmitted_upload_id;
      removals.pop();
    }
    return replaceQuery(changes, removals);
  }

  function showReviewCase(caseId) {
    return replaceQuery({ view: 'reviews', case: caseId }, [
      'workspace',
      'upload',
    ]);
  }

  // A workspace whose contribution is no longer pending, for instance because
  // another administrator accepted it, would otherwise leave the page without
  // its tabs and holding a URL that points nowhere. Close it and say why.
  watch(
    () => [
      workspaceMode.value,
      workspaceUploadId.value,
      uploadsLoaded.value,
      pendingUploads.value,
    ],
    ([mode, uploadId, loaded]) => {
      if (!mode) return;
      if (uploadId !== null && !loaded) return;
      if (uploadId !== null && selectedUpload.value) return;
      void closeWorkspace();
      if (uploadId !== null) {
        notify('contributionWorkspace.messages.noLongerPending', 'info', {
          id: uploadId,
        });
      }
    },
    { immediate: true }
  );

  return {
    activeView,
    highlightedCaseId,
    resubmissionUploadId,
    workspaceMode,
    selectedUpload,
    workspaceTitle,
    workspaceDescription,
    setActiveView,
    openWorkspace,
    closeWorkspace,
    openLinkedReview,
    showReviewCase,
  };
}
