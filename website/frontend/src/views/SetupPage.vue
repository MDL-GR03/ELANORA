<template>
  <main class="setup-page">
    <section class="setup-shell" aria-labelledby="setup-title">
      <aside class="setup-preview" :style="previewTheme">
        <p class="setup-wordmark">ELANORA</p>
        <div>
          <p class="setup-step">Institution workspace</p>
          <h2>{{ form.instance_name || 'Your research portal' }}</h2>
          <p>{{ form.institution_name || 'Your institution' }}</p>
        </div>
        <div class="preview-card">
          <span class="preview-dot"></span>
          <div>
            <strong>Live identity preview</strong
            ><small>Accessible, consistent, and reversible later.</small>
          </div>
        </div>
      </aside>

      <div class="setup-form-panel">
        <header>
          <p class="eyebrow">First-time setup</p>
          <h1 id="setup-title">Create your institution workspace</h1>
          <p>
            This one-time form creates the installation owner and visual
            identity.
          </p>
        </header>

        <form @submit.prevent="submit">
          <fieldset>
            <legend>Installation access</legend>
            <label
              >Setup token<input
                v-model="setupToken"
                type="password"
                autocomplete="off"
                required
            /></label>
          </fieldset>
          <fieldset>
            <legend>Institution</legend>
            <div class="form-grid">
              <label
                >Workspace name<input
                  v-model.trim="form.instance_name"
                  required
                  maxlength="100"
              /></label>
              <label
                >Institution name<input
                  v-model.trim="form.institution_name"
                  required
                  maxlength="100"
              /></label>
              <label
                >Contact email<input
                  v-model.trim="form.contact_email"
                  type="email"
                  required
              /></label>
              <label
                >Institution domain<input
                  v-model.trim="form.domain"
                  placeholder="university.example"
                  required
              /></label>
              <label
                >Timezone<input v-model.trim="form.timezone" required
              /></label>
              <label for="setup-default-language"
                >Language
                <AppSelect
                  id="setup-default-language"
                  v-model="form.default_language"
                  :options="languageOptions"
                />
              </label>
            </div>
          </fieldset>
          <fieldset>
            <legend>Visual identity</legend>
            <div class="color-grid">
              <label v-for="color in colors" :key="color.key"
                >{{ color.label }}<input v-model="form[color.key]" type="color"
              /></label>
            </div>
          </fieldset>
          <fieldset>
            <legend>First administrator</legend>
            <div class="form-grid">
              <label
                >Username<input
                  v-model.trim="form.admin_username"
                  required
                  minlength="3"
              /></label>
              <label
                >Email<input
                  v-model.trim="form.admin_email"
                  type="email"
                  required
              /></label>
              <label
                >First name<input v-model.trim="form.admin_first_name" required
              /></label>
              <label
                >Last name<input v-model.trim="form.admin_last_name" required
              /></label>
              <label
                >Affiliation<input
                  v-model.trim="form.admin_affiliation"
                  required
              /></label>
              <label
                >Department<input v-model.trim="form.admin_department" required
              /></label>
              <label
                >Password<input
                  v-model="form.password"
                  type="password"
                  minlength="12"
                  autocomplete="new-password"
                  required
              /></label>
              <label
                >Confirm password<input
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
            {{ submitting ? 'Creating workspace…' : 'Create workspace' }}
          </button>
        </form>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import setupService from '@/api/service/setupService';
import AppSelect from '@/components/common/AppSelect.vue';
import { useAppInfoStore } from '@/stores/appInfo';

const languageOptions = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'Français' },
];

const router = useRouter();
const appInfoStore = useAppInfoStore();
const setupToken = ref('');
const error = ref('');
const submitting = ref(false);
const colors = [
  { key: 'primary_color', label: 'Primary' },
  { key: 'secondary_color', label: 'Secondary' },
  { key: 'accent_color', label: 'Accent' },
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
    error.value = 'The administrator passwords do not match.';
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
      requestError.response?.data?.detail || 'Setup could not be completed.';
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped src="@/assets/css/setup.css"></style>
