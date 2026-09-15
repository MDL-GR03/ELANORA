// Bookkeeping for protocol rule snapshots edited in the browser.
//
// The backend refuses a rule on a tier that is not required, and language
// rules on a vocabulary that is not required. Removing a tier or vocabulary
// therefore has to remove every rule that names it, or the draft cannot be
// saved.

export const CONSTRAINT_STEREOTYPES = [
  { value: 'none', label: 'No constraint (independent tier)' },
  { value: 'Time_Subdivision', label: 'Time subdivision' },
  { value: 'Included_In', label: 'Included in' },
  { value: 'Symbolic_Subdivision', label: 'Symbolic subdivision' },
  { value: 'Symbolic_Association', label: 'Symbolic association' },
];

// Tier rules that are lists of tier names, with the check they switch on.
export const TIER_CHECKS = [
  { key: 'participant_tiers', label: 'Participant named' },
  { key: 'annotator_tiers', label: 'Annotator named' },
  { key: 'vocabulary_tiers', label: 'Values from vocabulary' },
  { key: 'non_empty_tiers', label: 'No empty values' },
  { key: 'time_aligned_tiers', label: 'Time-aligned' },
];

// Every rule a severity can be attached to, in the order the editor shows.
export const RULE_LABELS = {
  required_tiers: 'Required tiers',
  tier_parents: 'Parent tiers',
  tier_linguistic_types: 'Tier linguistic types',
  required_controlled_vocabularies: 'Required vocabularies',
  vocabulary_languages: 'Vocabulary languages',
  media_required: 'Linked media',
  allowed_media_mime_types: 'Media formats',
  participant_tiers: 'Participant named',
  annotator_tiers: 'Annotator named',
  tier_languages: 'Tier languages',
  vocabulary_tiers: 'Values from vocabulary',
  non_empty_tiers: 'No empty values',
  time_aligned_tiers: 'Time-aligned tiers',
  linguistic_type_constraints: 'Linguistic type constraints',
};

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
  severities: {},
});

// Fill in rule families that a snapshot published before they existed lacks.
export const normalizeRules = (rules) => ({
  ...emptyRules(),
  ...structuredClone(rules || {}),
});

const ruleSize = (rules, key) => {
  const value = rules[key];
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (Array.isArray(value)) return value.length;
  return Object.keys(value || {}).length;
};

export const configuredRuleKeys = (rules) =>
  Object.keys(RULE_LABELS).filter((key) => ruleSize(rules, key) > 0);

export const countRules = (rules) =>
  Object.keys(RULE_LABELS).reduce(
    (total, key) => total + ruleSize(rules, key),
    0
  );

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
  TIER_CHECKS.forEach(({ key }) => {
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
