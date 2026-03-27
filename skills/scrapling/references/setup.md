# Scrapling setup

## Expected environment

Preferred install path:

- virtualenv: `/root/.openclaw/workspace/.venvs/scrapling`

Install sequence:

```bash
apt install python3-pip python3.13-venv
python3 -m venv /root/.openclaw/workspace/.venvs/scrapling
/root/.openclaw/workspace/.venvs/scrapling/bin/pip install -U pip setuptools wheel
/root/.openclaw/workspace/.venvs/scrapling/bin/pip install 'scrapling[fetchers,shell]'
```

Optional browser support:

```bash
/root/.openclaw/workspace/.venvs/scrapling/bin/python -m playwright install chromium
```

## Notes

- This host currently lacked `pip` / `python3-venv` during first install attempt.
- If browser-based fetching is needed, Playwright browser binaries must also be installed.
- Start simple: many tasks only need `Fetcher`.
