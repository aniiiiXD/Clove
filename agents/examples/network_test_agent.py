#!/usr/bin/env python3
"""
Network Test Agent - Tests Network Isolation

This agent attempts to make network connections to demonstrate that
sandboxed agents without network access are properly isolated.

== Expected Behavior ==

Without network isolation:  Successfully connects to external services
With network isolation:     All network connections fail (ENETUNREACH)

== What This Demonstrates ==

AgentOS can protect against:
- Data exfiltration via network
- Command & control callbacks
- Unauthorized API access
- DNS-based attacks

When an agent is spawned with network=False, it runs in an isolated
network namespace with no network interfaces (except loopback).
"""

import os
import sys
import socket
import time
import urllib.request
import urllib.error

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient

def test_tcp_connection(host, port, timeout=3):
    """Try to establish a TCP connection"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True, "Connected successfully"
    except socket.timeout:
        return False, "Connection timeout"
    except OSError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def test_dns_resolution(hostname):
    """Try to resolve a hostname"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"Resolved to {ip}"
    except socket.gaierror as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def test_http_request(url, timeout=3):
    """Try to make an HTTP request"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AgentOS-Test'})
        response = urllib.request.urlopen(req, timeout=timeout)
        status = response.getcode()
        response.close()
        return True, f"HTTP {status}"
    except urllib.error.URLError as e:
        return False, str(e.reason)
    except Exception as e:
        return False, str(e)

def run_network_tests():
    """Run all network isolation tests"""
    results = []

    print("[NET-TEST] Testing network isolation...")
    print()

    # Test 1: DNS Resolution
    print("[NET-TEST] Test 1: DNS Resolution (google.com)")
    success, msg = test_dns_resolution("google.com")
    status = "ALLOWED" if success else "BLOCKED"
    print(f"           Result: {status} - {msg}")
    results.append(("DNS Resolution", success, msg))

    # Test 2: TCP Connection to well-known port
    print("[NET-TEST] Test 2: TCP Connection (8.8.8.8:53)")
    success, msg = test_tcp_connection("8.8.8.8", 53)
    status = "ALLOWED" if success else "BLOCKED"
    print(f"           Result: {status} - {msg}")
    results.append(("TCP Connection", success, msg))

    # Test 3: HTTP Request
    print("[NET-TEST] Test 3: HTTP Request (http://httpbin.org/ip)")
    success, msg = test_http_request("http://httpbin.org/ip")
    status = "ALLOWED" if success else "BLOCKED"
    print(f"           Result: {status} - {msg}")
    results.append(("HTTP Request", success, msg))

    # Test 4: HTTPS Request
    print("[NET-TEST] Test 4: HTTPS Request (https://api.github.com)")
    success, msg = test_http_request("https://api.github.com")
    status = "ALLOWED" if success else "BLOCKED"
    print(f"           Result: {status} - {msg}")
    results.append(("HTTPS Request", success, msg))

    print()

    # Summarize
    allowed = sum(1 for _, success, _ in results if success)
    blocked = len(results) - allowed

    return results, allowed, blocked

def main():
    print("=" * 60)
    print("  Network Test Agent")
    print("  Testing network namespace isolation")
    print("=" * 60)
    print()
    print(f"[NET-TEST] PID: {os.getpid()}")

    # Connect to kernel
    client = AgentOSClient()
    if client.connect():
        print("[NET-TEST] Connected to AgentOS kernel")

        # Register ourselves
        result = client.register_name("net-test")
        if result.get("success"):
            print(f"[NET-TEST] Registered as 'net-test' (id={result.get('agent_id')})")
    else:
        print("[NET-TEST] Running standalone (no kernel connection)")

    print()

    # Run tests
    results, allowed, blocked = run_network_tests()

    # Summary
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print()
    print(f"  Network operations allowed: {allowed}")
    print(f"  Network operations blocked: {blocked}")
    print()

    if blocked == len(results):
        print("  ISOLATION VERIFIED: All network access blocked")
        print("  Agent is running in isolated network namespace")
        print()
        print("  This demonstrates AgentOS protection against:")
        print("    - Data exfiltration")
        print("    - C2 callbacks")
        print("    - Unauthorized API access")
    elif blocked > 0:
        print("  PARTIAL ISOLATION: Some network access blocked")
        print("  Check network namespace configuration")
    else:
        print("  NO ISOLATION: All network access allowed")
        print("  Agent has full network access")
        print()
        print("  To enable network isolation:")
        print("    client.spawn(..., network=False)")

    print()
    print("[NET-TEST] Agent exiting...")

    if client._sock:
        client.disconnect()

    return 0

if __name__ == '__main__':
    sys.exit(main())
