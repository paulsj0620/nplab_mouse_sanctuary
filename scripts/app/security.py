"""Bounded, process-local authentication throttling; no credentials are retained."""
import hashlib
import ipaddress
import threading
import time


class LoginLimiter:
    def __init__(self, window=300, account_limit=15, ip_limit=30, capacity=4096):
        self.window, self.account_limit, self.ip_limit, self.capacity = window, account_limit, ip_limit, capacity
        self.entries = {}
        self.blocked = {}
        self.lock = threading.Lock()

    def begin(self, address, username):
        # Hash identifiers so arbitrary user input is not retained in the limiter.
        name = username[:80] if isinstance(username, str) else '(invalid username)'
        account = hashlib.sha256(name.encode()).hexdigest()
        keys = (('ip', address), ('account', account))
        now = time.monotonic()
        with self.lock:
            for key in list(self.entries):
                self.entries[key] = [t for t in self.entries[key] if now-t < self.window]
                if not self.entries[key]: del self.entries[key]
            self.blocked = {k:v for k,v in self.blocked.items() if now-v < self.window}
            full = len(self.entries) + sum(k not in self.entries for k in keys) > self.capacity
            limited = full or any(len(self.entries.get(k, [])) >= limit for k,limit in zip(keys,(self.ip_limit,self.account_limit)))
            if limited:
                # Record one blocked event per account/window, not one per request.
                log = keys[1] not in self.blocked and len(self.blocked) < self.capacity
                if log: self.blocked[keys[1]] = now
                return None, log
            ticket = (keys, now)
            for key in keys: self.entries.setdefault(key, []).append(now)
            return ticket, False

    def finish(self, ticket, success):
        if not success: return
        keys, timestamp = ticket
        with self.lock:
            for key in keys:
                values = self.entries.get(key, [])
                if timestamp in values: values.remove(timestamp)
                if not values: self.entries.pop(key, None)


def client_ip(peer, headers, hosted):
    # Only --alwaysdata trusts its front proxy, which replaces client IP headers.
    # Direct/LAN deployments must never trust client-supplied forwarding headers.
    if hosted:
        try: return str(ipaddress.ip_address(headers.get('X-Real-IP', '')))
        except ValueError: pass
    return peer
