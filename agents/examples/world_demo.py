#!/usr/bin/env python3
"""
World Simulation Demo

Demonstrates AgentOS world simulation features:
- Creating worlds with virtual filesystems
- Network mocking
- Chaos injection
- Snapshot/restore

Run the kernel first:
    cd build && ./agentos_kernel

Then run this demo:
    python3 agents/examples/world_demo.py
"""

import sys
import os
import json

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python_sdk'))
from clove_sdk import AgentOSClient


def demo_virtual_filesystem(client):
    """Demonstrate virtual filesystem isolation."""
    print("\n" + "=" * 60)
    print("DEMO 1: Virtual Filesystem")
    print("=" * 60)

    # Create a world with virtual filesystem
    config = {
        "virtual_filesystem": {
            "initial_files": {
                "/config.json": {
                    "content": '{"version": "1.0", "env": "test"}',
                    "mode": "r"  # Read-only
                },
                "/data/input.txt": {
                    "content": "Hello from virtual world!",
                    "mode": "rw"
                }
            },
            "writable_patterns": ["/data/*", "/tmp/*"],
            "readonly_patterns": ["/config.json"]
        }
    }

    print("\n1. Creating world with virtual filesystem...")
    result = client.world_create("vfs-test", config)
    if not result["success"]:
        print(f"   ERROR: {result.get('error')}")
        return
    world_id = result["world_id"]
    print(f"   Created world: {world_id}")

    print("\n2. Joining the world...")
    result = client.world_join(world_id)
    if not result["success"]:
        print(f"   ERROR: {result.get('error')}")
        return
    print(f"   Joined world: {world_id}")

    print("\n3. Reading from virtual filesystem...")
    result = client.read_file("/config.json")
    print(f"   /config.json: {result}")

    result = client.read_file("/data/input.txt")
    print(f"   /data/input.txt: {result}")

    print("\n4. Writing to virtual filesystem...")
    result = client.write_file("/data/output.txt", "This was written in the world!")
    print(f"   Write result: {result}")

    result = client.read_file("/data/output.txt")
    print(f"   Read back: {result}")

    print("\n5. Attempting to write to read-only file...")
    result = client.write_file("/config.json", "hacked!")
    print(f"   Write to /config.json: {result}")

    print("\n6. Leaving world...")
    result = client.world_leave()
    print(f"   Left world: {result}")

    print("\n7. Destroying world...")
    result = client.world_destroy(world_id)
    print(f"   Destroyed: {result}")


def demo_network_mocking(client):
    """Demonstrate network mocking."""
    print("\n" + "=" * 60)
    print("DEMO 2: Network Mocking")
    print("=" * 60)

    # Create a world with network mocks
    config = {
        "network": {
            "mode": "mock",
            "mock_responses": {
                "https://api.example.com/users": {
                    "status": 200,
                    "body": '{"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}',
                    "latency_ms": 50
                },
                "https://api.example.com/error": {
                    "status": 500,
                    "body": '{"error": "Internal Server Error"}',
                    "latency_ms": 10
                },
                "https://api.example.com/*": {
                    "status": 404,
                    "body": '{"error": "Not found"}'
                }
            },
            "fail_unmatched": True
        }
    }

    print("\n1. Creating world with network mocking...")
    result = client.world_create("network-test", config)
    if not result["success"]:
        print(f"   ERROR: {result.get('error')}")
        return
    world_id = result["world_id"]
    print(f"   Created world: {world_id}")

    print("\n2. Joining the world...")
    result = client.world_join(world_id)
    print(f"   Joined world: {world_id}")

    print("\n3. Making HTTP requests to mocked endpoints...")

    result = client.http("https://api.example.com/users")
    print(f"   GET /users: status={result.get('status_code')}, mocked={result.get('mocked')}")
    if result.get('success'):
        body = json.loads(result.get('body', '{}'))
        print(f"   Response body: {body}")

    result = client.http("https://api.example.com/error")
    print(f"   GET /error: status={result.get('status_code')}, body={result.get('body')}")

    result = client.http("https://api.example.com/nonexistent")
    print(f"   GET /nonexistent: status={result.get('status_code')}, body={result.get('body')}")

    print("\n4. Leaving and destroying world...")
    client.world_leave()
    client.world_destroy(world_id)
    print("   Done!")


def demo_chaos_engineering(client):
    """Demonstrate chaos engineering features."""
    print("\n" + "=" * 60)
    print("DEMO 3: Chaos Engineering")
    print("=" * 60)

    # Create a world with chaos enabled
    config = {
        "virtual_filesystem": {
            "initial_files": {
                "/data/important.txt": {"content": "Critical data", "mode": "rw"}
            },
            "writable_patterns": ["/data/*"]
        },
        "chaos": {
            "enabled": True,
            "failure_rate": 0.0,  # We'll inject events manually
            "latency": {"min_ms": 0, "max_ms": 100},
            "rules": [
                {
                    "type": "file_read_fail",
                    "path_pattern": "/data/flaky/*",
                    "probability": 0.5
                }
            ]
        }
    }

    print("\n1. Creating world with chaos engine...")
    result = client.world_create("chaos-test", config)
    if not result["success"]:
        print(f"   ERROR: {result.get('error')}")
        return
    world_id = result["world_id"]
    print(f"   Created world: {world_id}")

    print("\n2. Joining the world...")
    client.world_join(world_id)

    print("\n3. Normal operation - reading file...")
    result = client.read_file("/data/important.txt")
    print(f"   Read result: {result}")

    print("\n4. Injecting disk_fail chaos event...")
    result = client.world_event(world_id, "disk_fail", {})
    print(f"   Injection result: {result}")

    print("\n5. Attempting to read after chaos injection...")
    result = client.read_file("/data/important.txt")
    print(f"   Read result: {result}")

    print("\n6. Getting world state...")
    result = client.world_state(world_id)
    if result.get("success"):
        state = result.get("state", {})
        print(f"   Syscalls: {state.get('syscall_count', 0)}")
        print(f"   Chaos metrics: {state.get('chaos_metrics', {})}")

    print("\n7. Leaving and destroying world...")
    client.world_leave()
    client.world_destroy(world_id)
    print("   Done!")


