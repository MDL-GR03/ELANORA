import { describe, expect, it } from 'vitest';

import {
  RULE_LABELS,
  configuredRuleKeys,
  countRules,
  emptyRules,
  normalizeRules,
  parseLanguages,
  severityOf,
  withSeverity,
  withTierCheck,
  withoutTier,
  withoutVocabulary,
} from './protocolRules';

// Mirrors ProtocolRules in website/backend/app/schema/protocol.py.
const BACKEND_RULE_KEYS = [
  'allowed_media_mime_types',
  'annotator_tiers',
  'linguistic_type_constraints',
  'media_required',
  'non_empty_tiers',
  'participant_tiers',
  'required_controlled_vocabularies',
  'required_tiers',
  'tier_languages',
  'tier_linguistic_types',
  'tier_parents',
  'time_aligned_tiers',
  'vocabulary_languages',
  'vocabulary_tiers',
];

describe('protocol rules', () => {
  it('knows every rule family the backend accepts', () => {
    expect(Object.keys(RULE_LABELS).sort()).toEqual(BACKEND_RULE_KEYS);
    expect(Object.keys(emptyRules()).sort()).toEqual(
      [...BACKEND_RULE_KEYS, 'severities'].sort()
    );
  });

  it('fills in families missing from older snapshots without losing rules', () => {
    const rules = normalizeRules({ required_tiers: ['utterance'] });

    expect(rules.required_tiers).toEqual(['utterance']);
    expect(rules.non_empty_tiers).toEqual([]);
    expect(rules.severities).toEqual({});
  });

  it('removes a tier from every rule that names it', () => {
    const rules = {
      ...emptyRules(),
      required_tiers: ['utterance', 'gloss', 'translation'],
      tier_parents: { gloss: 'utterance', translation: 'gloss' },
      tier_linguistic_types: { gloss: 'gloss-type' },
      tier_languages: { gloss: 'en', translation: 'fr' },
      participant_tiers: ['gloss', 'utterance'],
      annotator_tiers: ['gloss'],
      vocabulary_tiers: ['gloss'],
      non_empty_tiers: ['gloss'],
      time_aligned_tiers: ['utterance', 'gloss'],
    };

    const next = withoutTier(rules, 'gloss');

    expect(next).toEqual({
      ...emptyRules(),
      required_tiers: ['utterance', 'translation'],
      tier_parents: {},
      tier_linguistic_types: {},
      tier_languages: { translation: 'fr' },
      participant_tiers: ['utterance'],
      time_aligned_tiers: ['utterance'],
    });
  });

  it('removes vocabulary language rules with their vocabulary', () => {
    const rules = {
      ...emptyRules(),
      required_controlled_vocabularies: ['greetings', 'signs'],
      vocabulary_languages: { greetings: ['en'], signs: ['fr'] },
    };

    const next = withoutVocabulary(rules, 'greetings');

    expect(next.required_controlled_vocabularies).toEqual(['signs']);
    expect(next.vocabulary_languages).toEqual({ signs: ['fr'] });
  });

  it('records only warnings, since errors are the default', () => {
    const warned = withSeverity(emptyRules(), 'non_empty_tiers', 'warning');
    expect(warned.severities).toEqual({ non_empty_tiers: 'warning' });
    expect(severityOf(warned, 'non_empty_tiers')).toBe('warning');
    expect(severityOf(warned, 'required_tiers')).toBe('error');

    const restored = withSeverity(warned, 'non_empty_tiers', 'error');
    expect(restored.severities).toEqual({});
  });

  it('counts and lists configured rules across families', () => {
    let rules = { ...emptyRules(), required_tiers: ['a', 'b'] };
    rules = withTierCheck(rules, 'non_empty_tiers', 'a', true);
    rules = withTierCheck(rules, 'non_empty_tiers', 'a', true);
    rules.linguistic_type_constraints = { 'gloss-type': 'Included_In' };

    expect(rules.non_empty_tiers).toEqual(['a']);
    expect(countRules(rules)).toBe(4);
    expect(configuredRuleKeys(rules)).toEqual([
      'required_tiers',
      'non_empty_tiers',
      'linguistic_type_constraints',
    ]);
  });

  it('parses typed language lists', () => {
    expect(parseLanguages(' fr, en  en,,')).toEqual(['en', 'fr']);
    expect(parseLanguages('')).toEqual([]);
  });
});
