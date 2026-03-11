import requests
import json
import os

PINATA_API_KEY = os.environ.get("55f0456e0a86ad1b5bae", "")
PINATA_SECRET_KEY = os.environ.get("8c4e07a913945513d066b5936faa15f24ce3dff6924cad9d195e27bc47d00db4p", "")

PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_GATEWAY = "https://gateway.pinata.cloud/ipfs/"

# Local cache file to remember the latest CID
CID_CACHE_FILE = "latest_cid.txt"


def _headers():
    return {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY,
        "Content-Type": "application/json"
    }


def save_blockchain_to_pinata(chain_data: list, name: str = "blockchain_data") -> str:
    """Pin blockchain JSON to IPFS via Pinata. Returns CID."""
    if not PINATA_API_KEY or not PINATA_SECRET_KEY:
        raise ValueError("Pinata API keys not set. Set PINATA_API_KEY and PINATA_SECRET_KEY env variables.")

    payload = {
        "pinataMetadata": {"name": name},
        "pinataContent": {"blockchain": chain_data}
    }

    response = requests.post(PINATA_PIN_JSON_URL, headers=_headers(), data=json.dumps(payload))

    if response.status_code != 200:
        raise Exception(f"Pinata upload failed: {response.text}")

    cid = response.json()["IpfsHash"]

    # Save CID locally so we can fetch latest
    with open(CID_CACHE_FILE, "w") as f:
        f.write(cid)

    return cid


def load_blockchain_from_pinata(cid: str = None) -> list:
    """Fetch blockchain JSON from IPFS via Pinata gateway."""
    if cid is None:
        if not os.path.exists(CID_CACHE_FILE):
            return None
        with open(CID_CACHE_FILE, "r") as f:
            cid = f.read().strip()

    if not cid:
        return None

    url = f"{PINATA_GATEWAY}{cid}"
    response = requests.get(url, timeout=15)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch from IPFS: {response.text}")

    data = response.json()
    return data.get("blockchain", None)


def get_latest_cid() -> str:
    if os.path.exists(CID_CACHE_FILE):
        with open(CID_CACHE_FILE, "r") as f:
            return f.read().strip()
    return None


def test_pinata_connection() -> bool:
    """Test if Pinata API keys are valid."""
    try:
        response = requests.get(
            "https://api.pinata.cloud/data/testAuthentication",
            headers={
                "pinata_api_key": PINATA_API_KEY,
                "pinata_secret_api_key": PINATA_SECRET_KEY
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False
