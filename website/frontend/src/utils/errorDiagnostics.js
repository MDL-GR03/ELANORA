const SAFE_ERROR_CODE = /^[A-Z0-9_-]{1,64}$/;

/**
 * Return operational metadata that is useful for debugging without retaining
 * response bodies, request payloads, headers, URLs, or personal information.
 */
export function getSafeErrorMetadata(error) {
  const metadata = {};
  const status = error?.response?.status;
  const code = error?.code;

  if (Number.isInteger(status) && status >= 100 && status <= 599) {
    metadata.status = status;
  }
  if (typeof code === 'string' && SAFE_ERROR_CODE.test(code)) {
    metadata.code = code;
  }

  return metadata;
}

export function reportClientError(message, error) {
  console.error(message, getSafeErrorMetadata(error));
}
