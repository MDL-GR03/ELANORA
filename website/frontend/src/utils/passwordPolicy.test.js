import { describe, expect, it } from 'vitest';

import {
  meetsPasswordPolicy,
  passwordChecksOf,
  passwordRequirementList,
  passwordStrengthOf,
} from './passwordPolicy';

describe('passwordPolicy', () => {
  it.each([
    ['Analytical1!', true],
    ['Analytical_1', true],
    ['analytical1!', false],
    ['ANALYTICAL1!', false],
    ['Analytical!!', false],
    ['Analytical12', false],
    ['Ab1!', false],
    ['A1!' + 'a'.repeat(70), false],
    ['Aé1!' + 'é'.repeat(35), false],
  ])('judges %j as acceptable: %s', (password, expected) => {
    expect(meetsPasswordPolicy(password)).toBe(expected);
  });

  it.each([
    ['', 'weak'],
    ['short', 'weak'],
    ['lowercaseonly', 'weak'],
    ['Lowercase1', 'medium'],
    ['Analytical1!', 'strong'],
  ])('rates the password %j as %s', (password, expected) => {
    expect(passwordStrengthOf(password)).toBe(expected);
  });

  it('reports nothing met for an empty password', () => {
    expect(Object.values(passwordChecksOf('')).some(Boolean)).toBe(false);
  });

  it('lists the requirements in order, translated', () => {
    expect(passwordRequirementList('Analytical1', (key) => `t:${key}`)).toEqual(
      [
        { key: 'length', text: 't:passwordPolicy.length', valid: true },
        { key: 'uppercase', text: 't:passwordPolicy.uppercase', valid: true },
        { key: 'lowercase', text: 't:passwordPolicy.lowercase', valid: true },
        { key: 'number', text: 't:passwordPolicy.number', valid: true },
        { key: 'special', text: 't:passwordPolicy.special', valid: false },
      ]
    );
  });
});
