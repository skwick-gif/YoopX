Place your API keys in this file or set them as environment variables.

Preferred secure workflow:
1) Set environment variables in your PowerShell session (temporary):

   $env:POLYGON_API_KEY = 'your_polygon_key'
   $env:ALPHAVANTAGE_API_KEY = 'your_av_key'

2) Or paste your keys into `config/keys.json` (this file is intended to be local-only; do NOT commit real keys).

File format (JSON):

{
  "polygon": "your_polygon_key",
  "alphavantage": "your_av_key",
  "marketstack": "your_marketstack_key",
  "twelvedata": "your_twelvedata_key"
}

After adding keys, run the tests that need them from the repository root. The test scripts prefer environment
variables, and fall back to this JSON file when env vars are not present.
