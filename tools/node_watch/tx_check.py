# File: tx_check.py
"""
tx_check.py

Manages TX FSM with four phases per container:
0) Idle, waiting for precommit assignment
1) Precommit TX detected → poll until success/fail
2) Waiting for commit assignment
3) Commit TX detected → poll until success/fail
Upon success at phase 3, transition to idle until new session.
Failures accumulate (shared counter) and can trigger restarts.
"""
import re
import requests
from datetime import timedelta

# Regexes for parsing log lines
LOG_STATE_RE = re.compile(r"Latest ID:\s*(\d+)\s*/\s*Latest State:\s*(\d+)")
ASSIGNED_RE  = re.compile(r"Assigned Miners:\s*(.*)")
TX_RE        = re.compile(r"TX:\s*(0x[0-9a-fA-F]+)")


def rpc_get_receipt(rpc_url, tx_hash, timeout=10):
    payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionReceipt", "params": [tx_hash]}
    try:
        r = requests.post(rpc_url, json=payload, headers={"Content-Type": "application/json"}, timeout=timeout)
        r.raise_for_status()
        return r.json().get("result", None)
    except Exception:
        return None


def find_latest_assigned_stage(log_lines, miner_addr, stage_code, lookahead=20):
    """
    Find the index in log_lines where Latest State == stage_code and miner_addr is in Assigned Miners thereafter.
    """
    idx_found = None
    for idx, ln in enumerate(log_lines):
        m = LOG_STATE_RE.search(ln)
        if m and int(m.group(2)) == stage_code:
            for j in range(idx+1, min(idx+1+lookahead, len(log_lines))):
                ma = ASSIGNED_RE.search(log_lines[j])
                if ma:
                    assigned = [a.strip().lower() for a in ma.group(1).split(',')]
                    if miner_addr.lower() in assigned:
                        idx_found = idx
                        break
    return idx_found


def find_first_tx_after(log_lines, start_idx):
    """
    Return first TX hash found after start_idx in log_lines, or None.
    """
    for ln in log_lines[start_idx:]:
        m = TX_RE.search(ln)
        if m:
            return m.group(1)
    return None


class TxChecker:
    def __init__(self, rpc_url, timeout_seconds=30):
        self.rpc_url = rpc_url
        self.timeout = timedelta(seconds=timeout_seconds)
        # per-container state: {cid: 0..3}
        self.tx_state = {}
        # per-container deadline for polling receipts
        self.tx_deadline = {}
        # per-container pending entry for polling phase: dict with 'tx', 'next', 'type'
        self.pending = {}
        # miner addresses
        self.miner_addr = {}

    def init_container(self, container_name, miner_addr):
        self.tx_state[container_name] = 0
        self.tx_deadline[container_name] = None
        self.pending[container_name] = {}
        self.miner_addr[container_name] = miner_addr.lower()

    def on_new_session(self, container_name):
        # Reset FSM on new session
        self.tx_state[container_name] = 0
        self.tx_deadline[container_name] = None
        self.pending[container_name].clear()

    def process_logs(self, container_name, log_lines, now, check_receipt):
        state = self.tx_state[container_name]
        addr = self.miner_addr[container_name]

        # Phase 0: detect precommit assignment & TX
        if state == 0:
            idx3 = find_latest_assigned_stage(log_lines, addr, 3)
            if idx3 is not None:
                tx1 = find_first_tx_after(log_lines, idx3)
                if tx1:
                    # move to precommit polling phase
                    self.tx_state[container_name] = 1
                    self.tx_deadline[container_name] = now + self.timeout
                    self.pending[container_name] = {
                        'tx': tx1,
                        'next': now + timedelta(seconds=5),
                        'type': 'pre'
                    }
                    return ('detect_pre', tx1)
            return None

        # Phase 1: poll for precommit receipt
        if state == 1:
            entry = self.pending.get(container_name)
            if entry and now >= entry['next']:
                tx_hash = entry['tx']
                receipt = check_receipt(tx_hash)
                if receipt and receipt.get('status') == '0x1':
                    # Precommit succeeded → advance to commit detection
                    self.tx_state[container_name] = 2
                    self.tx_deadline[container_name] = None
                    self.pending[container_name].clear()
                    return ('success_pre', tx_hash)
                # on failure or timeout
                if now > self.tx_deadline[container_name]:
                    # final precommit failure
                    self.pending[container_name].clear()
                    return ('fail', 'pre_timeout')
                # schedule next check
                entry['next'] = now + timedelta(seconds=5)
            return None

        # Phase 2: detect commit assignment & TX
        if state == 2:
            idx4 = find_latest_assigned_stage(log_lines, addr, 4)
            if idx4 is not None:
                tx2 = find_first_tx_after(log_lines, idx4)
                if tx2:
                    # move to commit polling phase
                    self.tx_state[container_name] = 3
                    self.tx_deadline[container_name] = now + self.timeout
                    self.pending[container_name] = {
                        'tx': tx2,
                        'next': now + timedelta(seconds=5),
                        'type': 'commit'
                    }
                    return ('detect_commit', tx2)
            return None

        # Phase 3: poll for commit receipt
        if state == 3:
            entry = self.pending.get(container_name)
            if entry and now >= entry['next']:
                tx_hash = entry['tx']
                receipt = check_receipt(tx_hash)
                if receipt and receipt.get('status') == '0x1':
                    # Commit succeeded → idle
                    self.tx_state[container_name] = 4
                    self.tx_deadline[container_name] = None
                    self.pending[container_name].clear()
                    return ('success_commit', tx_hash)
                # on failure or timeout
                if now > self.tx_deadline[container_name]:
                    self.pending[container_name].clear()
                    return ('fail', 'commit_timeout')
                entry['next'] = now + timedelta(seconds=5)
            return None

        return None
