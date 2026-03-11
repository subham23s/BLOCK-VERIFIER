# BlockVerify — Blockchain-Based File Integrity Verification

## 📌 Overview

BlockVerify uses **SHA-256 hashing**, **Proof-of-Work mining**, and **IPFS (via Pinata)** to verify the integrity of any file — images, documents, or ML models. Any modification to a registered file is instantly detected.

---

## 🆕 What's New (v2)

| Feature | v1 | v2 |
|---|---|---|
| File support | Only iris_model.joblib | Any image, document, ML model |
| Blockchain storage | Local JSON | Pinata IPFS (decentralized) |
| Mining | ❌ | ✅ Proof-of-Work |
| Interface | Script only | Flask Web UI + CLI |
| Multi-file | ❌ | ✅ Each file = its own block |

---

## 🏗 Architecture

```
File Upload
    ↓
SHA-256 Hash
    ↓
Proof-of-Work Mining (find nonce where hash starts with 0000)
    ↓
New Block added to chain
    ↓
Blockchain JSON pinned to IPFS via Pinata
    ↓
CID saved locally for future fetches
```

---

## 🚀 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Pinata API Keys
1. Go to [pinata.cloud](https://pinata.cloud) → Sign up (free)
2. API Keys → Create new key → enable `pinFiles` and `pinJSON`
3. Copy **API Key** and **Secret Key**

### 3. Set environment variables
```bash
# Linux/Mac
export PINATA_API_KEY="your_api_key_here"
export PINATA_SECRET_KEY="your_secret_key_here"

# Windows
set PINATA_API_KEY=your_api_key_here
set PINATA_SECRET_KEY=your_secret_key_here
```

---

## 🌐 Web UI

```bash
python app.py
```
Open: http://localhost:5000

### Features:
- **Register tab** — Upload any file, mines a block and stores on IPFS
- **Verify tab** — Upload a file to check if it matches the blockchain
- **Chain Explorer** — Browse all blocks with nonce, hash, timestamps
- **Config tab** — Enter Pinata keys directly in the UI

---

## 💻 CLI

```bash
# Register a file
python cli.py register iris_model.joblib
python cli.py register photo.jpg
python cli.py register report.pdf

# Verify a file
python cli.py verify photo.jpg

# View entire chain
python cli.py chain

# Check Pinata connection
python cli.py status
```

---

## 🔐 Proof-of-Work

Each block is mined by finding a `nonce` such that:

```
SHA-256(index + timestamp + file_hash + previous_hash + nonce)
```

starts with `0000` (difficulty = 4 zeros by default).

This makes it computationally expensive to tamper with the chain.

---

## 📂 Project Structure

```
blockchain_iris_project/
│
├── app.py              # Flask web application
├── cli.py              # Command-line interface
├── blockchain.py       # Block + Blockchain + PoW
├── hash_utils.py       # SHA-256 for files/bytes
├── pinata_utils.py     # Pinata IPFS integration
├── train_model.py      # Train iris ML model
├── requirements.txt
└── README.md
```

---

## ⚠ Limitations

- Not a distributed blockchain (single node)
- No consensus mechanism
- Pinata free tier has storage limits
- Educational/demo use only

---

## 📈 Future Improvements

- Digital signatures per file
- Email alerts on tamper detection
- Multi-user access with auth
- IPFS file storage (not just JSON)

---

## 👨‍💻 Author

**SUBHAM MISHRA**  
Regd No: 240301370048  
B.Tech CSE (AI/ML Specialization)  
Blockchain Intro Course Project — v2
