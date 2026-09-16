import axiosClient from '@/api/apiClient';
import axios from 'axios';
import { reportClientError } from '@/utils/errorDiagnostics';

/**
 * Service for location-related API calls
 */

/**
 * Get all countries from REST Countries API
 * @returns {Promise<Object>} Response with countries data
 */
export const getCountries = async () => {
  try {
    // Use REST Countries API for comprehensive country list
    const response = await axios.get(
      'https://restcountries.com/v3.1/all?fields=name,cca2,cca3'
    );

    // Transform the data to match our expected format
    const countries = response.data
      .map((country) => ({
        country_id: country.cca2, // Use ISO 2-letter code as ID
        country_code: country.cca3, // 3-letter code
        country_name: country.name.common,
        country_name_official: country.name.official,
      }))
      .sort((a, b) => a.country_name.localeCompare(b.country_name));

    return {
      success: true,
      data: countries,
    };
  } catch (error) {
    reportClientError('Error fetching countries', error);

    // Fallback to internal API if REST Countries fails
    try {
      const fallbackResponse = await axiosClient.get('/location/countries');
      return {
        success: true,
        data: fallbackResponse.data,
      };
    } catch (fallbackError) {
      reportClientError('Fallback error fetching countries', fallbackError);
      return {
        success: false,
        error: 'Unable to fetch countries from any source',
      };
    }
  }
};

/**
 * Validate city name using OpenStreetMap Nominatim API
 * @param {string} cityName - The city name to validate
 * @param {string} countryCode - The country code (ISO 2-letter)
 * @returns {Promise<Object>} Response with validation result
 */
export const validateCity = async (cityName, countryCode) => {
  if (!cityName || !countryCode) {
    return { success: false, error: 'City name and country code are required' };
  }

  try {
    // Search for the city using Nominatim API
    const response = await axios.get(
      'https://nominatim.openstreetmap.org/search',
      {
        params: {
          q: `${cityName}, ${countryCode}`,
          countrycodes: countryCode.toLowerCase(),
          limit: 10, // Get more results to filter better
          format: 'json',
          addressdetails: 1, // Get detailed address info for better validation
        },
        headers: {
          'User-Agent': 'ELANORA-App/1.0',
        },
      }
    );

    if (response.data && response.data.length > 0) {
      // Filter results to ensure the city actually belongs to the specified country
      const validResults = response.data.filter((result) => {
        const address = result.address;
        if (!address) return false;

        // Check if the result is actually in the specified country
        const resultCountryCode = address.country_code?.toUpperCase();
        if (resultCountryCode !== countryCode.toUpperCase()) {
          return false;
        }

        // Check if it's actually a city/town/village
        const isCity =
          address.city ||
          address.town ||
          address.village ||
          address.municipality;
        if (!isCity) return false;

        // Check if the city name matches (case insensitive)
        const resultCityName =
          address.city ||
          address.town ||
          address.village ||
          address.municipality;
        return (
          resultCityName &&
          resultCityName.toLowerCase() === cityName.toLowerCase()
        );
      });

      if (validResults.length > 0) {
        const bestResult = validResults[0];
        const address = bestResult.address;
        const resultCityName =
          address.city ||
          address.town ||
          address.village ||
          address.municipality;

        return {
          success: true,
          data: {
            isValid: true,
            cityName: resultCityName,
            fullName: bestResult.display_name,
            coordinates: {
              lat: parseFloat(bestResult.lat),
              lon: parseFloat(bestResult.lon),
            },
          },
        };
      } else {
        return {
          success: true,
          data: {
            isValid: false,
            message: 'City not found in the specified country',
          },
        };
      }
    } else {
      return {
        success: true,
        data: {
          isValid: false,
          message: 'City not found in the specified country',
        },
      };
    }
  } catch (error) {
    reportClientError('Error validating city', error);
    return {
      success: false,
      error: 'Unable to validate city',
    };
  }
};

/**
 * Validate postal code format and existence
 * @param {string} postalCode - The postal code to validate
 * @param {string} countryCode - The country code (ISO 2-letter)
 * @returns {Promise<Object>} Response with validation result
 */
