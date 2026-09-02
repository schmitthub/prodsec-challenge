# `config/`

## Directory summary

Development-only vendor configuration lives here. The directory contains the standalone Python module `dev.py` and has no child directories. Project runtime code does not currently import these values.

## Module role

`config.dev` provides fixed sample values for development and security-scanner fixtures; it is not part of the FastAPI request path.

## Code files and symbols

- `dev.py` — declares sample vendor configuration constants.
  - `LAB_VENDOR_API_KEY` — fixed example vendor API credential.
  - `DEBUG_VENDOR_URL` — example vendor endpoint associated with the development configuration.