def demo_snapshot_restore(client):
    """Demonstrate snapshot and restore functionality."""
    print("\n" + "=" * 60)
    print("DEMO 4: Snapshot and Restore")
    print("=" * 60)

    # Create a world with some state
    config = {
        "virtual_filesystem": {
            "initial_files": {
                "/counter.txt": {"content": "0", "mode": "rw"}
            },
            "writable_patterns": ["/**"]
        }
    }

    print("\n1. Creating world...")
    result = client.world_create("snapshot-test", config)
    world_id = result["world_id"]
    print(f"   Created world: {world_id}")

    print("\n2. Joining and modifying state...")
    client.world_join(world_id)

    # Make some changes
    for i in range(1, 4):
        client.write_file("/counter.txt", str(i))
        client.write_file(f"/file_{i}.txt", f"Content {i}")
        print(f"   Iteration {i}: wrote counter and file_{i}.txt")

    result = client.read_file("/counter.txt")
    print(f"   Counter value: {result.get('content')}")

    print("\n3. Creating snapshot...")
    client.world_leave()  # Leave before snapshot
    result = client.world_snapshot(world_id)
    if not result.get("success"):
        print(f"   ERROR: {result.get('error')}")
        return
    snapshot = result["snapshot"]
    print(f"   Snapshot created at: {snapshot.get('snapshot_time')}")
    print(f"   VFS files: {list(snapshot.get('vfs', {}).get('files', {}).keys())}")

    print("\n4. Destroying original world...")
    client.world_destroy(world_id)
    print("   Original world destroyed")

    print("\n5. Restoring from snapshot...")
    result = client.world_restore(snapshot, "restored-world")
    if not result.get("success"):
        print(f"   ERROR: {result.get('error')}")
        return
    restored_id = result["world_id"]
    print(f"   Restored as: {restored_id}")

    print("\n6. Verifying restored state...")
    client.world_join(restored_id)

    result = client.read_file("/counter.txt")
    print(f"   Counter value: {result.get('content')}")

    for i in range(1, 4):
        result = client.read_file(f"/file_{i}.txt")
        print(f"   file_{i}.txt: {result.get('content', 'NOT FOUND')}")

    print("\n7. Cleanup...")
    client.world_leave()
    client.world_destroy(restored_id)
    print("   Done!")


def demo_world_isolation(client):
    """Demonstrate isolation between worlds."""
    print("\n" + "=" * 60)
    print("DEMO 5: World Isolation")
    print("=" * 60)

    # Create two separate worlds
    config1 = {
        "virtual_filesystem": {
            "initial_files": {
                "/secret.txt": {"content": "World 1 secret", "mode": "rw"}
            },
            "writable_patterns": ["/**"]
        }
    }

    config2 = {
        "virtual_filesystem": {
            "initial_files": {
                "/secret.txt": {"content": "World 2 secret", "mode": "rw"}
            },
            "writable_patterns": ["/**"]
        }
    }

    print("\n1. Creating two worlds...")
    result1 = client.world_create("world-1", config1)
    result2 = client.world_create("world-2", config2)
    world1_id = result1["world_id"]
    world2_id = result2["world_id"]
    print(f"   World 1: {world1_id}")
    print(f"   World 2: {world2_id}")

    print("\n2. Listing all worlds...")
    result = client.world_list()
    for world in result.get("worlds", []):
        print(f"   - {world['id']} (agents: {world['agent_count']})")

    print("\n3. Testing isolation - World 1...")
    client.world_join(world1_id)
    result = client.read_file("/secret.txt")
    print(f"   World 1 secret: {result.get('content')}")
    client.write_file("/shared.txt", "Written in World 1")
    client.world_leave()

    print("\n4. Testing isolation - World 2...")
    client.world_join(world2_id)
    result = client.read_file("/secret.txt")
    print(f"   World 2 secret: {result.get('content')}")

    result = client.read_file("/shared.txt")
    print(f"   /shared.txt from World 2: {result}")  # Should not exist

    client.world_leave()

    print("\n5. Cleanup...")
    client.world_destroy(world1_id)
    client.world_destroy(world2_id)
    print("   Both worlds destroyed")


def main():
    socket_path = sys.argv[1] if len(sys.argv) > 1 else '/tmp/clove.sock'

    print("=" * 60)
    print("AgentOS World Simulation Demo")
    print("=" * 60)
    print(f"Connecting to: {socket_path}")

    client = AgentOSClient(socket_path)
    if not client.connect():
        print("ERROR: Failed to connect to kernel")
        print("Make sure the kernel is running: ./agentos_kernel")
        return 1

    try:
        # Run all demos
        demo_virtual_filesystem(client)
        demo_network_mocking(client)
        demo_chaos_engineering(client)
        demo_snapshot_restore(client)
        demo_world_isolation(client)

        print("\n" + "=" * 60)
        print("All demos completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        client.disconnect()

    return 0


if __name__ == '__main__':
    sys.exit(main())
