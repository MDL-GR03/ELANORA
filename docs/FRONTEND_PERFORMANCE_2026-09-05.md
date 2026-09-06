# Frontend performance remediation

## Confirmed causes

The local HTTP servers were not the principal delay: the development document
responded in about 5 ms and the health endpoint in about 3 ms. Browser-side
navigation and mounting were doing unnecessary whole-application work.

The primary header used normal anchors for Projects, Upload, and Contributions.
Each navigation therefore discarded the Vue application and reloaded its
scripts, styles, authentication state, institution state, stores, layout, and
page. All internal navigation now uses Vue Router.

Project Configuration rendered collapsed sections with `v-show`. This mounted
every editor and started their lifecycle/API work even though the user could
not see them. Sections now use conditional mounting and asynchronous component
chunks. Profile subpages use asynchronous chunks as well.

## Build evidence

Before the change, the Project Configuration route loaded approximately 69.44
kB of route JavaScript and 35.39 kB of route CSS. Its initial route shell is now
4.42 kB JavaScript and 2.58 kB CSS; an editor is downloaded and mounted only
when opened.

The Profile route previously included approximately 66.66 kB of JavaScript and
49.45 kB of CSS. Its initial shell is now 3.72 kB JavaScript and 8.22 kB CSS;
overview, settings, security, and notifications are separate chunks.

Vite polling is now enabled only for Docker bind mounts, excludes dependency,
Git, and build-output trees, and project BroadcastChannel initialization is
idempotent. These changes reduce development CPU and duplicate listeners.

## Remaining measurement work

Add Playwright browser performance tests once browser tooling is part of the
locked development dependencies. Record navigation timing, request counts, and
largest-contentful-paint for authenticated representative datasets. The next
bundle target is the shared icon and application chunks, but they should be
changed only after browser traces establish their execution or transfer cost.
# Follow-up: shared shell and request lifecycle

The application shell now supplies a route-level accessible loading state.
Project collection loading is single-flight and distinguishes an initialized
empty result from an uninitialized store. Project file metadata and naming
standards load concurrently. Duplicate pending-upload startup requests were
removed, and background polling pauses when the document is hidden.

The Font Awesome compatibility bundle remains available to older feature
screens but is no longer preloaded on every visit. It is isolated as a deferred
chunk while new shared-shell components use small inline SVGs.
