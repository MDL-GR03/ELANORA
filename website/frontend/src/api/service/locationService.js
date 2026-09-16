import axiosClient from '@/api/apiClient';
import axios from 'axios';
import { reportClientError } from '@/utils/errorDiagnostics';

/**
 * Countries, and address checks against OpenStreetMap.
 *
 * Checks answer with a translation key rather than a sentence, so the form
 * shows the result in the researcher's language.
 */

const NOMINATIM_SEARCH = 'https://nominatim.openstreetmap.org/search';

/** Country-specific postal code formats; other countries accept any value. */
const POSTAL_CODE_PATTERNS = {
  US: /^\d{5}(-\d{4})?$/,
  CA: /^[A-Z]\d[A-Z] \d[A-Z]\d$/,
  GB: /^[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}$/,
  FR: /^\d{5}$/,
  DE: /^\d{5}$/,
  BE: /^\d{4}$/,
  NL: /^\d{4} [A-Z]{2}$/,
  IT: /^\d{5}$/,
  ES: /^\d{5}$/,
  PT: /^\d{4}-\d{3}$/,
  CH: /^\d{4}$/,
  AT: /^\d{4}$/,
  SE: /^\d{3} \d{2}$/,
  NO: /^\d{4}$/,
  DK: /^\d{4}$/,
  FI: /^\d{5}$/,
  PL: /^\d{2}-\d{3}$/,
  CZ: /^\d{3} \d{2}$/,
  SK: /^\d{3} \d{2}$/,
  HU: /^\d{4}$/,
  RO: /^\d{6}$/,
  BG: /^\d{4}$/,
  HR: /^\d{5}$/,
  SI: /^\d{4}$/,
  LU: /^\d{4}$/,
  IE: /^[A-Z]\d{2} [A-Z\d]{4}$/,
  MT: /^[A-Z]{3} \d{4}$/,
  CY: /^\d{4}$/,
  EE: /^\d{5}$/,
  LV: /^\d{4}$/,
  LT: /^\d{5}$/,
  JP: /^\d{3}-\d{4}$/,
  KR: /^\d{5}$/,
  CN: /^\d{6}$/,
  IN: /^\d{6}$/,
  AU: /^\d{4}$/,
  NZ: /^\d{4}$/,
  BR: /^\d{5}-\d{3}$/,
  MX: /^\d{5}$/,
  AR: /^\d{4}$/,
  CL: /^\d{7}$/,
  CO: /^\d{6}$/,
  PE: /^\d{5}$/,
  ZA: /^\d{4}$/,
  EG: /^\d{5}$/,
  MA: /^\d{5}$/,
  TN: /^\d{4}$/,
  DZ: /^\d{5}$/,
  RU: /^\d{6}$/,
  UA: /^\d{5}$/,
  TR: /^\d{5}$/,
  IL: /^\d{7}$/,
  AE: /^\d{5}$/,
  SA: /^\d{5}$/,
  QA: /^\d{5}$/,
  KW: /^\d{5}$/,
  BH: /^\d{3,4}$/,
  OM: /^\d{3}$/,
  TH: /^\d{5}$/,
  VN: /^\d{6}$/,
  MY: /^\d{5}$/,
  SG: /^\d{6}$/,
  PH: /^\d{4}$/,
  ID: /^\d{5}$/,
};

/** Search OpenStreetMap for places within one country. */
async function searchPlaces(params, countryCode, limit) {
  const response = await axios.get(NOMINATIM_SEARCH, {
    params: {
      ...params,
      countrycodes: countryCode.toLowerCase(),
      limit,
      format: 'json',
      addressdetails: 1,
    },
    headers: { 'User-Agent': 'ELANORA-App/1.0' },
  });
  return Array.isArray(response.data) ? response.data : [];
}

/** The locality a search result lies in, whatever OpenStreetMap calls it. */
export function localityOf(place) {
  const address = place?.address;
  return (
    address?.city ||
    address?.town ||
    address?.village ||
    address?.municipality ||
    null
  );
}

