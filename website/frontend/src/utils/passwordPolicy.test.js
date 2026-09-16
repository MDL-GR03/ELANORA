import { describe, expect, it } from 'vitest';

import {
  meetsPasswordPolicy,
  passwordChecksOf,
  passwordRequirementList,
  passwordStrengthOf,
} from './passwordPolicy';

describe('passwordPolicy', () => {
  it.each([
    ['the quiet river bends west', true],
    ['tidal marsh 7 lanterns', true],
    ['Sh0rt!Pass', false],
    ['aaaaaaaaaaaaaaaaaaaa', false],
    ['abcabcabcabcabcabc', false],
    ['abcdefghijklmnop', false],
    ['a'.repeat(60) + 'é'.repeat(7), false],
  ])('judges %j as acceptable: %s', (password, expected) => {
    expect(meetsPasswordPolicy(password)).toBe(expected);
  });

  it('asks for length, not capitals, digits or symbols', () => {
    expect(passwordChecksOf('the quiet river bends west')).toEqual({
      length: true,
      pattern: true,
    });
  });

  it.each([
    ['', 'weak'],
    ['Analytical1!', 'weak'],
    ['tidal marsh lamps', 'medium'],
    ['the quiet river bends west', 'strong'],
  ])('rates %j as %s', (password, expected) => {
    expect(passwordStrengthOf(password)).toBe(expected);
  });

  it('lists the requirements with the minimum length', () => {
    expect(
      passwordRequirementList('short', (key, params) =>
        params ? `${key}:${params.min}` : key
      )
    ).toEqual([
      { key: 'length', text: 'passwordPolicy.length:15', valid: false },
      { key: 'pattern', text: 'passwordPolicy.pattern:15', valid: true },
    ]);
  });
});
