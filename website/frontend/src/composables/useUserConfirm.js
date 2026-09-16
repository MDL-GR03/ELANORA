import { getCurrentInstance, h, render } from 'vue';
import UserConfirm from '@/components/common/UserConfirm.vue';

/**
 * Ask the researcher to confirm an action in a modal dialog.
 *
 * Call it during setup. The dialog is rendered outside the component tree, so
 * it borrows the caller's app context; without it the dialog could not reach
 * the app's translations.
 */
export function useUserConfirm() {
  const appContext = getCurrentInstance()?.appContext ?? null;
  return (options) => {
    return new Promise((resolve) => {
      const container = document.createElement('div');
      document.body.appendChild(container);

      const vnode = h(UserConfirm, {
        ...options,
        modelValue: true,
        onConfirm: () => {
          cleanup();
          resolve(true);
        },
        onCancel: () => {
          cleanup();
          resolve(false);
        },
        'onUpdate:modelValue': (v) => {
          if (!v) cleanup();
        },
      });

      function cleanup() {
        render(null, container);
        document.body.removeChild(container);
      }

      vnode.appContext = appContext;
      render(vnode, container);
    });
  };
}
