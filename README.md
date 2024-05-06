# BPDM Upload Tool

This tool implements upload (and download) of BPDM data in CSV format using the BPDM REST API.

See [CSV File Format](documentation/CSV%20File%20Format.md)

## Installation
```bash
# Install pipenv, if not already present in local Python setup
pip install pipenv

# change into main directory
cd bpdm-upload-tool

# optionally: create local .venv directory if you want the environment
# to be stored below the source tree and not in your home directory.
mkdir .venv

# install dependencies (will automatically detect the .venv directory)
pipenv install
```

## Credentials
You have to create a file called `credentials.json` in the root of the project
containing the credentials for authentication.

Content:
```json
{
    "client_id": "...",
    "client_secret": "..."
}
```

## Running
```bash
.venv\scripts\activate
cd server
flask run
```
