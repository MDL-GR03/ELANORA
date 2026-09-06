<template>
  <div id="app">
    <AppHeader class="navbar" />
    <main class="content">
      <router-view v-slot="{ Component }"
        ><Suspense
          ><component :is="Component" /><template #fallback
            ><PageLoader /></template></Suspense
      ></router-view>
    </main>
    <AppFooter class="footer" />
  </div>
</template>

<script setup>
import AppHeader from '@/components/layout/AppHeader.vue';
import AppFooter from '@/components/layout/AppFooter.vue';
import PageLoader from '@/components/common/PageLoader.vue';

import '@css/default-layout.css';
</script>
