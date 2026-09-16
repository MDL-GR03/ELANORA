# Password policy

ELANORA follows [NIST SP 800-63B revision 4](https://pages.nist.gov/800-63-4/sp800-63b.html)
for passwords that are the only authentication factor. The same rules apply
wherever a password is set: registration, password reset, password change, the
setup page, and the `elanora-bootstrap` and `elanora-reset-password` tools.
Existing passwords keep working; the rules apply when a password is set.

## The rules

| Rule | Why |
| --- | --- |
| At least 15 characters | Length is what makes a password hard to guess. |
| At most 72 bytes | bcrypt ignores everything after 72 bytes, so longer passwords would only appear to be accepted. |
| No rules about capitals, digits or symbols | They push people towards predictable substitutions and make passwords harder to remember. |
| Not a repeated or sequential pattern | `abcabcabc…` or `abcdefghijklmno` meet the length rule while being trivial to guess. |
| Not built mostly from the account's username, email address or names, or from "elanora" | Anyone who knows whose account it is would try those first. |
| Not found in a known data breach | Attackers try breached passwords before anything else. |

The browser shows the rules it can check while the password is typed. The API
enforces all of them, and each refusal carries a stable code
(`password_too_short`, `password_breached`, …) that the interface explains in
the researcher's language.

## Breached passwords

Two checks apply, one after the other.

**Have I Been Pwned.** The API asks the
[Pwned Passwords range API](https://haveibeenpwned.com/API/v3#PwnedPasswords),
which covers several hundred million passwords from real breaches and is updated
as new breaches are found. It uses k-anonymity: the installation sends only the
first five hexadecimal characters of the password's SHA-1 hash, receives every
breached hash starting with them, and compares the rest locally. Neither the
password nor its full hash leaves the installation, and responses are padded so
their size reveals nothing either.

If the service cannot be reached, the password is not refused because of it —
researchers are never locked out by an outage — and the failure is logged. An
installation without internet access sets `PASSWORD_BREACH_CHECK=false`.

**The shipped list.** `app/core/common_passwords.txt` holds the entries of 15
characters or more from the UK National Cyber Security Centre's list of the
100,000 passwords most often found in breaches (from SecLists, MIT licence).
It works offline and is a floor, not a substitute for the check above: shorter
entries on that list are already refused by the length rule.

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `PASSWORD_BREACH_CHECK` | `true` | Ask Have I Been Pwned about new passwords. |
| `BREACH_CHECK_API_URL` | `https://api.pwnedpasswords.com/range/` | Range endpoint, for a mirror inside the institution. |
| `BREACH_CHECK_TIMEOUT_SECONDS` | `3` | How long to wait before treating the service as unavailable. |
