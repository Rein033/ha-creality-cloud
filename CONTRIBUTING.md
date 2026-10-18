# Contributing

Thanks for helping out. Bug reports and pull requests are welcome.

## Reporting a bug

Open an issue with the bug template. Please add **diagnostics**: Settings → Devices & services → Creality Cloud →
three dots → *Download diagnostics*. They contain what Creality Cloud returned, with your e-mail, password, token,
serial numbers and network details removed. Check the file before you attach it anyway.

## Supporting another printer

The integration reads whatever Creality Cloud returns in `getDeviceList`. If your printer shows wrong or missing values,
attach diagnostics and say which values the Creality app shows at the same time.

## Development

```bash
uv venv --python 3.14 .venv
VIRTUAL_ENV=.venv uv pip install pytest-homeassistant-custom-component
.venv/bin/python -m pytest
```

- `custom_components/creality_cloud/api.py` talks to Creality Cloud. `parse_device()` has no network and is tested with
  `tests/device.json`, an anonymised real K1 Max.
- Never commit real tokens, e-mail addresses, serial numbers or MAC addresses, also not in test data.
- Commands to the printer are an allow-list (`COMMANDS`). Please do not add G-code or file upload.
- The card is a single file without build step: `custom_components/creality_cloud/www/creality-print-card.js`.
  Bump `version` in `manifest.json` when you change it, so browsers load the new file.
