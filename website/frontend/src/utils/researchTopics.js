export function normalizeResearchTopicName(value = '') {
  return value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function editDistance(left, right) {
  const previous = Array.from(
    { length: right.length + 1 },
    (_, index) => index
  );
  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    const current = [leftIndex];
    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      current[rightIndex] = Math.min(
        current[rightIndex - 1] + 1,
        previous[rightIndex] + 1,
        previous[rightIndex - 1] +
          (left[leftIndex - 1] === right[rightIndex - 1] ? 0 : 1)
      );
    }
    previous.splice(0, previous.length, ...current);
  }
  return previous[right.length];
}

export function findSimilarResearchTopic(
  proposedName,
  topics,
  threshold = 0.78
) {
  const proposed = normalizeResearchTopicName(proposedName);
  if (!proposed) return null;
  let closest = null;
  let bestScore = 0;
  for (const topic of topics) {
    const candidate = normalizeResearchTopicName(topic.name);
    const length = Math.max(proposed.length, candidate.length);
    const score = length ? 1 - editDistance(proposed, candidate) / length : 1;
    if (score > bestScore) {
      bestScore = score;
      closest = topic;
    }
  }
  return bestScore >= threshold ? closest : null;
}
