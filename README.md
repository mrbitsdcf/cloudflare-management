# Cloudflare DNS CLI

Command-line tools to manage DNS zones and records on Cloudflare using the official REST API. Built with Python and Click, with logging, validation, and friendly error handling.

##

- Python 3.8+ installed.
- A Cloudflare API token with the required permissions:
    - `Zone:Read` for listing zones.
    - `DNS:Edit` for creating DNS records.

## Installation

```bash
# Optionally create/activate a virtualenv
# python3 -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

## Development & Tests

```bash
# Install dev dependencies (pytest, coverage helpers)
pip install -r requirements-dev.txt

# Run the test suite
python -m pytest

# With coverage report
python -m pytest --cov=cfmanager --cov-report=term-missing
```

## Configuration

- Provide your token via `--api-token` **or** set the environment variable (safer option):

  ```bash
  export CLOUDFLARE_API_TOKEN=your_token_here
  ```

## Usage

From the project root:

### List DNS zones

```bash
python cfmanager.py list-dns-zones \
  [--api-token YOUR_TOKEN] \
  [--page-size 50] \
  [--zone-name exact-zone.example.com]
```

- Shows each zone name and its ID.  

- Use `--zone-name` to filter by an exact zone name.

### Create a DNS record

```bash
python cfmanager.py create-dns-record \
  --zone-name example.com \
  --hostname host.example.com \
  --type A \
  --value 192.168.1.10 \
  [--api-token YOUR_TOKEN]
```

- Accepts record types: A, AAAA, CNAME, TXT, MX, NS, SRV, PTR, CAA.  
- `--zone-name` is resolved to the correct `zone_id` automatically.

### List DNS records of a zone

```bash
python cfmanager.py list-dns-records \
  --zone-name example.com \
  [--api-token YOUR_TOKEN] \
  [--page-size 100]
```

- Prints a table with `HOSTNAME`, `TYPE`, and `DESTINATION`.  
- Prints destinations as the record content (e.g., IP, CNAME target); MX records include priority before the target.

### Remove a DNS record

```bash
python cfmanager.py remove-dns-record \
  --zone-name example.com \
  --record-name host.example.com \
  [--api-token YOUR_TOKEN]
```

- Locates the record by exact name, prompts for confirmation, then deletes it.

### Export a DNS zone (BIND format)

```bash
python cfmanager.py export-dns-zone \
  --zone-name example.com \
  [--api-token YOUR_TOKEN] \
  [--output ./example.com.zone]
```

- Uses Cloudflare's export endpoint to fetch the zone in BIND9 format.  
- Writes to `<zone-name>.zone` by default or the path provided via `--output`.

## Logging

The CLI logs actions and API responses to stdout using a timestamped format.  
All commands accept `--log-file path/to/cfmanager.log` (before or after the subcommand) to also write rotating logs (1 MB, 3 backups).  
Example:

```bash
python cfmanager.py list-dns-zones --log-file cfmanager.log
```
