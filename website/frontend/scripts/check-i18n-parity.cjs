/* global require, __dirname, console, process */
const fs = require('node:fs');
const path = require('node:path');

const localeDirectory = path.resolve(__dirname, '../src/locales');
const languages = ['en', 'fr', 'ja'];
const protectedNamespaces = [
  'acceptedHistory',
  'contributionDetails',
  'contributionResolution',
  'contributionWorkspace',
  'researchScopes',
  'reviewArchive',
  'uploadPage',
];
const locales = Object.fromEntries(
  languages.map((language) => [
    language,
    JSON.parse(
      fs.readFileSync(path.join(localeDirectory, `${language}.json`), 'utf8')
    ),
  ])
);

function leafPaths(value, prefix = '') {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return [prefix];
  }
  return Object.entries(value).flatMap(([key, child]) =>
    leafPaths(child, prefix ? `${prefix}.${key}` : key)
  );
}

function valueAt(value, dottedPath) {
  return dottedPath.split('.').reduce((current, key) => current?.[key], value);
}

const failures = [];
for (const namespace of protectedNamespaces) {
  const referencePaths = leafPaths(locales.en[namespace], namespace);
  for (const language of languages.slice(1)) {
    for (const key of referencePaths) {
      const value = valueAt(locales[language], key);
      if (typeof value !== 'string' || value.trim() === '') {
        failures.push(`${language}: ${key}`);
      }
    }
  }
}

if (failures.length) {
  console.error('Missing protected translations:\n' + failures.join('\n'));
  process.exit(1);
}

console.log(`Translation parity passed for: ${protectedNamespaces.join(', ')}`);