export const validatePostalCode = async (postalCode, countryCode) => {
  if (!postalCode || !countryCode) {
    return {
      success: false,
      error: 'Postal code and country code are required',
    };
  }

  // Basic postal code format validation by country
  const postalCodePatterns = {
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

  const pattern = postalCodePatterns[countryCode.toUpperCase()];

  if (!pattern) {
    // If no pattern exists for the country, accept any non-empty value
    return {
      success: true,
      data: {
        isValid: postalCode.trim().length > 0,
        message:
          postalCode.trim().length > 0
            ? 'Format not validated for this country'
            : 'Postal code is required',
      },
    };
  }

  const isValid = pattern.test(postalCode.trim());

  return {
    success: true,
    data: {
      isValid,
      message: isValid
        ? 'Valid postal code format'
        : 'Invalid postal code format for this country',
    },
  };
};

/**
 * Validate postal code against city using Nominatim API
 * @param {string} postalCode - The postal code to validate
 * @param {string} cityName - The city name
 * @param {string} countryCode - The country code (ISO 2-letter)
 * @returns {Promise<Object>} Response with validation result
 */
export const validatePostalCodeInCity = async (
  postalCode,
  cityName,
  countryCode
) => {
  if (!postalCode || !cityName || !countryCode) {
    return {
      success: false,
      error: 'Postal code, city name, and country code are required',
    };
  }

  try {
    // Search by postal code first
    const response = await axios.get(
      'https://nominatim.openstreetmap.org/search',
      {
        params: {
          postalcode: postalCode,
          countrycodes: countryCode.toLowerCase(),
          limit: 10,
          format: 'json',
          addressdetails: 1,
        },
        headers: {
          'User-Agent': 'ELANORA-App/1.0',
        },
      }
    );

    if (response.data && response.data.length > 0) {
      // Check if any result matches our city
      const validResults = response.data.filter((result) => {
        const address = result.address;
        if (!address) return false;

        const resultCity =
          address.city ||
          address.town ||
          address.village ||
          address.municipality;
        return (
          resultCity && resultCity.toLowerCase() === cityName.toLowerCase()
        );
      });

      if (validResults.length > 0) {
        return {
          success: true,
          data: {
            isValid: true,
            message: 'Postal code matches the specified city',
          },
        };
      } else {
        // Get the cities that do match this postal code
        const actualCities = response.data
          .map(
            (r) =>
              r.address?.city ||
              r.address?.town ||
              r.address?.village ||
              r.address?.municipality
          )
          .filter(Boolean)
          .slice(0, 3);

        return {
          success: true,
          data: {
            isValid: false,
            message:
              actualCities.length > 0
                ? `Postal code belongs to: ${actualCities.join(', ')}`
                : 'Postal code does not match the specified city',
            suggestions: actualCities,
          },
        };
      }
    } else {
      return {
        success: true,
        data: {
          isValid: false,
          message: 'Postal code not found',
        },
      };
    }
  } catch (error) {
    reportClientError('Error validating postal code in city', error);
    return {
      success: false,
      error: 'Unable to validate postal code',
    };
  }
};

/**
 * Validate street name (basic validation)
 * @param {string} streetName - The street name to validate
 * @returns {Object} Validation result
 */
export const validateStreetName = (streetName) => {
  if (!streetName || streetName.trim().length === 0) {
    return {
      isValid: false,
      message: 'Street name is required',
    };
  }

  if (streetName.trim().length < 2) {
    return {
      isValid: false,
      message: 'Street name must be at least 2 characters long',
    };
  }

  // Check for suspicious patterns
  if (/^\d+$/.test(streetName.trim())) {
    return {
      isValid: false,
      message: 'Street name cannot be only numbers',
    };
  }

  return {
    isValid: true,
    message: 'Valid street name',
  };
};

/**
 * Validate street name against city using Nominatim API
 * @param {string} streetName - The street name to validate
 * @param {string} cityName - The city name
 * @param {string} countryCode - The country code (ISO 2-letter)
 * @returns {Promise<Object>} Response with validation result
 */
export const validateStreetInCity = async (
  streetName,
  cityName,
  countryCode
) => {
  if (!streetName || !cityName || !countryCode) {
    return {
      success: false,
      error: 'Street name, city name, and country code are required',
    };
  }

  try {
    // Search for the street in the specific city
    const response = await axios.get(
      'https://nominatim.openstreetmap.org/search',
      {
        params: {
          q: `${streetName}, ${cityName}`,
          countrycodes: countryCode.toLowerCase(),
          limit: 5,
          format: 'json',
          addressdetails: 1,
        },
        headers: {
          'User-Agent': 'ELANORA-App/1.0',
        },
      }
    );

    if (response.data && response.data.length > 0) {
      // Check if any result matches our city
      const validResults = response.data.filter((result) => {
        const address = result.address;
        if (!address) return false;

        const resultCity =
          address.city ||
          address.town ||
          address.village ||
          address.municipality;
        return (
          resultCity && resultCity.toLowerCase() === cityName.toLowerCase()
        );
      });

      if (validResults.length > 0) {
        return {
          success: true,
          data: {
            isValid: true,
            message: 'Street found in the specified city',
            suggestions: validResults.map((r) => r.display_name),
          },
        };
      } else {
        return {
          success: true,
          data: {
            isValid: false,
            message: 'Street not found in the specified city',
            suggestions: response.data.map((r) => r.display_name).slice(0, 3),
          },
        };
      }
    } else {
      return {
        success: true,
        data: {
          isValid: false,
          message: 'Street not found',
        },
      };
    }
  } catch (error) {
    reportClientError('Error validating street in city', error);
    return {
      success: false,
      error: 'Unable to validate street',
    };
  }
};
