import js from '@eslint/js';
import vue from 'eslint-plugin-vue';
import vueParser from 'vue-eslint-parser';
import globals from 'globals';
import prettierConfig from 'eslint-config-prettier';

const commonGlobals = {
  ...globals.browser,
  ...globals.node,
  window: 'readonly',
  document: 'readonly',
  console: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  CustomEvent: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  requestAnimationFrame: 'readonly',
  error: 'writable',
  alert: 'readonly',
  FormData: 'readonly',
  fetch: 'readonly',
  URL: 'readonly',
  URLSearchParams: 'readonly',
  confirm: 'readonly',
  Event: 'readonly',
  ResizeObserver: 'readonly',
};

const commonParserOptions = {
  ecmaVersion: 2021,
  sourceType: 'module',
  ecmaFeatures: { jsx: true },
};

export default [
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettierConfig,
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: commonParserOptions,
      globals: commonGlobals,
    },
    plugins: { vue },
    rules: {
      'vue/max-attributes-per-line': 'off',
      'vue/html-indent': 'off',
      'vue/html-closing-bracket-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
    },
  },
  {
    files: ['**/*.js'],
    languageOptions: {
      parserOptions: commonParserOptions,
      globals: commonGlobals,
    },
  },
];
