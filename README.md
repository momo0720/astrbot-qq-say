# astrbot-qq-say

Generate fake QQ forwarded chat records from mentions and text.

## Features

- Supports multi-speaker forwarded chat generation.
- Supports configurable separators, group whitelist, private chat switch, and protected target users.

## Installation

1. Clone or download this repository.
2. Copy the `qq_say` directory into your AstrBot plugin directory.
3. Open the AstrBot plugin configuration page and fill in the required settings.
4. Restart AstrBot or reload the plugin.

## Usage

- Main command: `/qq说`
- Detailed command examples: see `qq_say/README.md`

## Repository Structure

- `qq_say/main.py`
- `qq_say/_conf_schema.json`
- `qq_say/metadata.yaml`
- `qq_say/README.md`

## Notes

- Sensitive local API endpoints and keys have been replaced with placeholders where applicable.
- Runtime-specific local config files are not included.
