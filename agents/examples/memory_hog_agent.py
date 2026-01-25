#!/usr/bin/env python3
"""
Memory Hog Agent - Stress test for memory limits

This agent demonstrates kernel-level memory isolation by:
1. Connecting to the kernel
2. Continuously allocating memory
3. Getting OOM-killed when hitting cgroups memory.max limit

Expected behavior (with root/cgroups):
- Agent gets killed when memory limit exceeded
- Kernel detects OOM and logs it
- Other agents continue unaffected

Without root: may cause system-wide memory pressure.
"""

import sys
import os
import time

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))

from clove_sdk import AgentOSClient


def get_memory_mb():
    """Get current process memory usage in MB"""
    try:
        with open(f'/proc/{os.getpid()}/statm', 'r') as f:
            # statm: size resident shared text lib data dirty
            # Values are in pages (typically 4KB)
            parts = f.read().split()
            resident_pages = int(parts[1])
            return (resident_pages * 4096) / (1024 * 1024)
    except:
        return 0


def main():
    socket_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/clove.sock'

    print(f"[MEM-HOG] Starting - PID: {os.getpid()}")
    print(f"[MEM-HOG] Connecting to {socket_path}")

    client = AgentOSClient(socket_path)

    if not client.connect():
        print("[MEM-HOG] ERROR: Failed to connect")
        return 1

    # Announce ourselves
    response = client.echo(f"MEM-HOG agent started, PID={os.getpid()}")
    print(f"[MEM-HOG] Kernel acknowledged: {response}")

    print("[MEM-HOG] Starting memory allocation loop...")
    print("[MEM-HOG] (Should be OOM-killed by cgroups if running with root)")

    client.disconnect()

    # Allocate memory in chunks
    CHUNK_SIZE = 10 * 1024 * 1024  # 10MB chunks
    memory_chunks = []
    total_allocated = 0

    try:
        while True:
            # Allocate a chunk of memory
            chunk = bytearray(CHUNK_SIZE)
            # Touch it to ensure it's actually allocated
            for i in range(0, len(chunk), 4096):
                chunk[i] = 0xff
            memory_chunks.append(chunk)
            total_allocated += CHUNK_SIZE

            mem_mb = get_memory_mb()
            print(f"[MEM-HOG] Allocated {total_allocated // (1024*1024)}MB "
                  f"(process RSS: {mem_mb:.1f}MB)")

            time.sleep(0.1)  # Small delay to see output

    except MemoryError:
        print(f"[MEM-HOG] MemoryError - Python caught allocation failure")
        print(f"[MEM-HOG] Total allocated before failure: {total_allocated // (1024*1024)}MB")
    except KeyboardInterrupt:
        print(f"\n[MEM-HOG] Interrupted - allocated {total_allocated // (1024*1024)}MB")

    return 0


if __name__ == '__main__':
    sys.exit(main())
