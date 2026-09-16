import { beforeEach, describe, expect, it, vi } from 'vitest';

const get = vi.fn();
const fallbackGet = vi.fn();

vi.mock('axios', () => ({ default: { get: (...args) => get(...args) } }));
vi.mock('@/api/apiClient', () => ({
  default: { get: (...args) => fallbackGet(...args) },
}));
vi.mock('@/utils/errorDiagnostics', () => ({ reportClientError: vi.fn() }));

import {
  getCountries,
  localityOf,
  validateCity,
  validatePostalCode,
  validatePostalCodeInCity,
  validateStreetInCity,
} from './locationService';

const place = (address, display_name = 'somewhere') => ({
  address,
  display_name,
});

describe('locationService', () => {
  beforeEach(() => {
    get.mockReset();
    fallbackGet.mockReset();
  });

  it('confirms a city only in the country that was chosen', async () => {
    get.mockResolvedValue({
      data: [place({ town: 'Paris', country_code: 'us' })],
    });
    expect((await validateCity('Paris', 'FR')).data.isValid).toBe(false);

    get.mockResolvedValue({
      data: [place({ city: 'Paris', country_code: 'fr' })],
    });
    expect((await validateCity('paris', 'FR')).data.isValid).toBe(true);
    expect(get.mock.calls[0][1].params).toMatchObject({
      countrycodes: 'fr',
      format: 'json',
    });
  });

  it('reports a failed search as unanswered rather than invalid', async () => {
    get.mockRejectedValue(new Error('offline'));
    expect(await validateCity('Paris', 'FR')).toEqual({ success: false });
  });

  it('checks a postal code against its country format', async () => {
    expect((await validatePostalCode('75001', 'FR')).data.isValid).toBe(true);
    expect((await validatePostalCode('7500', 'FR')).data.isValid).toBe(false);
    expect((await validatePostalCode('ABC', 'ZZ')).data.isValid).toBe(true);
  });

  it('names the cities a postal code belongs to when it is not the chosen one', async () => {
    get.mockResolvedValue({
      data: [
        place({ city: 'Villeurbanne' }),
        place({ city: 'Villeurbanne' }),
        place({ town: 'Bron' }),
      ],
    });
    const result = await validatePostalCodeInCity('69100', 'Lyon', 'FR');
    expect(result.data).toEqual({
      isValid: false,
      messageKey: 'register.location.postal_code_belongs_to',
      messageParams: { cities: 'Villeurbanne, Bron' },
      suggestions: ['Villeurbanne', 'Bron'],
    });
  });

  it('confirms a street found in the chosen city', async () => {
    get.mockResolvedValue({
      data: [place({ village: 'Lyon' }, 'Rue Garibaldi, Lyon')],
    });
    const result = await validateStreetInCity('Rue Garibaldi', 'Lyon', 'FR');
    expect(result.data).toMatchObject({
      isValid: true,
      messageKey: 'register.location.street_in_city',
      suggestions: ['Rue Garibaldi, Lyon'],
    });
  });

  it('says a street was not found at all when the search is empty', async () => {
    get.mockResolvedValue({ data: [] });
    const result = await validateStreetInCity('Nowhere', 'Lyon', 'FR');
    expect(result.data.messageKey).toBe('register.location.street_not_found');
  });

  it('falls back to the installation for countries when the public list fails', async () => {
    get.mockRejectedValue(new Error('blocked'));
    fallbackGet.mockResolvedValue({ data: [{ country_id: 'FR' }] });
    expect(await getCountries()).toEqual({
      success: true,
      data: [{ country_id: 'FR' }],
    });
  });

  it('reads the locality whatever OpenStreetMap calls it', () => {
    expect(localityOf(place({ municipality: 'Ixelles' }))).toBe('Ixelles');
    expect(localityOf({})).toBeNull();
  });
});
