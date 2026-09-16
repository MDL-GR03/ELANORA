<template>
  <main class="login-page">
    <section class="login-shell" aria-labelledby="login-title">
      <aside class="login-context">
        <div>
          <p class="product-mark" aria-label="ELANORA">ELANORA</p>
          <p class="product-kicker">{{ t('login.platform_subtitle') }}</p>
        </div>

        <div class="institution-card">
          <span class="institution-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path
                d="M12 3 3 8v2h18V8l-9-5ZM5 12v6H3v2h18v-2h-2v-6h-2v6h-2v-6h-2v6h-2v-6H9v6H7v-6H5Z"
              />
            </svg>
          </span>
          <div>
            <p class="institution-label">{{ t('login.instance_label') }}</p>
            <h2>{{ instanceName }}</h2>
            <p>{{ institutionName }}</p>
          </div>
        </div>

        <ul class="feature-list" :aria-label="t('login.capabilities')">
          <li v-for="feature in features" :key="feature">
            <span aria-hidden="true">✓</span>{{ feature }}
          </li>
        </ul>
      </aside>

      <div class="login-card">
        <header class="login-header">
          <p class="eyebrow">{{ instanceName }}</p>
          <h1 id="login-title">{{ t('login.welcome_back') }}</h1>
          <p>{{ t('login.sign_in_instruction') }}</p>
        </header>

        <form class="login-form" @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="login">{{ t('login.login') }}</label>
            <input
              id="login"
              v-model.trim="loginForm.login"
              name="username"
              type="text"
              autocomplete="username"
              required
              :placeholder="t('login.login_placeholder')"
              :disabled="userStore.authState.loading"
            />
          </div>

          <div class="form-group">
            <div class="password-label-row">
              <label for="password">{{ t('login.password') }}</label>
              <router-link to="/forgot-password">
                {{ t('login.forgot_password') }}
              </router-link>
            </div>
            <input
              id="password"
              v-model="loginForm.password"
              name="password"
              type="password"
              autocomplete="current-password"
              required
              :placeholder="t('login.password_placeholder')"
              :disabled="userStore.authState.loading"
            />
          </div>

          <button
            type="submit"
            class="login-button"
            :disabled="userStore.authState.loading"
          >
            {{
              userStore.authState.loading
                ? t('login.logging_in')
                : t('login.login')
            }}
          </button>
        </form>

        <footer class="login-footer">
          <p>
            {{ t('login.have_invitation') }}
            <router-link to="/register">{{
              t('login.join_project')
            }}</router-link>
          </p>
          <router-link to="/contact">{{ t('login.need_help') }}</router-link>
        </footer>
      </div>
    </section>
  </main>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

import { useEventMessageStore } from '@stores/eventMessage';
import { useAppInfoStore } from '@stores/appInfo';
import { useUserStore } from '@stores/user';
import { reportClientError } from '@/utils/errorDiagnostics';

const router = useRouter();
const { t } = useI18n();
const appInfoStore = useAppInfoStore();
const userStore = useUserStore();
const eventMessageStore = useEventMessageStore();

const loginForm = reactive({ login: '', password: '' });
const instanceName = computed(
  () => appInfoStore.instance?.instance_name || t('login.default_instance')
);
const institutionName = computed(
  () =>
    appInfoStore.instance?.institution_name || t('login.institution_fallback')
);
const features = computed(() => [
  t('login.features.collaborative_elan'),
  t('login.features.conflict_detection'),
  t('login.features.annotation_workflows'),
  t('login.features.project_repositories'),
  t('login.features.secure_instance'),
]);

onMounted(() => {
  const message = localStorage.getItem('logoutMessage');
  if (message) {
    eventMessageStore.addMessage(message, 'success');
    localStorage.removeItem('logoutMessage');
  }
});

const handleLogin = async () => {
  try {
    const response = await userStore.login({
      login: loginForm.login,
      password: loginForm.password,
    });

    if (response.needs_verification) {
      eventMessageStore.addMessage(
        response.message || t('login.email_verification_required'),
        'warning'
      );
      await router.push({
        name: 'EmailVerificationPage',
        query: { email: response.email, freshCode: 'true' },
      });
      return;
    }
    if (!userStore.user) {
      eventMessageStore.addMessage(t('login.login_connection_error'), 'error');
      return;
    }
    eventMessageStore.addMessage(t('login.login_success'), 'success');
    await router.push({ name: 'HomePage' });
  } catch (error) {
    reportClientError('Login error', error);
    const message = apiErrorMessage(
      error,
      t,
      t('login.login_connection_error')
    );
    eventMessageStore.addMessage(message, 'error');
  }
};
</script>

<style scoped src="@/assets/css/login.css"></style>
