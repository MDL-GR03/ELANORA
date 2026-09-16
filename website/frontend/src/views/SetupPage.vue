<template>
  <main class="setup-page">
    <section class="setup-shell" aria-labelledby="setup-title">
      <aside class="setup-preview" :style="previewTheme">
        <p class="setup-wordmark">ELANORA</p>
        <div>
          <p class="setup-step">{{ t('setup.preview.step') }}</p>
          <h2>{{ form.instance_name || t('setup.preview.workspace') }}</h2>
          <p>{{ form.institution_name || t('setup.preview.institution') }}</p>
        </div>
        <div class="preview-card">
          <span class="preview-dot"></span>
          <div>
            <strong>{{ t('setup.preview.title') }}</strong
            ><small>{{ t('setup.preview.hint') }}</small>
          </div>
        </div>
      </aside>

      <div class="setup-form-panel">
        <header>
          <p class="eyebrow">{{ t('setup.eyebrow') }}</p>
          <h1 id="setup-title">{{ t('setup.title') }}</h1>
          <p>{{ t('setup.description') }}</p>
        </header>

        <form @submit.prevent="submit">
          <fieldset>
            <legend>{{ t('setup.sections.access') }}</legend>
            <label
              >{{ t('setup.fields.setup_token')
              }}<input
                v-model="setupToken"
                type="password"
                autocomplete="off"
                required
            /></label>
          </fieldset>
          <fieldset>
            <legend>{{ t('setup.sections.institution') }}</legend>
            <div class="form-grid">
              <label
                >{{ t('setup.fields.workspace_name')
                }}<input
                  v-model.trim="form.instance_name"
                  required
                  maxlength="100"
              /></label>
              <label
                >{{ t('setup.fields.institution_name')
                }}<input
                  v-model.trim="form.institution_name"
                  required
                  maxlength="100"
              /></label>
              <label
                >{{ t('setup.fields.contact_email')
                }}<input
                  v-model.trim="form.contact_email"
                  type="email"
                  required
              /></label>
              <label
                >{{ t('setup.fields.domain')
                }}<input
                  v-model.trim="form.domain"
                  placeholder="university.example"
                  required
              /></label>
              <label
                >{{ t('setup.fields.timezone')
                }}<input v-model.trim="form.timezone" required
              /></label>
              <label for="setup-default-language"
                >{{ t('setup.fields.language') }}
                <AppSelect
                  id="setup-default-language"
                  v-model="form.default_language"
                  :options="languageOptions"
                />
              </label>
            </div>
          </fieldset>
          <fieldset>
            <legend>{{ t('setup.sections.identity') }}</legend>
            <div class="color-grid">
              <label v-for="color in colors" :key="color.key"
                >{{ t(`setup.colors.${color.key}`)
                }}<input v-model="form[color.key]" type="color"
              /></label>
            </div>
          </fieldset>
          <fieldset>
            <legend>{{ t('setup.sections.administrator') }}</legend>
            <div class="form-grid">
              <label
                >{{ t('setup.fields.username')
                }}<input
                  v-model.trim="form.admin_username"
                  required
                  minlength="3"
              /></label>
              <label
                >{{ t('setup.fields.email')
                }}<input v-model.trim="form.admin_email" type="email" required
              /></label>
              <label
                >{{ t('setup.fields.first_name')
                }}<input v-model.trim="form.admin_first_name" required
              /></label>
              <label
                >{{ t('setup.fields.last_name')
                }}<input v-model.trim="form.admin_last_name" required
              /></label>
              <label
                >{{ t('setup.fields.affiliation')
                }}<input v-model.trim="form.admin_affiliation" required
              /></label>
              <label
                >{{ t('setup.fields.department')
                }}<input v-model.trim="form.admin_department" required
              /></label>
              <label
                >{{ t('setup.fields.password')
                }}<input
                  v-model="form.password"
                  type="password"
                  minlength="12"
                  autocomplete="new-password"
                  required
              /></label>
              <label
                >{{ t('setup.fields.password_confirmation')
                }}<input
                  v-model="form.password_confirmation"
                  type="password"
                  minlength="12"
                  autocomplete="new-password"
                  required
              /></label>
            </div>
          </fieldset>
          <p v-if="error" class="setup-error" role="alert">{{ error }}</p>
          <button type="submit" :disabled="submitting">
            {{ submitting ? t('setup.submitting') : t('setup.submit') }}
          </button>
        </form>
      </div>
    </section>
  </main>
</template>

<script setup>
import { useI18n } from 'vue-i18n';
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import setupService from '@/api/service/setupService';
import AppSelect from '@/components/common/AppSelect.vue';
import { useAppInfoStore } from '@/stores/appInfo';

const { t } = useI18n();

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
  { value: 'ja', label: '日本語' },
];

const router = useRouter();
const appInfoStore = useAppInfoStore();
const setupToken = ref('');
const error = ref('');
const submitting = ref(false);
const colors = [
  { key: 'primary_color' },
  { key: 'secondary_color' },
  { key: 'accent_color' },
];
const form = reactive({
  instance_name: '',
  institution_name: '',
  contact_email: '',
  domain: '',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
  default_language: 'en',
  primary_color: '#2563eb',
  secondary_color: '#0f766e',
  accent_color: '#d97706',
  admin_username: '',
  admin_email: '',
  admin_first_name: '',
  admin_last_name: '',
  admin_affiliation: '',
  admin_department: '',
  password: '',
  password_confirmation: '',
});
const previewTheme = computed(() => ({
  '--preview-primary': form.primary_color,
  '--preview-secondary': form.secondary_color,
  '--preview-accent': form.accent_color,
}));

async function submit() {
  if (form.password !== form.password_confirmation) {
    error.value = t('setup.errors.passwords_no_match');
    return;
  }
  submitting.value = true;
  error.value = '';
  try {
    const result = await setupService.initialize({ ...form }, setupToken.value);
    appInfoStore.setInstance(result.instance);
    window.location.assign(router.resolve({ name: 'LoginPage' }).href);
  } catch (requestError) {
    error.value =
      requestError.response?.data?.detail || t('setup.errors.failed');
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped src="@/assets/css/setup.css"></style>
