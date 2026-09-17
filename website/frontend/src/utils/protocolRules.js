// Bookkeeping for protocol rule snapshots edited in the browser.
//
// The backend refuses a rule on a tier that is not required, and language
// rules on a vocabulary that is not required. Removing a tier or vocabulary
// therefore has to remove every rule that names it, or the draft cannot be
// saved.

import { toRaw } from 'vue';

// Labels for these keys live in the locale files under protocolRules.

export const CONSTRAINT_STEREOTYPES = [
  'none',
  'Time_Subdivision',
  'Included_In',
  'Symbolic_Subdivision',
  'Symbolic_Association',
];

// Tier rules that are lists of tier names, with the check they switch on.
export const TIER_CHECKS = [
  'participant_tiers',
  'annotator_tiers',
  'vocabulary_tiers',
  'non_empty_tiers',
  'time_aligned_tiers',
];

// Every rule a severity can be attached to, in the order the editor shows.
export const RULE_KEYS = [
  'required_tiers',
  'tier_parents',
  'tier_linguistic_types',
  'required_controlled_vocabularies',
  'vocabulary_languages',
  'media_required',
  'allowed_media_mime_types',
  'participant_tiers',
  'annotator_tiers',
  'tier_languages',
  'vocabulary_tiers',
  'non_empty_tiers',
  'time_aligned_tiers',
  'linguistic_type_constraints',
  'filename_standard',
];

export const emptyRules = () => ({
  required_tiers: [],
  tier_parents: {},
  tier_linguistic_types: {},
  required_controlled_vocabularies: [],
  media_required: false,
  allowed_media_mime_types: [],
  vocabulary_tiers: [],
  vocabulary_languages: {},
  participant_tiers: [],
  annotator_tiers: [],
  tier_languages: {},
  non_empty_tiers: [],
  time_aligned_tiers: [],
  linguistic_type_constraints: {},
  filename_standard: null,
  severities: {},
});

// A deep copy of rules that may be reactive: structuredClone refuses Vue's
// proxies, so copy the raw object underneath.
export const cloneRules = (rules) => structuredClone(toRaw(rules));

// Fill in rule families that a snapshot published before they existed lacks.
export const normalizeRules = (rules) => ({
  ...emptyRules(),
  ...cloneRules(rules || {}),
});

const ruleSize = (rules, key) => {
  const value = rules[key];
  // A filename standard is one rule, however many components it has.
  if (key === 'filename_standard') return value ? 1 : 0;
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (Array.isArray(value)) return value.length;
  return Object.keys(value || {}).length;
};

export const configuredRuleKeys = (rules) =>
  RULE_KEYS.filter((key) => ruleSize(rules, key) > 0);

export const countRules = (rules) =>
  RULE_KEYS.reduce((total, key) => total + ruleSize(rules, key), 0);

export const severityOf = (rules, key) => rules.severities?.[key] || 'error';

export const withSeverity = (rules, key, severity) => {
  const severities = { ...(rules.severities || {}) };
  // Errors are the default, so only warnings need recording.
  if (severity === 'warning') severities[key] = 'warning';
  else delete severities[key];
  return { ...rules, severities };
};

export const withTierCheck = (rules, key, tier, enabled) => {
  const tiers = (rules[key] || []).filter((name) => name !== tier);
  return { ...rules, [key]: enabled ? [...tiers, tier] : tiers };
};

export const withMappingValue = (rules, key, name, value) => {
  const mapping = { ...(rules[key] || {}) };
  const empty = Array.isArray(value) ? value.length === 0 : !value;
  if (empty) delete mapping[name];
  else mapping[name] = value;
  return { ...rules, [key]: mapping };
};

export const withoutTier = (rules, tier) => {
  const next = {
    ...rules,
    required_tiers: (rules.required_tiers || []).filter(
      (name) => name !== tier
    ),
  };
  TIER_CHECKS.forEach((key) => {
    next[key] = (rules[key] || []).filter((name) => name !== tier);
  });
  const parents = { ...(rules.tier_parents || {}) };
  Object.entries(parents).forEach(([child, parent]) => {
    if (child === tier || parent === tier) delete parents[child];
  });
  next.tier_parents = parents;
  ['tier_linguistic_types', 'tier_languages'].forEach((key) => {
    next[key] = withMappingValue(rules, key, tier, '')[key];
  });
  return next;
};

export const withoutVocabulary = (rules, vocabulary) => ({
  ...withMappingValue(rules, 'vocabulary_languages', vocabulary, []),
  required_controlled_vocabularies: (
    rules.required_controlled_vocabularies || []
  ).filter((item) => item !== vocabulary),
});

// Language identifiers typed as "en, fr" become a clean, ordered list.
export const parseLanguages = (text) =>
  [
    ...new Set(
      text
        .split(/[\s,]+/)
        .map((item) => item.trim())
        .filter(Boolean)
    ),
  ].sort();

const union = (left, right) => [...new Set([...left, ...right])];

/**
 * Add rules suggested from the corpus to the rules being edited. Lists are
 * united, per-tier mappings take the suggestion, and a media requirement is
 * never dropped.
 */
export const withSuggestedRules = (rules, suggested) => ({
  ...rules,
  required_tiers: union(rules.required_tiers, suggested.required_tiers),
  tier_parents: { ...rules.tier_parents, ...suggested.tier_parents },
  tier_linguistic_types: {
    ...rules.tier_linguistic_types,
    ...suggested.tier_linguistic_types,
  },
  required_controlled_vocabularies: union(
    rules.required_controlled_vocabularies,
    suggested.required_controlled_vocabularies
  ),
  media_required: rules.media_required || suggested.media_required,
  allowed_media_mime_types: union(
    rules.allowed_media_mime_types,
    suggested.allowed_media_mime_types
  ),
});
