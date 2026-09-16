"""Settings shared by every test run."""

import os

# Tests never call Have I Been Pwned; the breach check has tests of its own
# that replace the HTTP transport.
os.environ.setdefault("PASSWORD_BREACH_CHECK", "false")
