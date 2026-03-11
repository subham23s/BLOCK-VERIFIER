#!/usr/bin/env python3
"""
BlockVerify CLI — Blockchain-based File Integrity Verification
Usage: python cli.py [command] [options]
"""

import argparse
import sys
import os
import time
from blockchain import Blockchain
from hash_utils import generate_file_hash, detect_file_type
from pinata_utils import (
    save_blockchain_to_pinata,
    load_blockchain_from_pinata,
    test_pinata_connection,
    get_latest_cid
)

# ── ANSI Colors ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"
PURPLE = "\033[95m"

def cprint(color, *args): print(color + " ".join(str(a) for a in args) + RESET)
def ok(*args):   cprint(GREEN,  "✅", *args)
def err(*args):  cprint(RED,    "❌", *args)
def warn(*args): cprint(YELLOW, "⚠ ", *args)
def info(*args): cprint(CYAN,   "ℹ ", *args)
def head(*args): cprint(BOLD + PURPLE, *args)

def separator(): print(DIM + "─" * 60 + RESET)

def spinner_start(msg):
    sys.stdout.write(f"\r{CYAN}⛏  {msg}...{RESET}")
    sys.stdout.flush()

def spinner_stop(): print()


# ── Blockchain helpers ─────────────────────────────────────────────────────
def get_blockchain() -> Blockchain:
    try:
        data = load_blockchain_from_pinata()
        if data:
            return Blockchain.from_list(data)
    except Exception as e:
        warn(f"Could not load from Pinata: {e}")
    return Blockchain(difficulty=4)


def save(bc: Blockchain):
    spinner_start("Uploading blockchain to Pinata IPFS")
    cid = save_blockchain_to_pinata(bc.to_list())
    spinner_stop()
    return cid


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_register(args):
    head("\n  REGISTER FILE")
    separator()

    if not os.path.exists(args.file):
        err(f"File not found: {args.file}")
        sys.exit(1)

    file_hash = generate_file_hash(args.file)
    file_type = detect_file_type(args.file)
    file_name = os.path.basename(args.file)

    info(f"File     : {file_name}")
    info(f"Type     : {file_type}")
    info(f"SHA-256  : {file_hash}")
    separator()

    bc = get_blockchain()
    existing = bc.find_block_by_hash(file_hash)

    if existing:
        warn("This file is already registered!")
        info(f"Block #  : {existing.index}")
        info(f"File     : {existing.file_name}")
        return

    spinner_start(f"Mining block (PoW difficulty={bc.difficulty})")
    start = time.time()
    block = bc.add_block(file_name, file_hash, file_type)
    elapsed = time.time() - start
    spinner_stop()

    ok(f"Block mined in {elapsed:.2f}s  |  nonce={block.nonce}")
    info(f"Block #  : {block.index}")
    info(f"Hash     : {block.current_hash[:32]}...")

    cid = save(bc)
    ok(f"Stored on IPFS: {cid}")
    separator()


def cmd_verify(args):
    head("\n  VERIFY FILE")
    separator()

    if not os.path.exists(args.file):
        err(f"File not found: {args.file}")
        sys.exit(1)

    file_hash = generate_file_hash(args.file)
    file_type = detect_file_type(args.file)
    file_name = os.path.basename(args.file)

    info(f"File     : {file_name}")
    info(f"Type     : {file_type}")
    info(f"SHA-256  : {file_hash}")
    separator()

    spinner_start("Fetching blockchain from Pinata")
    bc = get_blockchain()
    spinner_stop()

    block = bc.find_block_by_hash(file_hash)
    chain_valid = bc.is_chain_valid()

    if block:
        ok("FILE INTEGRITY VERIFIED")
        info(f"Registered as : {block.file_name}")
        info(f"Block #        : {block.index}")
        info(f"Chain valid    : {'✅ Yes' if chain_valid else '❌ Compromised!'}")
    else:
        err("FILE NOT REGISTERED or TAMPERED")
        warn("Hash does not match any block in the chain.")
        info("If this is a new file, register it first using: python cli.py register <file>")
    separator()


def cmd_chain(args):
    head("\n  CHAIN EXPLORER")
    separator()

    spinner_start("Fetching blockchain from Pinata")
    bc = get_blockchain()
    spinner_stop()

    chain_valid = bc.is_chain_valid()
    cid = get_latest_cid()

    info(f"Total blocks : {len(bc.chain)}")
    info(f"Chain valid  : {'✅ Yes' if chain_valid else '❌ COMPROMISED'}")
    info(f"IPFS CID     : {cid or 'Not synced'}")
    separator()

    for block in bc.chain:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(block.timestamp))
        prefix = f"  [{block.index}]"
        cprint(CYAN, f"{prefix} {block.file_name}")
        print(f"       Type      : {block.file_type}")
        print(f"       Timestamp : {ts}")
        print(f"       Nonce     : {block.nonce}")
        print(f"       Hash      : {block.current_hash[:40]}...")
        if block.index < len(bc.chain) - 1:
            print(f"       {DIM}↓{RESET}")
    separator()


def cmd_status(args):
    head("\n  SYSTEM STATUS")
    separator()
    connected = test_pinata_connection()
    if connected:
        ok("Pinata IPFS : Connected")
    else:
        err("Pinata IPFS : Not connected — set PINATA_API_KEY and PINATA_SECRET_KEY")
    cid = get_latest_cid()
    info(f"Latest CID  : {cid or 'None'}")
    separator()


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="blockverify",
        description=f"{BOLD}BlockVerify — SHA-256 + PoW Blockchain File Integrity{RESET}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py register iris_model.joblib
  python cli.py register photo.jpg
  python cli.py verify photo.jpg
  python cli.py chain
  python cli.py status
        """
    )
    sub = parser.add_subparsers(dest="command")

    # register
    p_reg = sub.add_parser("register", help="Register a file in the blockchain")
    p_reg.add_argument("file", help="Path to file to register")

    # verify
    p_ver = sub.add_parser("verify", help="Verify if a file matches the blockchain")
    p_ver.add_argument("file", help="Path to file to verify")

    # chain
    sub.add_parser("chain", help="View all blocks in the chain")

    # status
    sub.add_parser("status", help="Check Pinata connection and chain status")

    args = parser.parse_args()

    if args.command == "register": cmd_register(args)
    elif args.command == "verify":   cmd_verify(args)
    elif args.command == "chain":    cmd_chain(args)
    elif args.command == "status":   cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
