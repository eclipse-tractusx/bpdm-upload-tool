# BPDM Upload Tool

This tool implements upload (and download) of BPDM data in CSV format using the BPDM REST API.

See [CSV File Format](documentation/CSV%20File%20Format.md)

## Installation
```bash
# Install pipenv, if it is not already present in your local Python setup.
# Use one of the commands below, suitable for your OS.
pip install pipenv
pip3 install pipenv
brew install pipenv
apt install pipenv

# Change into the main directory
cd bpdm-upload-tool

# Optionally: create a local .venv directory if you want the environment
# to be stored below the source tree and not in your home directory.
mkdir .venv

# Install dependencies (will automatically detect the .venv directory)
pipenv install

# create uploads folder
mkdir uploads
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
