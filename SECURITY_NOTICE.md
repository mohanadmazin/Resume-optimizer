# Security notice

The uploaded source archive contained plaintext provider API keys in
`opencode.json`. That local file is excluded from this corrected package and is
already covered by `.gitignore`.

Before using or publishing this project:

1. Revoke and rotate every provider credential that was stored in the old file.
2. Check the GitHub repository history for committed copies of `opencode.json`.
3. Store new credentials in environment variables or a local ignored file.
4. Copy `opencode.example.json` to `opencode.json` only on your own machine and
   replace placeholders locally.

Do not commit real API keys to Git.
