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

## Logging

The CLI logs actions and API responses to stdout using a timestamped format to make troubleshooting easier.