function isInCity(place, cityName) {
  return localityOf(place)?.toLowerCase() === cityName.toLowerCase();
}

/** A completed check. */
function answer(isValid, messageKey = '', messageParams = {}, extra = {}) {
  return {
    success: true,
    data: { isValid, messageKey, messageParams, ...extra },
  };
}

/**
 * Get all countries, from REST Countries or, failing that, the backend.
 * @returns {Promise<Object>} Response with countries data
 */
export const getCountries = async () => {
  try {
    const response = await axios.get(
      'https://restcountries.com/v3.1/all?fields=name,cca2,cca3'
    );
    const countries = response.data
      .map((country) => ({
        country_id: country.cca2,
        country_code: country.cca3,
        country_name: country.name.common,
        country_name_official: country.name.official,
      }))
      .sort((a, b) => a.country_name.localeCompare(b.country_name));
    return { success: true, data: countries };
  } catch (error) {
    reportClientError('Error fetching countries', error);
    try {
      const fallbackResponse = await axiosClient.get('/location/countries');
      return { success: true, data: fallbackResponse.data };
    } catch (fallbackError) {
      reportClientError('Fallback error fetching countries', fallbackError);
      return { success: false };
    }
  }
};

/** Check that a city exists in the given country. */
export const validateCity = async (cityName, countryCode) => {
  if (!cityName || !countryCode) return { success: false };
  try {
    const places = await searchPlaces(
      { q: `${cityName}, ${countryCode}` },
      countryCode,
      10
    );
    const found = places.find(
      (place) =>
        place.address?.country_code?.toUpperCase() ===
          countryCode.toUpperCase() && isInCity(place, cityName)
    );
    return answer(Boolean(found));
  } catch (error) {
    reportClientError('Error validating city', error);
    return { success: false };
  }
};

/** Check a postal code against its country's format. */
export const validatePostalCode = async (postalCode, countryCode) => {
  if (!postalCode || !countryCode) return { success: false };
  const pattern = POSTAL_CODE_PATTERNS[countryCode.toUpperCase()];
  const value = postalCode.trim();
  return answer(pattern ? pattern.test(value) : value.length > 0);
};

/** Check that a postal code belongs to the given city. */
export const validatePostalCodeInCity = async (
  postalCode,
  cityName,
  countryCode
) => {
  if (!postalCode || !cityName || !countryCode) return { success: false };
  try {
    const places = await searchPlaces(
      { postalcode: postalCode },
      countryCode,
      10
    );
    if (places.length === 0) {
      return answer(false, 'register.location.postal_code_not_found');
    }
    if (places.some((place) => isInCity(place, cityName))) {
      return answer(true, 'register.location.postal_code_in_city');
    }
    const cities = [...new Set(places.map(localityOf).filter(Boolean))].slice(
      0,
      3
    );
    return cities.length
      ? answer(
          false,
          'register.location.postal_code_belongs_to',
          { cities: cities.join(', ') },
          { suggestions: cities }
        )
      : answer(false, 'register.location.postal_code_not_in_city');
  } catch (error) {
    reportClientError('Error validating postal code in city', error);
    return { success: false };
  }
};

/** Check that a street exists in the given city. */
export const validateStreetInCity = async (
  streetName,
  cityName,
  countryCode
) => {
  if (!streetName || !cityName || !countryCode) return { success: false };
  try {
    const places = await searchPlaces(
      { q: `${streetName}, ${cityName}` },
      countryCode,
      5
    );
    if (places.length === 0) {
      return answer(false, 'register.location.street_not_found');
    }
    const inCity = places.filter((place) => isInCity(place, cityName));
    return inCity.length
      ? answer(
          true,
          'register.location.street_in_city',
          {},
          {
            suggestions: inCity.map((place) => place.display_name),
          }
        )
      : answer(
          false,
          'register.location.street_not_in_city',
          {},
          {
            suggestions: places.slice(0, 3).map((place) => place.display_name),
          }
        );
  } catch (error) {
    reportClientError('Error validating street in city', error);
    return { success: false };
  }
};
