export const KNOWN_NAMING_SEPARATORS = ['_', '-', '.', ' '];

export function normalizeNumericAcceptedValues(input, length) {
  const inputParts = (input ?? '')
    .split(/[,;]/)
    .map((value) => value.trim())
    .filter(Boolean);
  const values = [];
  for (const part of inputParts) {
    if (/^\d+-\d+$/.test(part)) {
      const [start, end] = part.split('-').map(Number);
      if (Number.isNaN(start) || Number.isNaN(end) || start > end) {
        return { error: `Invalid range "${part}".` };
      }
      const startString = start.toString().padStart(length, '0');
      const endString = end.toString().padStart(length, '0');
      if (startString.length > length || endString.length > length) {
        return { error: `Values in range "${part}" exceed ${length} digits.` };
      }
      values.push(`${startString}-${endString}`);
    } else if (/^\d+$/.test(part)) {
      const value = Number(part).toString().padStart(length, '0');
      if (value.length > length) {
        return { error: `Value "${part}" exceeds ${length} digits.` };
      }
      values.push(value);
    } else {
      return { error: `Invalid value "${part}".` };
    }
  }
  return { values, error: null };
}

export function extractPatternComponents(pattern) {
  return [...pattern.matchAll(/\{([^}]+)\}/g)].map((match, index) => ({
    name: match[1],
    regex: '',
    description: '',
    order: index + 1,
    accepted_values: [],
    accepted_values_str: '',
  }));
}

export function splitTypeGroups(value) {
  if (!value) return [];
  const groups = [];
  let current = '';
  let lastType = null;
  const charType = (character) => {
    if (/[A-Z]/.test(character)) return 'U';
    if (/[a-z]/.test(character)) return 'L';
    if (/\d/.test(character)) return 'D';
    return 'O';
  };

  for (const character of value) {
    const type = charType(character);
    if (lastType === null || type === lastType) current += character;
    else {
      groups.push(current);
      current = character;
    }
    lastType = type;
  }
  if (current) groups.push(current);
  return groups;
}

export function splitPatternBlocks(pattern, separator) {
  const blocks = [];
  let current = '';
  let depth = 0;
  for (const character of pattern) {
    if (character === '{') depth += 1;
    if (character === '}') depth -= 1;
    if (character === separator && depth === 0) {
      blocks.push(current);
      current = '';
    } else current += character;
  }
  if (current) blocks.push(current);
  return blocks;
}

export function acceptedValuesPlaceholder(regex) {
  if (!regex) return 'Accepted Values';

  const letterMatch = regex.match(/\\p\{L\}\{(\d+)\}/u);
  if (letterMatch) {
    const length = Number.parseInt(letterMatch[1]);
    if (length === 1) return 'e.g. A, É, Z';
    if (length === 2) return 'e.g. AB, ÉZ, ZA';
    if (length === 3) return 'e.g. ABC, ÉZA, CAB';
    return `e.g. ${'ABCDEFGH'.slice(0, length)}, ${'ÉÉÉ'.repeat(length).slice(0, length)}`;
  }

  const digitMatch = regex.match(/\\p\{N\}\{(\d+)\}/u);
  if (digitMatch) {
    const length = Number.parseInt(digitMatch[1]);
    if (length === 1) return 'e.g. 1, 2, 3';
    if (length === 2) return 'e.g. 01, 12, 99';
    return `e.g. ${'0'.repeat(length - 1)}1, ${'9'.repeat(length)}`;
  }

  return 'Accepted Values';
}
