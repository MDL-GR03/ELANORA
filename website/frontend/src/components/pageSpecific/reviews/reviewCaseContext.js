import { inject, provide } from 'vue';

const REVIEW_CASE_CONTEXT = Symbol('reviewCaseContext');

/**
 * Share one review panel's state and actions with the components it renders.
 *
 * A case card, its task list, next step and discussion all act on the same
 * cases, busy flag, drafts and reviewer decisions. Providing them once keeps
 * each component focused on its own markup instead of relaying dozens of
 * props and events.
 */
export function provideReviewCaseContext(context) {
  provide(REVIEW_CASE_CONTEXT, context);
  return context;
}

export function useReviewCaseContext() {
  const context = inject(REVIEW_CASE_CONTEXT, null);
  if (!context) {
    throw new Error(
      'Review case components must be rendered in a review panel'
    );
  }
  return context;
}
