/**
 * Pure helpers relating a project's EAF files (tier groups) to research
 * topics. A topic names tiers; a file covers the topic to the extent it
 * contains those tiers.
 */

export function flattenTiers(tiers = []) {
  return tiers.flatMap((tier) => [tier, ...flattenTiers(tier.children || [])]);
}

export function tierNamesOf(group) {
  return new Set(flattenTiers(group?.tiers).map((tier) => tier.tier_name));
}

export function topicTiersIn(group, topic) {
  const names = tierNamesOf(group);
  return topic.tier_names.filter((name) => names.has(name));
}

export function topicCoverageOf(group, topic) {
  return topicTiersIn(group, topic).length;
}

export function filesCoveringTopic(groups, topic) {
  return groups.filter((group) => topicCoverageOf(group, topic) > 0).length;
}

export function filesWithTier(groups, name) {
  return groups
    .filter((group) => tierNamesOf(group).has(name))
    .map((group) => group.elan_file_name);
}

export function allTierNamesOf(groups) {
  return [
    ...new Set(groups.flatMap((group) => [...tierNamesOf(group)])),
  ].sort();
}

function byFilename(a, b) {
  return a.elan_file_name.localeCompare(b.elan_file_name);
}

/** Files ordered by topic coverage (best first), then by name. */
export function rankGroupsForTopic(groups, topic) {
  if (!topic) return [...groups].sort(byFilename);
  const coverage = new Map(
    groups.map((group) => [group, topicCoverageOf(group, topic)])
  );
  return [...groups].sort(
    (a, b) => coverage.get(b) - coverage.get(a) || byFilename(a, b)
  );
}

/** The best file for a topic, only when no other file ties with it. */
export function uniqueBestGroup(rankedGroups, topic) {
  if (!topic || !rankedGroups.length) return null;
  const first = topicCoverageOf(rankedGroups[0], topic);
  const second = rankedGroups[1] ? topicCoverageOf(rankedGroups[1], topic) : -1;
  return first > second && first > 0 ? rankedGroups[0] : null;
}

/** One row per file containing at least one of the topic's tiers. */
export function topicCoverageRows(groups, topic) {
  return groups
    .map((group) => {
      const matches = topicTiersIn(group, topic);
      return {
        filename: group.elan_file_name,
        matches,
        percent: Math.round((matches.length / topic.tier_names.length) * 100),
      };
    })
    .filter((row) => row.matches.length)
    .sort(
      (a, b) =>
        b.matches.length - a.matches.length ||
        a.filename.localeCompare(b.filename)
    );
}

/** Tier names of a group that must be kept as parents of selected tiers. */
export function automaticParentNames(tiers, selectedNames) {
  const result = new Set();
  function visit(nodes, parents) {
    for (const tier of nodes) {
      if (selectedNames.has(tier.tier_name)) {
        for (const name of parents) {
          if (!selectedNames.has(name)) result.add(name);
        }
      }
      visit(tier.children || [], [...parents, tier.tier_name]);
    }
  }
  visit(tiers || [], []);
  return result;
}
