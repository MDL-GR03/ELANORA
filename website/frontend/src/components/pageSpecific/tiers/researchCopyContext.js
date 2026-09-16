import { inject, provide } from 'vue';

const RESEARCH_COPY_CONTEXT = Symbol('researchCopyContext');

/**
 * Share one research-copy selection with the steps that edit it. The page
 * owns the selection so it survives switching to the topics tab and back.
 */
export function provideResearchCopyContext(context) {
  provide(RESEARCH_COPY_CONTEXT, context);
  return context;
}

export function useResearchCopyContext() {
  const context = inject(RESEARCH_COPY_CONTEXT, null);
  if (!context) {
    throw new Error(
      'Research copy steps must be rendered inside the research copy workspace'
    );
  }
  return context;
}
