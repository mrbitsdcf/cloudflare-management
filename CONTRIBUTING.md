# Contributing

Thanks for your interest in contributing! This project is a small CLI for managing Cloudflare DNS via their API. Here’s how to get started.

## Code of Conduct
Please read and follow the [Code of Conduct](CODE_OF_CONDUCT.md). We expect all contributors to uphold these standards.

## Development Setup
1) Clone the repo and enter the directory.  
2) (Optional) Create and activate a virtualenv:  
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   ```  
3) Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```

## Running Lint
We use `pylint` for linting. Install it (if not already available) and run:
```bash
PYLINTHOME=.pylint.d pylint cfmanager.py
```

## Making Changes
- Keep changes focused; separate unrelated fixes into different pull requests.
- Add or update documentation when behavior changes.
- Avoid introducing new dependencies unless necessary; if you do, explain why.

## Pull Requests
1) Fork the repo and create a feature branch.  
2) Ensure lint passes and commands work as expected.  
3) Submit a PR using the template in `.github/pull_request_template.md`.  
4) Be responsive to review feedback; small, incremental updates are preferred.

Thank you for contributing!
