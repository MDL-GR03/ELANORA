<template>
  <section class="branding-panel">
    <div class="branding-preview" :style="previewTheme">
      <img :src="previewUrl" alt="Institution logo preview" />
      <div>
        <strong>{{ form.instance_name }}</strong
        ><span>{{ form.institution_name }}</span>
      </div>
    </div>
    <form @submit.prevent="save">
      <div class="branding-grid">
        <label
          >Workspace name<input v-model.trim="form.instance_name" required
        /></label>
        <label
          >Institution name<input v-model.trim="form.institution_name" required
        /></label>
        <label
          >Contact email<input
            v-model.trim="form.contact_email"
            type="email"
            required
        /></label>
      </div>
      <div class="color-grid">
        <label v-for="color in colors" :key="color.key"
          >{{ color.label }}<input v-model="form[color.key]" type="color"
        /></label>
      </div>
      <label class="logo-picker"
        >Institution logo
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="selectLogo"
        />
        <small
          >PNG, JPEG, or WebP; maximum 5 MB. It will be safely
          normalized.</small
        >
      </label>
      <button :disabled="saving">
        {{ saving ? 'Saving…' : 'Save institution identity' }}
      </button>
      <p v-if="error" role="alert">{{ error }}</p>
    </form>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref } from 'vue';
import instanceService from '@/api/service/instanceService';
import { useAppInfoStore } from '@/stores/appInfo';

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
  { key: 'primary_color', label: 'Primary' },
  { key: 'secondary_color', label: 'Secondary' },
  { key: 'accent_color', label: 'Accent' },
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
      text: 'Institution identity updated.',
      type: 'success',
    });
  } catch (requestError) {
    error.value =
      requestError.response?.data?.detail ||
      'The institution identity could not be saved.';
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
