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

export function findPatternSeparator(pattern) {
  let depth = 0;
  for (const character of pattern) {
    if (character === '{') depth += 1;
    else if (character === '}') depth -= 1;
    else if (depth === 0 && KNOWN_NAMING_SEPARATORS.includes(character)) {
      return character;
    }
  }
  return '_';
}

function collapsedCharacterRegex(value) {
  let output = '';
  let index = 0;
  while (index < value.length) {
    const character = value[index];
    let characterClass = '';
    if (/\p{L}/u.test(character)) characterClass = '\\p{L}';
    else if (/\p{N}/u.test(character)) characterClass = '\\p{N}';
    else characterClass = character.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    let run = 1;
    while (
      index + run < value.length &&
      ((/\p{L}/u.test(character) && /\p{L}/u.test(value[index + run])) ||
        (/\p{N}/u.test(character) && /\p{N}/u.test(value[index + run])) ||
        character === value[index + run])
    ) {
      run += 1;
    }
    output +=
      characterClass === '\\p{L}' || characterClass === '\\p{N}'
        ? `${characterClass}{${run}}`
        : characterClass.repeat(run);
    index += run;
  }
  return output;
}

export async function inferPatternComponents({
  pattern,
  example,
  showPrompt,
  translate,
}) {
  const separator = findPatternSeparator(pattern);
  const patternBlocks = splitPatternBlocks(pattern, separator);
  const exampleBlocks = example.split(separator);
  if (patternBlocks.length !== exampleBlocks.length) {
    return {
      components: null,
      error: translate('configureNamingStandards.patternExampleBlockCount'),
    };
  }

  const components = extractPatternComponents(pattern);
  let inferenceError = '';

  async function assignRegexAndAcceptedValues(component, value) {
    if (/^\p{L}+$/u.test(value)) component.type = 'L';
    else if (/^\p{N}+$/u.test(value)) component.type = 'D';
    else component.type = 'O';

    if (component.name.startsWith('prefix_')) {
      component.regex = /^\p{L}+$/u.test(value)
        ? `\\p{L}{${value.length}}`
        : /^\p{N}+$/u.test(value)
          ? `\\p{N}{${value.length}}`
          : collapsedCharacterRegex(value);
      component.accepted_values = [value];
      component.accepted_values_str = value;
      return;
    }
    if (component.type === 'L') {
      component.regex = `\\p{L}{${value.length}}`;
      component.accepted_values = [value];
      component.accepted_values_str = value;
      return;
    }
    if (component.type === 'D') {
      component.regex = `\\p{N}{${value.length}}`;
      const accepted = await showPrompt(
        translate('configureNamingStandards.promptExtractedValue', {
          name: component.name,
          value,
          length: value.length,
          example: value.length === 3 ? '001-150' : '01-99',
        }),
        '',
        (input) => {
          if (!input) return false;
          return (
            normalizeNumericAcceptedValues(input, value.length).error || false
          );
        },
        'text'
      );
      const normalized =
        accepted && accepted.trim()
          ? normalizeNumericAcceptedValues(accepted, value.length).values
          : [value];
      component.accepted_values = normalized;
      component.accepted_values_str = normalized.join(', ');
      return;
    }
    component.regex = '.+';
    component.accepted_values = [];
    component.accepted_values_str = '';
  }

  async function processBlock(componentNames, value) {
    if (!componentNames.length || !value) return;
    const typeGroups = splitTypeGroups(value);
    let componentIndex = 0;
    let groupIndex = 0;
    while (
      componentIndex < componentNames.length &&
      groupIndex < typeGroups.length
    ) {
      if (
        componentNames.length - componentIndex >
        typeGroups.length - groupIndex
      ) {
        const remaining = typeGroups[groupIndex].length;
        const componentsLeft = componentNames.length - componentIndex;
        const validator = (input) => {
          const normalized = (input ?? '').toString().trim();
          if (!normalized) return 'Please enter a correct numbered value.';
          if (!/^\d+$/.test(normalized)) return 'Please enter a valid number.';
          const number = Number.parseInt(normalized, 10);
          if (number < 1) return 'Length must be at least 1.';
          if (number > remaining) return `Length must not exceed ${remaining}.`;
          return false;
        };
        const promptedLength = await showPrompt(
          `Ambiguous block "${typeGroups[groupIndex]}": Please specify the length for component "${componentNames[componentIndex]}"`,
          Math.floor(remaining / componentsLeft),
          validator,
          'number'
        );
        const length = Number.parseInt(promptedLength, 10);
        if (!length || length < 1 || length > remaining) {
          inferenceError = `Invalid length for "${componentNames[componentIndex]}".`;
          return;
        }
        const component = components.find(
          (entry) => entry.name === componentNames[componentIndex]
        );
        await assignRegexAndAcceptedValues(
          component,
          typeGroups[groupIndex].slice(0, length)
        );
        const leftover = typeGroups[groupIndex].slice(length);
        if (leftover) {
          componentIndex += 1;
          if (componentNames.length - componentIndex === 1) {
            await assignRegexAndAcceptedValues(
              components.find(
                (entry) => entry.name === componentNames[componentIndex]
              ),
              leftover
            );
            componentIndex += 1;
            groupIndex += 1;
          } else typeGroups[groupIndex] = leftover;
        } else {
          groupIndex += 1;
          componentIndex += 1;
        }
        continue;
      }

      if (
        componentNames.length - componentIndex ===
        typeGroups.length - groupIndex
      ) {
        for (
          ;
          componentIndex < componentNames.length;
          componentIndex += 1, groupIndex += 1
        ) {
          const component = components.find(
            (entry) => entry.name === componentNames[componentIndex]
          );
          if (!component) {
            inferenceError = `Component "${componentNames[componentIndex]}" not found.`;
            return;
          }
          await assignRegexAndAcceptedValues(component, typeGroups[groupIndex]);
        }
        return;
      }

      await assignRegexAndAcceptedValues(
        components.find(
          (entry) => entry.name === componentNames[componentIndex]
        ),
        typeGroups[groupIndex]
      );
      componentIndex += 1;
      groupIndex += 1;
    }
  }

  for (let index = 0; index < patternBlocks.length; index += 1) {
    const componentNames = [
      ...patternBlocks[index].matchAll(/\{([^}]+)\}/g),
    ].map((match) => match[1]);
    if (!componentNames.length) continue;
    let value = exampleBlocks[index];
    if (componentNames[0].startsWith('prefix_')) {
      const prefix = [...value].findIndex(
        (character) => !/\p{Lu}/u.test(character)
      );
      const prefixLength = prefix === -1 ? value.length : prefix;
      await assignRegexAndAcceptedValues(
        components.find((entry) => entry.name === componentNames[0]),
        value.slice(0, prefixLength)
      );
      componentNames.shift();
      value = value.slice(prefixLength);
    }
    await processBlock(componentNames, value);
    if (inferenceError) return { components: null, error: inferenceError };
  }

  return { components, error: null };
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
