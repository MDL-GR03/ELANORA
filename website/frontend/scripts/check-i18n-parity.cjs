/* global require, __dirname, console, process */
const fs = require('node:fs');
const path = require('node:path');

const localeDirectory = path.resolve(__dirname, '../src/locales');
const languages = ['en', 'fr', 'ja'];
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

// Every key English defines must exist in every language, and no language may
// carry a key English lacks: a missing key shows the researcher a raw key path,
// and an extra one is a misspelling or a leftover nothing can reach.
const failures = [];
const referencePaths = new Set(leafPaths(locales.en));
for (const language of languages.slice(1)) {
  for (const key of referencePaths) {
    const value = valueAt(locales[language], key);
    if (typeof value !== 'string' || value.trim() === '') {
      failures.push(`${language}: missing ${key}`);
    }
  }
  for (const key of leafPaths(locales[language])) {
    if (!referencePaths.has(key)) {
      failures.push(`${language}: not in English ${key}`);
    }
  }
}

if (failures.length) {
  console.error('Translation parity failed:\n' + failures.join('\n'));
  process.exit(1);
}

console.log(
  `Translation parity passed: ${referencePaths.size} keys in ${languages.join(', ')}`
);
