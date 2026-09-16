const toRegExp = (pat) => {
  if (!pat) return null;
  if (pat instanceof RegExp) return pat;
  const s = String(pat);
  const anchored = s.startsWith('^') && s.endsWith('$') ? s : `^${s}$`;
  try {
    return new RegExp(anchored, 'u');
  } catch {
    return null;
  }
};

const parseRange = (s) => {
  if (typeof s !== 'string') return null;
  const m = /^(\d+)-(\d+)$/.exec(s.trim());
  if (!m) return null;
  const minS = m[1],
    maxS = m[2];
  return { min: Number(minS), max: Number(maxS), width: minS.length, raw: s };
};

const matchesRangeValue = (value, range) => {
  const n = Number(value);
  if (Number.isNaN(n)) return false;
  if (String(value).length !== range.width) return false;
  if (value !== n.toString().padStart(range.width, '0')) return false;
  return n >= range.min && n <= range.max;
};

const isRegexLiteral = (s) => /^\/.*\/[gimsuy]*$/.test(s);

function checkRegex(comp, value) {
  const rx = toRegExp(comp.regex);
  return !rx || rx.test(value);
}

function isAcceptedValueRegex(av, value) {
  if (!isRegexLiteral(av)) return false;
  try {
    const parts = /^\/(.*)\/([gimsuy]*)$/.exec(av);
    const r = new RegExp(parts[1], parts[2]);
    return r.test(value);
  } catch {
    return false;
  }
}

function isAcceptedValueRange(av, value) {
  const r = parseRange(av);
  return r && matchesRangeValue(value, r);
}

function checkAcceptedValues(comp, value) {
  if (!Array.isArray(comp.acceptedValues) || comp.acceptedValues.length === 0)
    return true;
  for (const av of comp.acceptedValues) {
    if (av == null) continue;
    if (isAcceptedValueRegex(av, value)) return true;
    if (isAcceptedValueRange(av, value)) return true;
    if (String(av) === value) return true;
  }
  return false;
}

function checkFixedValue(comp, value) {
  if (comp.fixedValue == null) return true;
  if (String(comp.fixedValue) !== String(value)) {
    return false;
  }
  return true;
}

function checkNumericRangeString(comp, value) {
  const r = parseRange(comp.numericRange);
  return r && matchesRangeValue(value, r);
}

function checkNumericRangeObject(comp, value) {
  const num = Number(value);
  if (Number.isNaN(num)) {
    return false;
  }
  if (
    typeof comp.numericRange.width === 'number' &&
    String(value).length !== comp.numericRange.width
  ) {
    return false;
  }
  if (
    typeof comp.numericRange.min === 'number' &&
    num < comp.numericRange.min
  ) {
    return false;
  }
  if (
    typeof comp.numericRange.max === 'number' &&
    num > comp.numericRange.max
  ) {
    return false;
  }
  return true;
}

function checkNumericRange(comp, value) {
  if (!comp.numericRange) return true;
  if (typeof comp.numericRange === 'string') {
    return checkNumericRangeString(comp, value);
  }
  if (typeof comp.numericRange === 'object') {
    return checkNumericRangeObject(comp, value);
  }
  return false;
}

function checkComponent(comp, value) {
  return (
    checkRegex(comp, value) &&
    checkAcceptedValues(comp, value) &&
    checkFixedValue(comp, value) &&
    checkNumericRange(comp, value)
  );
}

/** Read a component in whichever shape the API or the editor supplied it. */
function normalizeComponent(component) {
  let acceptedValues = [];
  if (Array.isArray(component.acceptedValues)) {
    acceptedValues = component.acceptedValues;
  } else if (Array.isArray(component.accepted_values)) {
    acceptedValues = component.accepted_values;
  } else if (typeof component.accepted_values_str === 'string') {
    acceptedValues = component.accepted_values_str
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  }

  return {
    ...component,
    regex: component.regex ?? component.pattern ?? null,
    acceptedValues,
    fixedValue:
      component.fixedValue ?? component.fixed_value ?? component.value ?? null,
    numericRange:
      component.numericRange ??
      component.numeric_range ??
      component.numericRangeValue ??
      null,
  };
}

/**
 * Match a name against a standard's pattern.
 *
 * Returns the normalised components with the value each one captured, or null
 * when the standard is unusable or the name does not fit its pattern.
 */
function matchStandard(standard, name) {
  if (!standard?.pattern || !Array.isArray(standard?.components)) {
    return null;
  }
  const components = standard.components.map(normalizeComponent);

  let pattern = standard.pattern;
  for (const component of components) {
    pattern = pattern.replace(
      new RegExp(`\\{${component.name}\\}`, 'g'),
      `(${component.regex || '.+'})`
    );
  }

  let expression;
  try {
    expression = new RegExp(`^${pattern}$`, 'u');
  } catch {
    return null;
  }

  const match = expression.exec(name);
  if (!match) return null;
  return components.map((component, index) => ({
    component,
    value: match[index + 1],
  }));
}

export function isFilenameCompliant(standard, name) {
  const nameWithoutExt = String(name || '').replace(/\.[^/.]+$/, '');
  const captured = matchStandard(standard, nameWithoutExt);
  return Boolean(
    captured?.every(({ component, value }) => checkComponent(component, value))
  );
}

/**
 * Extract components from a filename using a naming standard
 * @param {Object} standard - The naming standard to use for extraction
 * @param {string} filename - The filename to extract components from (without extension)
 * @returns {Object|null} Object with component names as keys and extracted values as values, or null if extraction fails
 */
export function extractComponentsFromFilename(standard, filename) {
  if (!filename) return null;
  const captured = matchStandard(standard, filename);
  if (!captured) return null;

  const extracted = {};
  for (const { component, value } of captured) {
    if (value !== undefined) extracted[component.name] = value;
  }
  return extracted;
}
