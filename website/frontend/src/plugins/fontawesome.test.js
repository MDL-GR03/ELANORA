import { describe, expect, it } from 'vitest';
import { library } from '@fortawesome/fontawesome-svg-core';

import './fontawesome';

const sources = import.meta.glob(
  ['../**/*.vue', '../**/*.js', '!../**/*.test.js'],
  {
    query: '?raw',
    import: 'default',
    eager: true,
  }
);

function namedIcons() {
  const named = new Set();
  for (const text of Object.values(sources)) {
    for (const [, style, name] of text.matchAll(
      /fa-(solid|regular) fa-([a-z0-9-]+)/g
    )) {
      named.add(`${style === 'regular' ? 'far' : 'fas'}:${name}`);
    }
    for (const [, name] of text.matchAll(
      /<font-awesome-icon[^>]*\sicon="([a-z0-9-]+)"/g
    )) {
      named.add(`fas:${name.replace(/^fa-/, '')}`);
    }
  }
  return [...named].sort();
}

describe('icon registration', () => {
  it('registers every icon a template or script names', () => {
    const definitions = library.definitions;
    const missing = namedIcons().filter((entry) => {
      const [prefix, name] = entry.split(':');
      return !definitions[prefix]?.[name];
    });
    expect(missing).toEqual([]);
  });

  it('finds the icons it is checking', () => {
    expect(namedIcons()).toContain('fas:trash');
  });
});
