<template>
  <section class="branding-panel">
    <div class="branding-preview" :style="previewTheme">
      <img :src="previewUrl" :alt="t('instanceBranding.logo_preview')" />
      <div>
        <strong>{{ form.instance_name }}</strong
        ><span>{{ form.institution_name }}</span>
      </div>
    </div>
    <form @submit.prevent="save">
      <div class="branding-grid">
        <label
          >{{ t('setup.fields.workspace_name')
          }}<input v-model.trim="form.instance_name" required
        /></label>
        <label
          >{{ t('setup.fields.institution_name')
          }}<input v-model.trim="form.institution_name" required
        /></label>
        <label
          >{{ t('setup.fields.contact_email')
          }}<input v-model.trim="form.contact_email" type="email" required
        /></label>
      </div>
      <div class="color-grid">
        <label v-for="color in colors" :key="color.key"
          >{{ t(`setup.colors.${color.key}`)
          }}<input v-model="form[color.key]" type="color"
        /></label>
      </div>
      <label class="logo-picker"
        >{{ t('instanceBranding.logo') }}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="selectLogo"
        />
        <small>{{ t('instanceBranding.logo_hint') }}</small>
      </label>
      <button :disabled="saving">
        {{ saving ? t('instanceBranding.saving') : t('instanceBranding.save') }}
      </button>
      <p v-if="error" role="alert">{{ error }}</p>
    </form>
  </section>
</template>

<script setup>
import { apiErrorMessage } from '@/utils/apiError';
import { useI18n } from 'vue-i18n';
import { computed, onBeforeUnmount, reactive, ref } from 'vue';
import instanceService from '@/api/service/instanceService';
import { useAppInfoStore } from '@/stores/appInfo';

const { t } = useI18n();

const emit = defineEmits(['show-message']);
const store = useAppInfoStore();
const source = store.instance;
const form = reactive({
  instance_name: source.instance_name,
  institution_name: source.institution_name,
  contact_email: source.contact_email,
  primary_color: source.primary_color,
  secondary_color: source.secondary_color,
  accent_color: source.accent_color,
});
const colors = [
  { key: 'primary_color' },
  { key: 'secondary_color' },
  { key: 'accent_color' },
];
const logoFile = ref(null);
const localPreview = ref('');
const saving = ref(false);
const error = ref('');
const previewUrl = computed(
  () =>
    localPreview.value ||
    source.logo_url ||
    '/instance/images/logos/instance-logo.png'
);
const previewTheme = computed(() => ({
  '--brand-primary': form.primary_color,
  '--brand-secondary': form.secondary_color,
}));
function selectLogo(event) {
  if (localPreview.value) URL.revokeObjectURL(localPreview.value);
  logoFile.value = event.target.files?.[0] || null;
  localPreview.value = logoFile.value
    ? URL.createObjectURL(logoFile.value)
    : '';
}
async function save() {
  saving.value = true;
  error.value = '';
  try {
    const updated = await instanceService.updateBranding({ ...form });
    if (logoFile.value) {
      await instanceService.uploadLogo(logoFile.value);
      updated.logo_url = `/api/v1/instance/logo?v=${Date.now()}`;
    }
    store.setInstance(updated);
    emit('show-message', {
      text: t('instanceBranding.saved'),
      type: 'success',
    });
  } catch (requestError) {
    error.value = apiErrorMessage(
      requestError,
      t,
      t('instanceBranding.save_failed')
    );
  } finally {
    saving.value = false;
  }
}
onBeforeUnmount(() => {
  if (localPreview.value) URL.revokeObjectURL(localPreview.value);
});
</script>

<style scoped>
.branding-panel {
  padding: clamp(1rem, 4vw, 2rem);
  display: grid;
  gap: 2rem;
}

.branding-preview {
  min-height: 8rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
  border-radius: 1rem;
  color: white;
  background: linear-gradient(
    135deg,
    var(--brand-primary),
    color-mix(in srgb, var(--brand-secondary) 65%, #17243a)
  );
}

.branding-preview img {
  width: 5rem;
  height: 5rem;
  padding: 0.35rem;
  border-radius: 0.8rem;
  object-fit: contain;
  background: white;
}

.branding-preview div {
  display: grid;
  gap: 0.3rem;
}

.branding-preview strong {
  font-size: 1.35rem;
}

.branding-preview span {
  color: #e2e8f0;
}

.branding-panel form {
  display: grid;
  gap: 1.4rem;
}

.branding-grid,
.color-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.branding-panel label {
  display: grid;
  gap: 0.4rem;
  color: #334155;
  font-weight: 650;
  font-size: 0.9rem;
}

.branding-panel input:not([type='color']) {
  min-height: 2.8rem;
  padding: 0.65rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.6rem;
}

.color-grid input {
  width: 100%;
  height: 3rem;
}

.logo-picker small {
  color: #64748b;
  font-weight: 400;
}

.branding-panel button {
  min-height: 3rem;
  border: 0;
  border-radius: 0.65rem;
  color: white;
  background: var(--primary-color);
  font-weight: 700;
}

.branding-panel p {
  color: #991b1b;
}

@media (width <= 760px) {
  .branding-grid,
  .color-grid {
    grid-template-columns: 1fr;
  }

  .branding-preview {
    align-items: flex-start;
  }
}
</style>
