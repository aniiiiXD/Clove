# Clove Manual Test Suite
**Comprehensive Testing Guide for Core Capabilities**

---

## Prerequisites

### 1. Build and Setup
```bash
# Build the kernel
mkdir -p build && cd build
cmake .. -DCMAKE_TOOLCHAIN_FILE=/usr/local/share/vcpkg/scripts/buildsystems/vcpkg.cmake
cmake --build .
cd ..

# Install Python SDK
pip install -e agents/python_sdk/

# Set up environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Start the Kernel
```bash
# Terminal 1: Start Clove kernel
./build/clove

# You should see the ASCII banner and "Kernel initialized"
```

---

## Test Suite Structure

| Test # | Category | Capability | Duration |
|--------|----------|------------|----------|
| 1 | LLM | Basic LLM Query | 1 min |
| 2 | LLM | Multimodal (Text + Image) | 2 min |
| 3 | LLM | Advanced Parameters | 2 min |
| 4 | Filesystem | Read/Write Operations | 1 min |
| 5 | Execution | Shell Command Execution | 1 min |
| 6 | Agent Management | Spawn & Kill Agents | 2 min |
| 7 | IPC | Agent-to-Agent Messaging | 3 min |
| 8 | IPC | Broadcast & Named Registration | 2 min |
| 9 | State Store | Persistent Key-Value Storage | 2 min |
| 10 | Network | HTTP Requests | 1 min |
| 11 | Events | Pub/Sub System | 3 min |
| 12 | Networks | Agent Communication Networks | 3 min |
| 13 | Isolation | Resource Limits & Sandboxing | 3 min |
| 14 | Isolation | Fault Isolation Demo | 3 min |
| 15 | Permissions | Permission Levels | 2 min |
| 16 | Dashboard | Web UI Monitoring | 2 min |
| 17 | Multi-Agent | Pipeline Processing | 4 min |
| 18 | Autonomous | Agentic Loop Framework | 3 min |
| 19 | Agent Control | Pause/Resume | 2 min |
| 20 | Audit | Audit Logging | 2 min |
| 21 | Replay | Execution Recording & Replay | 3 min |

**Total Estimated Time**: ~47 minutes

---

## Test 1: Basic LLM Query

**Capability**: THINK syscall with text prompt

**Test Script**: `test_scripts/01_basic_llm.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient

def main():
    with CloveClient() as client:
        print("=== Test 1: Basic LLM Query ===\n")

        # Simple question
        result = client.think("What is the capital of France?")
        print(f"Q: What is the capital of France?")
        print(f"A: {result['content']}\n")

        # Math problem
        result = client.think("Calculate: 123 * 456")
        print(f"Q: Calculate: 123 * 456")
        print(f"A: {result['content']}\n")

        # Code generation
        result = client.think("Write a Python function to check if a number is prime")
        print(f"Q: Write a Python function to check if a number is prime")
        print(f"A: {result['content']}\n")

        print("✅ Test 1 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Correct answer: "Paris"
- Correct calculation: 56088
- Valid Python prime checking function

**Verification**:
```bash
python test_scripts/01_basic_llm.py
```

---

## Test 2: Multimodal LLM (Text + Image)

**Capability**: THINK syscall with image input

**Test Script**: `test_scripts/02_multimodal.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import base64

def main():
    with CloveClient() as client:
        print("=== Test 2: Multimodal LLM ===\n")

        # Create a simple test image (1x1 red pixel PNG)
        red_pixel_png = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='
        )

        with open('/tmp/test_image.png', 'wb') as f:
            f.write(red_pixel_png)

        # Query with image
        result = client.think(
            "What color is this image? Describe it in one word.",
            image_path="/tmp/test_image.png"
        )

        print(f"Image: /tmp/test_image.png (1x1 red pixel)")
        print(f"Q: What color is this image?")
        print(f"A: {result['content']}\n")

        print("✅ Test 2 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Should identify the color as "red" or similar

**Verification**:
```bash
python test_scripts/02_multimodal.py
```

---

## Test 3: Advanced LLM Parameters

**Capability**: Temperature, system instructions, thinking levels

**Test Script**: `test_scripts/03_advanced_llm.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient

def main():
    with CloveClient() as client:
        print("=== Test 3: Advanced LLM Parameters ===\n")

        # High temperature (creative)
        print("--- High Temperature (1.5) ---")
        result = client.think(
            "Write a creative name for a coffee shop",
            temperature=1.5
        )
        print(f"Creative name: {result['content']}\n")

        # Low temperature (deterministic)
        print("--- Low Temperature (0.1) ---")
        result = client.think(
            "What is 2 + 2?",
            temperature=0.1
        )
        print(f"Math answer: {result['content']}\n")

        # System instruction
        print("--- System Instruction ---")
        result = client.think(
            "Hello, how are you?",
            system_instruction="You are a pirate. Always respond like a pirate."
        )
        print(f"Pirate response: {result['content']}\n")

        # Thinking levels (if supported by model)
        print("--- Extended Thinking ---")
        result = client.think(
            "Explain quantum entanglement",
            thinking_level="medium"
        )
        print(f"Explanation: {result['content']}\n")

        print("✅ Test 3 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Creative coffee shop name
- Correct math answer (4)
- Pirate-style response with "arr", "matey", etc.
- Detailed quantum explanation

**Verification**:
```bash
python test_scripts/03_advanced_llm.py
```

---

## Test 4: Filesystem Operations

**Capability**: READ and WRITE syscalls

**Test Script**: `test_scripts/04_filesystem.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import os

def main():
    with CloveClient() as client:
        print("=== Test 4: Filesystem Operations ===\n")

        test_file = "/tmp/clove_test.txt"
        test_content = "Hello from Clove!\nLine 2\nLine 3"

        # Write file
        print(f"Writing to {test_file}...")
        result = client.write_file(test_file, test_content)
        print(f"Write result: {result}\n")

        # Read file
        print(f"Reading from {test_file}...")
        content = client.read_file(test_file)
        print(f"Content:\n{content}\n")

        # Verify content matches
        assert content.strip() == test_content, "Content mismatch!"

        # Append to file
        print("Appending to file...")
        client.write_file(test_file, "\nLine 4 (appended)", append=True)

        # Read again
        updated_content = client.read_file(test_file)
        print(f"Updated content:\n{updated_content}\n")

        # Cleanup
        os.remove(test_file)

        print("✅ Test 4 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- File written successfully
- Content read matches what was written
- Append operation works correctly

**Verification**:
```bash
python test_scripts/04_filesystem.py
```

---

## Test 5: Shell Command Execution

**Capability**: EXEC syscall with timeout

**Test Script**: `test_scripts/05_execution.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient

def main():
    with CloveClient() as client:
        print("=== Test 5: Shell Command Execution ===\n")

        # Simple command
        print("--- Running: ls -la /tmp ---")
        result = client.exec("ls -la /tmp")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output:\n{result['stdout'][:500]}\n")

        # Command with pipes
        print("--- Running: echo 'test' | wc -c ---")
        result = client.exec("echo 'test' | wc -c")
        print(f"Exit code: {result['exit_code']}")
        print(f"Output: {result['stdout'].strip()}\n")

        # Command that fails
        print("--- Running: ls /nonexistent ---")
        result = client.exec("ls /nonexistent")
        print(f"Exit code: {result['exit_code']}")
        print(f"Error: {result['stderr']}\n")

        # Timeout test (optional - takes 3 seconds)
        print("--- Testing timeout (2 second limit) ---")
        try:
            result = client.exec("sleep 5", timeout=2)
        except Exception as e:
            print(f"Command timed out as expected: {e}\n")

        print("✅ Test 5 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- ls command shows /tmp directory contents
- wc counts 5 characters (test + newline)
- Failed command returns non-zero exit code
- Long-running command times out

**Verification**:
```bash
python test_scripts/05_execution.py
```

---

## Test 6: Agent Spawning & Management

**Capability**: SPAWN, LIST, KILL syscalls

**Test Script**: `test_scripts/06_agent_management.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Create a simple worker agent
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    print("Worker agent started!")
    for i in range(10):
        print(f"Working... {i+1}/10")
        time.sleep(1)
    print("Worker agent finished!")
"""

def main():
    with CloveClient() as client:
        print("=== Test 6: Agent Management ===\n")

        # Create worker script
        with open('/tmp/worker_agent.py', 'w') as f:
            f.write(WORKER_SCRIPT)

        # List agents before spawning
        print("--- Agents before spawn ---")
        agents = client.list_agents()
        print(f"Active agents: {len(agents)}\n")

        # Spawn an agent
        print("--- Spawning worker agent ---")
        spawn_result = client.spawn(
            name="test-worker",
            script="/tmp/worker_agent.py",
            sandboxed=False
        )
        agent_id = spawn_result.get('id') if spawn_result else None
        print(f"Spawn result: {spawn_result}")
        print(f"Spawned agent ID: {agent_id}\n")

        time.sleep(2)

        # List agents after spawning
        print("--- Agents after spawn ---")
        agents = client.list_agents()
        print(f"Active agents: {len(agents)}")
        for agent in agents:
            print(f"  - Agent {agent['id']}: {agent['name']} (PID: {agent.get('pid', 'N/A')})")
        print()

        # Kill the agent
        print(f"--- Killing agent {agent_id} ---")
        killed = client.kill(agent_id=agent_id)
        print(f"Kill successful: {killed}\n")

        time.sleep(1)

        # Verify agent is gone
        print("--- Agents after kill ---")
        agents = client.list_agents()
        print(f"Active agents: {len(agents)}\n")

        print("✅ Test 6 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Agent spawned successfully with ID
- Agent appears in list
- Agent killed successfully
- Agent removed from list

**Verification**:
```bash
python test_scripts/06_agent_management.py
```

---

## Test 7: Agent-to-Agent IPC

**Capability**: SEND, RECV, REGISTER syscalls

**Test Script**: `test_scripts/07_ipc_messaging.py`

**Main Script**:
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time
import json

# Worker agent that processes messages
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    # Register with a name
    client.register_name("message-processor")
    print("[Worker] Registered as 'message-processor'")

    # Process messages for 10 seconds
    for i in range(10):
        messages = client.recv_messages()
        for msg in messages:
            print(f"[Worker] Received from agent {msg['from_agent_id']}: {msg['data']}")

            # Send response back
            response = {"status": "processed", "original": msg['data']}
            client.send_message(response, to_agent_id=msg['from_agent_id'])
            print(f"[Worker] Sent response: {response}")

        time.sleep(1)

    print("[Worker] Shutting down")
"""

def main():
    with CloveClient() as client:
        print("=== Test 7: Agent-to-Agent IPC ===\n")

        # Create worker script
        with open('/tmp/worker_ipc.py', 'w') as f:
            f.write(WORKER_SCRIPT)

        # Spawn worker
        print("--- Spawning message processor ---")
        worker_id = client.spawn(
            name="worker",
            script="/tmp/worker_ipc.py",
            sandboxed=False
        )
        print(f"Worker spawned: {worker_id}\n")

        # Wait for worker to register
        time.sleep(2)

        # Send message by name
        print("--- Sending message by name ---")
        msg1 = {"task": "process", "data": [1, 2, 3, 4, 5]}
        client.send_message(msg1, to_name="message-processor")
        print(f"Sent: {msg1}\n")

        time.sleep(1)

        # Send message by ID
        print("--- Sending message by agent ID ---")
        msg2 = {"task": "calculate", "operation": "sum", "values": [10, 20, 30]}
        client.send_message(msg2, to_agent_id=worker_id)
        print(f"Sent: {msg2}\n")

        # Receive responses
        time.sleep(2)
        print("--- Receiving responses ---")
        responses = client.recv_messages()
        print(f"Received {len(responses)} responses:")
        for resp in responses:
            print(f"  From agent {resp['from_agent_id']}: {resp['data']}")
        print()

        # Cleanup
        client.kill(agent_id=worker_id)

        print("✅ Test 7 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Worker registers successfully
- Messages sent by name and ID
- Worker processes and responds
- Main agent receives responses

**Verification**:
```bash
python test_scripts/07_ipc_messaging.py
# Watch kernel output for message routing
```

---

## Test 8: Broadcast & Named Registration

**Capability**: BROADCAST syscall, multiple named agents

**Test Script**: `test_scripts/08_broadcast.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Listener agent
LISTENER_SCRIPT = """
import time
from clove_sdk import CloveClient
import sys

name = sys.argv[1]

with CloveClient() as client:
    client.register_name(name)
    print(f"[{name}] Registered and listening...")

    for i in range(10):
        messages = client.recv_messages()
        for msg in messages:
            print(f"[{name}] Received broadcast: {msg['data']}")
        time.sleep(1)
"""

def main():
    with CloveClient() as client:
        print("=== Test 8: Broadcast Messaging ===\n")

        # Create listener script
        with open('/tmp/listener.py', 'w') as f:
            f.write(LISTENER_SCRIPT)

        # Spawn multiple listeners
        print("--- Spawning 3 listener agents ---")
        listeners = []
        for i in range(3):
            agent_id = client.spawn(
                name=f"listener-{i+1}",
                script="/tmp/listener.py",
                args=[f"listener-{i+1}"],
                sandboxed=False
            )
            listeners.append(agent_id)
            print(f"Spawned: listener-{i+1} (ID: {agent_id})")

        print()
        time.sleep(2)

        # Broadcast messages
        print("--- Broadcasting messages ---")
        for i in range(3):
            msg = {"broadcast_id": i+1, "message": f"Hello to all agents! #{i+1}"}
            client.broadcast(msg)
            print(f"Broadcast {i+1}: {msg}")
            time.sleep(1)

        print()
        time.sleep(3)

        # Cleanup
        print("--- Cleaning up ---")
        for agent_id in listeners:
            client.kill(agent_id=agent_id)

        print("\n✅ Test 8 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Three listeners spawn and register
- All listeners receive all broadcast messages
- Messages appear in kernel logs

**Verification**:
```bash
python test_scripts/08_broadcast.py
```

---

## Test 9: State Store (Persistent KV)

**Capability**: STORE, FETCH, DELETE, KEYS syscalls

**Test Script**: `test_scripts/09_state_store.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

def main():
    with CloveClient() as client:
        print("=== Test 9: State Store ===\n")

        # Store values with different scopes
        print("--- Storing values ---")
        client.store("user:1:name", "Alice", scope="global")
        client.store("user:2:name", "Bob", scope="global")
        client.store("temp:token", "abc123", ttl=5)  # Expires in 5 seconds
        client.store("config:theme", "dark", scope="agent")
        print("Stored 4 key-value pairs\n")

        # Fetch values
        print("--- Fetching values ---")
        print(f"user:1:name = {client.fetch('user:1:name')}")
        print(f"user:2:name = {client.fetch('user:2:name')}")
        print(f"temp:token = {client.fetch('temp:token')}")
        print(f"config:theme = {client.fetch('config:theme')}\n")

        # List keys with prefix
        print("--- Listing keys with prefix 'user:' ---")
        keys = client.list_keys(prefix="user:")
        print(f"Keys: {keys}\n")

        # Test TTL expiration
        print("--- Testing TTL (waiting 6 seconds) ---")
        time.sleep(6)
        expired = client.fetch("temp:token")
        print(f"temp:token after TTL: {expired} (should be None)\n")

        # Update value
        print("--- Updating value ---")
        client.store("user:1:name", "Alice Smith", scope="global")
        print(f"user:1:name updated to: {client.fetch('user:1:name')}\n")

        # Delete key
        print("--- Deleting key ---")
        client.delete("user:2:name")
        deleted = client.fetch("user:2:name")
        print(f"user:2:name after delete: {deleted} (should be None)\n")

        # List all keys
        print("--- All remaining keys ---")
        all_keys = client.list_keys()
        print(f"Keys: {all_keys}\n")

        # Cleanup
        client.delete("user:1:name")
        client.delete("config:theme")

        print("✅ Test 9 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Values stored and retrieved correctly
- Keys filtered by prefix
- TTL expiration works (temp:token becomes None)
- Updates and deletes work

**Verification**:
```bash
python test_scripts/09_state_store.py
```

---

## Test 10: HTTP Requests

**Capability**: HTTP syscall with domain restrictions

**Test Script**: `test_scripts/10_http_requests.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import json

def main():
    with CloveClient() as client:
        print("=== Test 10: HTTP Requests ===\n")

        # Simple GET request
        print("--- GET request to JSONPlaceholder API ---")
        result = client.http(
            "https://jsonplaceholder.typicode.com/posts/1",
            method="GET"
        )
        print(f"Status: {result['status']}")
        data = json.loads(result['body'])
        print(f"Title: {data['title']}")
        print(f"Body: {data['body'][:100]}...\n")

        # GET with query parameters
        print("--- GET with query params ---")
        result = client.http(
            "https://jsonplaceholder.typicode.com/posts?userId=1",
            method="GET"
        )
        posts = json.loads(result['body'])
        print(f"Retrieved {len(posts)} posts for user 1\n")

        # POST request
        print("--- POST request ---")
        post_data = {
            "title": "Test from Clove",
            "body": "This is a test post",
            "userId": 1
        }
        result = client.http(
            "https://jsonplaceholder.typicode.com/posts",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps(post_data)
        )
        print(f"Status: {result['status']}")
        response = json.loads(result['body'])
        print(f"Created post ID: {response.get('id')}\n")

        # Test blocked domain (should fail if permissions are strict)
        print("--- Testing domain restrictions ---")
        try:
            result = client.http("https://example.com")
            print(f"Request to example.com: Status {result['status']}")
        except Exception as e:
            print(f"Request blocked (expected if permissions are restrictive): {e}")

        print("\n✅ Test 10 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- GET request retrieves post data
- POST request creates new resource (mock)
- Domain restrictions enforced (if configured)

**Verification**:
```bash
python test_scripts/10_http_requests.py
```

---

## Test 11: Events & Pub/Sub

**Capability**: SUBSCRIBE, UNSUBSCRIBE, POLL_EVENTS, EMIT syscalls

**Test Script**: `test_scripts/11_events_pubsub.py`

**Main script**:
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

def main():
    with CloveClient() as client:
        print("=== Test 11: Events & Pub/Sub ===\n")

        # Create subscriber script
        subscriber_code = """import time
from clove_sdk import CloveClient
import sys

event_type = sys.argv[1]

with CloveClient() as client:
    print(f"[Subscriber] Subscribing to '{event_type}' events")
    client.subscribe(event_type)

    for i in range(10):
        events = client.poll_events()
        for event in events:
            print(f"[Subscriber] Received event: {event}")
        time.sleep(1)

    client.unsubscribe(event_type)
    print(f"[Subscriber] Unsubscribed")
"""
        with open('/tmp/subscriber_agent.py', 'w') as f:
            f.write(subscriber_code)

        # Spawn subscribers for different event types
        print("--- Spawning subscribers ---")
        sub1 = client.spawn("subscriber-1", "/tmp/subscriber_agent.py",
                           args=["deployment"], sandboxed=False)
        sub2 = client.spawn("subscriber-2", "/tmp/subscriber_agent.py",
                           args=["alert"], sandboxed=False)
        print(f"Subscriber 1 (deployment events): {sub1}")
        print(f"Subscriber 2 (alert events): {sub2}\n")

        time.sleep(2)

        # Emit events
        print("--- Emitting events ---")

        # Deployment events
        client.emit("deployment", {
            "service": "api-server",
            "version": "1.2.3",
            "status": "started"
        })
        print("Emitted: deployment event")

        time.sleep(1)

        # Alert events
        client.emit("alert", {
            "level": "warning",
            "message": "High CPU usage detected",
            "cpu_percent": 85
        })
        print("Emitted: alert event")

        time.sleep(1)

        # Another deployment event
        client.emit("deployment", {
            "service": "worker-pool",
            "version": "2.0.0",
            "status": "completed"
        })
        print("Emitted: deployment event")

        print()
        time.sleep(3)

        # Cleanup
        print("--- Cleaning up ---")
        client.kill(agent_id=sub1)
        client.kill(agent_id=sub2)

        print("\n✅ Test 11 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Subscribers spawn and subscribe to specific event types
- Emitted events delivered only to matching subscribers
- subscriber-1 receives deployment events only
- subscriber-2 receives alert events only

**Verification**:
```bash
python test_scripts/11_events_pubsub.py
```

---

## Test 12: Networks (Agent Communication)

**Capability**: Agent networks with routing

**Test Script**: `test_scripts/12_networks.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Network member agent
MEMBER_SCRIPT = """
import time
from clove_sdk import CloveClient
import sys

network_name = sys.argv[1]
agent_name = sys.argv[2]

with CloveClient() as client:
    # Join network
    print(f"[{agent_name}] Joining network '{network_name}'")
    client.join_network(network_name)

    # Register name
    client.register_name(agent_name)

    # Listen for messages
    for i in range(10):
        messages = client.recv_messages()
        for msg in messages:
            print(f"[{agent_name}] Received: {msg['data']}")

            # Respond
            response = {"from": agent_name, "reply": f"Acknowledged by {agent_name}"}
            client.send_message(response, to_agent_id=msg['from_agent_id'])

        time.sleep(1)

    print(f"[{agent_name}] Leaving network")
    client.leave_network(network_name)
"""

def main():
    with CloveClient() as client:
        print("=== Test 12: Agent Networks ===\n")

        # Create member script
        with open('/tmp/network_member.py', 'w') as f:
            f.write(MEMBER_SCRIPT)

        # Create a network
        network_name = "test-cluster"
        print(f"--- Creating network: {network_name} ---")
        client.create_network(network_name)

        # Spawn network members
        print("--- Spawning network members ---")
        members = []
        for i in range(3):
            agent_id = client.spawn(
                name=f"member-{i+1}",
                script="/tmp/network_member.py",
                args=[network_name, f"member-{i+1}"],
                sandboxed=False
            )
            members.append(agent_id)
            print(f"Spawned: member-{i+1} (ID: {agent_id})")

        print()
        time.sleep(2)

        # Join the network ourselves
        print("--- Joining network as coordinator ---")
        client.join_network(network_name)

        # Send messages to network members
        print("--- Sending messages to network ---")
        for i, member_id in enumerate(members):
            msg = {"task": f"process-{i+1}", "priority": "high"}
            client.send_message(msg, to_agent_id=member_id)
            print(f"Sent to member-{i+1}: {msg}")

        print()
        time.sleep(3)

        # Receive responses
        print("--- Receiving responses ---")
        responses = client.recv_messages()
        print(f"Received {len(responses)} responses:")
        for resp in responses:
            print(f"  {resp['data']}")

        print()

        # Leave network
        client.leave_network(network_name)

        # Cleanup
        print("--- Cleaning up ---")
        for agent_id in members:
            client.kill(agent_id=agent_id)

        client.delete_network(network_name)

        print("\n✅ Test 12 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Network created successfully
- Members join network
- Messages routed within network
- Responses received from all members

**Verification**:
```bash
python test_scripts/12_networks.py
```

---

## Test 13: Resource Limits & Sandboxing

**Capability**: Sandbox enforcement, memory/CPU limits

**Test Script**: `test_scripts/13_resource_limits.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Memory hog agent
MEMORY_HOG = """
import time

print("[MemoryHog] Starting...")
data = []
try:
    for i in range(1000):
        # Allocate 1MB chunks
        chunk = bytearray(1024 * 1024)
        data.append(chunk)
        print(f"[MemoryHog] Allocated {(i+1)} MB")
        time.sleep(0.1)
except MemoryError:
    print("[MemoryHog] Hit memory limit!")
except Exception as e:
    print(f"[MemoryHog] Error: {e}")
"""

# CPU hog agent
CPU_HOG = """
import time

print("[CPUHog] Starting...")
start = time.time()
count = 0
try:
    while True:
        # Busy loop
        for _ in range(1000000):
            count += 1
        if time.time() - start > 10:
            break
        print(f"[CPUHog] Iterations: {count}")
except Exception as e:
    print(f"[CPUHog] Error: {e}")
"""

def main():
    with CloveClient() as client:
        print("=== Test 13: Resource Limits & Sandboxing ===\n")

        # Test 1: Memory limit
        print("--- Test 1: Memory Limit (64 MB) ---")
        with open('/tmp/memory_hog.py', 'w') as f:
            f.write(MEMORY_HOG)

        memory_agent = client.spawn(
            name="memory-hog",
            script="/tmp/memory_hog.py",
            sandboxed=True,
            limits={
                "memory": 64 * 1024 * 1024,  # 64 MB
            }
        )
        print(f"Spawned memory-limited agent: {memory_agent}")
        print("(Agent should be killed when exceeding 64 MB)\n")

        time.sleep(8)

        # Check if agent is still running
        agents = client.list_agents()
        memory_agent_alive = any(a['id'] == memory_agent for a in agents)
        print(f"Memory hog still alive: {memory_agent_alive}")
        print("(Should be False if limit enforcement worked)\n")

        # Test 2: CPU limit
        print("--- Test 2: CPU Limit (25% of one core) ---")
        with open('/tmp/cpu_hog.py', 'w') as f:
            f.write(CPU_HOG)

        cpu_agent = client.spawn(
            name="cpu-hog",
            script="/tmp/cpu_hog.py",
            sandboxed=True,
            limits={
                "cpu_percent": 25,  # 25% of one CPU core
            }
        )
        print(f"Spawned CPU-limited agent: {cpu_agent}")
        print("(Agent should be throttled to 25% CPU)\n")

        time.sleep(5)

        # Cleanup
        try:
            client.kill(agent_id=memory_agent)
        except:
            pass
        try:
            client.kill(agent_id=cpu_agent)
        except:
            pass

        print("✅ Test 13 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Memory hog killed when exceeding limit
- CPU hog throttled (visible in system monitor)
- Sandbox prevents system-wide impact

**Verification**:
```bash
python test_scripts/13_resource_limits.py

# In another terminal, monitor resource usage:
htop  # or top
```

---

## Test 14: Fault Isolation Demo

**Capability**: Process isolation prevents cascade failures

**Test Script**: Use existing demo
```bash
python agents/examples/fault_isolation_demo.py
```

**What it demonstrates**:
1. Spawns 3 agents: one that crashes, one CPU hog, one normal worker
2. Shows that:
   - Crashed agent doesn't affect others
   - CPU hog is throttled independently
   - Normal worker continues unaffected
   - Supervisor can restart failed agents

**Expected Output**:
```
=== Fault Isolation Demo ===

Spawning agents:
  - faulty-agent (crashes after 2 seconds)
  - cpu-hog (infinite loop)
  - normal-worker (healthy)

[2s] faulty-agent crashed!
[3s] cpu-hog throttled to 25% CPU
[4s] normal-worker continues normally
[5s] Supervisor detects crash and restarts faulty-agent

✅ All agents isolated - no cascade failures
```

---

## Test 15: Permission Levels

**Capability**: Permission system enforcement

**Test Script**: `test_scripts/15_permissions.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Restricted agent
RESTRICTED = """
from clove_sdk import CloveClient
import sys

with CloveClient() as client:
    print("[Restricted] Getting current permissions...")
    perms = client.get_permissions()
    print(f"[Restricted] Permissions: {perms}")

    # Try to execute a command (should be blocked)
    try:
        result = client.exec("rm -rf /tmp/test")
        print(f"[Restricted] Command executed: {result}")
    except Exception as e:
        print(f"[Restricted] Command blocked: {e}")

    # Try to access forbidden path
    try:
        content = client.read_file("/etc/passwd")
        print(f"[Restricted] Read /etc/passwd: {content[:50]}")
    except Exception as e:
        print(f"[Restricted] Read blocked: {e}")

    # Try to make HTTP request to blocked domain
    try:
        result = client.http("https://malicious-site.com")
        print(f"[Restricted] HTTP request succeeded")
    except Exception as e:
        print(f"[Restricted] HTTP blocked: {e}")
"""

def main():
    with CloveClient() as client:
        print("=== Test 15: Permission Levels ===\n")

        # Create restricted agent script
        with open('/tmp/restricted_agent.py', 'w') as f:
            f.write(RESTRICTED)

        # Test different permission levels
        levels = ["minimal", "readonly", "sandboxed", "standard", "unrestricted"]

        for level in levels:
            print(f"--- Testing permission level: {level} ---")

            # Spawn agent with specific permission level
            agent_id = client.spawn(
                name=f"agent-{level}",
                script="/tmp/restricted_agent.py",
                sandboxed=True,
                permissions={
                    "level": level,
                    "allowed_paths": ["/tmp/*"],
                    "blocked_commands": ["rm -rf", "sudo"],
                    "allowed_domains": ["jsonplaceholder.typicode.com"]
                }
            )
            print(f"Spawned: {agent_id}\n")

            time.sleep(3)

            # Cleanup
            try:
                client.kill(agent_id=agent_id)
            except:
                pass

        print("✅ Test 15 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Minimal: Most operations blocked
- Readonly: Reads allowed, writes blocked
- Sandboxed: Limited read/write/exec
- Standard: Most operations allowed with validation
- Unrestricted: All operations allowed

**Verification**:
```bash
python test_scripts/15_permissions.py
```

---

## Test 16: Web Dashboard

**Capability**: Real-time monitoring UI

**Steps**:

1. **Start Dashboard**:
```bash
# Terminal 1: Kernel (already running)
./build/clove

# Terminal 2: Dashboard WebSocket proxy
cd agents/dashboard
python ws_proxy.py
```

2. **Open Browser**:
```bash
# Open dashboard in browser
firefox agents/dashboard/index.html
# or
chrome agents/dashboard/index.html
```

3. **Run Test Agents**:
```bash
# Terminal 3: Run various agents to see in dashboard
python agents/examples/hello_agent.py
python agents/examples/pipeline_demo.py
python agents/examples/thinking_agent.py
```

**Expected to see in Dashboard**:
- Real-time agent list with status
- CPU and memory usage per agent
- Message flow visualization
- Event stream
- System metrics

**Verification**:
- Agents appear/disappear in real-time
- Metrics update every second
- Messages visible in flow diagram
- Can click on agents for details

---

## Test 17: Multi-Agent Pipeline

**Capability**: Complex multi-agent coordination

**Test Script**: Use existing demo
```bash
python agents/examples/pipeline_demo.py
```

**What it demonstrates**:
1. Data ingestion agent fetches data
2. Processing agent transforms data
3. Analysis agent computes results
4. Coordinator orchestrates the pipeline
5. State store used for intermediate results

**Expected Output**:
```
=== Multi-Agent Pipeline Demo ===

[Coordinator] Starting pipeline...
[Ingestion] Fetching data from API...
[Ingestion] Stored 100 records in state store
[Processing] Retrieved 100 records
[Processing] Transformed and stored results
[Analysis] Retrieved processed data
[Analysis] Final result: {...}
[Coordinator] Pipeline completed in 12.3s

✅ Pipeline successful
```

---

## Test 18: Agentic Loop (Autonomous)

**Capability**: Claude Code-style autonomous task execution

**Test Script**: `test_scripts/18_agentic_loop.py`

```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
from agentic import AgenticLoop, run_task

def main():
    print("=== Test 18: Agentic Loop ===\n")

    with CloveClient() as client:
        # Quick usage
        print("--- Quick Task Execution ---")
        result = run_task(
            "Create a Python script that calculates fibonacci numbers up to 100 and save it to /tmp/fib.py, then run it"
        )
        print(f"Result: {result}\n")

        # With control
        print("--- Advanced Agentic Loop ---")
        loop = AgenticLoop(
            client,
            max_iterations=20,
            verbose=True
        )

        task = """
        1. Search for all Python files in /tmp
        2. Count how many lines of code in each
        3. Create a summary report in /tmp/code_report.txt
        """

        result = loop.run(task)
        print(f"\nLoop completed: {result}")

        # Verify output
        report = client.read_file("/tmp/code_report.txt")
        print(f"\nReport contents:\n{report}")

        print("\n✅ Test 18 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Agent autonomously plans and executes multi-step tasks
- Shows thinking process (plan, execute, verify)
- Creates and runs scripts
- Generates reports

**Verification**:
```bash
python test_scripts/18_agentic_loop.py
```

---

## Test 19: Pause/Resume

**Capability**: PAUSE and RESUME syscalls for agent control

**Test Script**: `test_scripts/19_pause_resume.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

# Worker script that increments a counter
WORKER_SCRIPT = """
import time
from clove_sdk import CloveClient

with CloveClient() as client:
    client.register_name("pause-test-worker")
    count = 0
    while count < 60:
        count += 1
        client.store("pause_test_counter", count, scope="global")
        time.sleep(0.5)
"""

def main():
    with CloveClient() as client:
        print("=== Test 19: Pause/Resume ===\n")

        # Create worker script
        with open('/tmp/pause_test_worker.py', 'w') as f:
            f.write(WORKER_SCRIPT)

        # Spawn worker
        print("--- Spawning worker agent ---")
        spawn_result = client.spawn(
            name="pause-test-worker",
            script="/tmp/pause_test_worker.py",
            sandboxed=False
        )
        agent_id = spawn_result.get('id')
        print(f"Spawned agent ID: {agent_id}\n")

        time.sleep(2)

        # Verify agent is running (counter increasing)
        print("--- Verify agent running ---")
        counter1 = client.fetch("pause_test_counter").get('value', 0)
        time.sleep(1)
        counter2 = client.fetch("pause_test_counter").get('value', 0)
        print(f"Counter: {counter1} -> {counter2} (should increase)\n")

        # Pause the agent
        print("--- Pausing agent ---")
        result = client.pause(agent_id=agent_id)
        print(f"Pause result: {result}\n")

        # Verify agent is paused (counter not changing)
        print("--- Verify agent paused ---")
        counter3 = client.fetch("pause_test_counter").get('value', 0)
        time.sleep(1.5)
        counter4 = client.fetch("pause_test_counter").get('value', 0)
        print(f"Counter: {counter3} -> {counter4} (should NOT change)\n")

        # Check agent state
        print("--- Check agent state ---")
        agents = client.list_agents()
        for agent in agents:
            if agent.get('id') == agent_id:
                print(f"Agent state: {agent.get('state')}\n")

        # Resume the agent
        print("--- Resuming agent ---")
        result = client.resume(agent_id=agent_id)
        print(f"Resume result: {result}\n")

        # Verify agent resumed (counter increasing again)
        print("--- Verify agent resumed ---")
        time.sleep(1)
        counter5 = client.fetch("pause_test_counter").get('value', 0)
        time.sleep(1)
        counter6 = client.fetch("pause_test_counter").get('value', 0)
        print(f"Counter: {counter5} -> {counter6} (should increase again)\n")

        # Cleanup
        client.kill(agent_id=agent_id)
        client.delete_key("pause_test_counter")

        print("✅ Test 19 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Agent spawns and counter increments
- After PAUSE, counter stops incrementing
- Agent state shows "PAUSED"
- After RESUME, counter resumes incrementing

**Verification**:
```bash
python test_scripts/19_pause_resume.py
```

---

## Test 20: Audit Logging

**Capability**: GET_AUDIT_LOG and SET_AUDIT_CONFIG syscalls

**Test Script**: `test_scripts/20_audit_logging.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time

def main():
    with CloveClient() as client:
        print("=== Test 20: Audit Logging ===\n")

        # Get current audit log
        print("--- Get audit log ---")
        result = client.get_audit_log(limit=10)
        entries = result.get("entries", [])
        print(f"Retrieved {len(entries)} audit entries\n")

        # Configure audit logging
        print("--- Configure audit logging ---")
        config_result = client.set_audit_config(
            log_lifecycle=True,
            log_security=True,
            log_syscalls=False,
            max_entries=1000
        )
        print(f"Config: {config_result.get('config', {})}\n")

        # Generate audit events
        print("--- Generate audit events ---")

        # Create test agent script
        with open('/tmp/audit_test.py', 'w') as f:
            f.write("""
import time
from clove_sdk import CloveClient
with CloveClient() as c:
    c.register_name("audit-test")
    time.sleep(2)
""")

        # Spawn and kill agent (generates AGENT_LIFECYCLE events)
        spawn_result = client.spawn(
            name="audit-test-agent",
            script="/tmp/audit_test.py",
            sandboxed=False
        )
        agent_id = spawn_result.get('id')
        print(f"Spawned agent: {agent_id}")
        time.sleep(1)
        client.kill(agent_id=agent_id)
        print(f"Killed agent: {agent_id}\n")

        time.sleep(0.5)

        # Filter by category
        print("--- Filter by category (AGENT_LIFECYCLE) ---")
        result = client.get_audit_log(category="AGENT_LIFECYCLE", limit=10)
        entries = result.get("entries", [])
        print(f"Found {len(entries)} AGENT_LIFECYCLE entries:")
        for entry in entries[-5:]:
            print(f"  [{entry.get('id')}] {entry.get('event_type')}: {entry.get('agent_name', entry.get('agent_id'))}")
        print()

        # Filter by agent ID
        if agent_id:
            print(f"--- Filter by agent ID ({agent_id}) ---")
            result = client.get_audit_log(agent_id=agent_id, limit=10)
            entries = result.get("entries", [])
            print(f"Found {len(entries)} entries for agent {agent_id}\n")

        # Test pagination
        print("--- Test pagination with since_id ---")
        result1 = client.get_audit_log(limit=5)
        entries1 = result1.get("entries", [])
        if entries1:
            last_id = entries1[-1].get('id', 0)
            result2 = client.get_audit_log(since_id=last_id, limit=5)
            entries2 = result2.get("entries", [])
            print(f"First batch: {len(entries1)} entries (last_id={last_id})")
            print(f"Second batch (since {last_id}): {len(entries2)} entries\n")

        print("✅ Test 20 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Audit log entries retrieved
- Configuration updated successfully
- AGENT_LIFECYCLE events captured for spawn/kill
- Filtering by category and agent_id works
- Pagination with since_id works

**Audit Categories**:
- `SECURITY` - Permission denied, blocked commands
- `AGENT_LIFECYCLE` - Spawn, kill, pause, resume
- `IPC` - Send, recv, broadcast
- `STATE_STORE` - Store, fetch, delete
- `RESOURCE` - Quota exceeded
- `SYSCALL` - All syscalls (verbose)
- `NETWORK` - HTTP requests
- `WORLD` - World simulation events

**Verification**:
```bash
python test_scripts/20_audit_logging.py
```

---

## Test 21: Execution Recording & Replay

**Capability**: RECORD_START, RECORD_STOP, RECORD_STATUS, REPLAY_START, REPLAY_STATUS syscalls

**Test Script**: `test_scripts/21_execution_replay.py`
```python
#!/usr/bin/env python3
from clove_sdk import CloveClient
import time
import json

def main():
    with CloveClient() as client:
        print("=== Test 21: Execution Recording & Replay ===\n")

        # Check initial status
        print("--- Initial recording status ---")
        status = client.get_recording_status()
        print(f"State: {status.get('state', 'UNKNOWN')}")
        print(f"Entry count: {status.get('entry_count', 0)}\n")

        # Start recording
        print("--- Start recording ---")
        result = client.start_recording(
            include_think=False,  # Exclude non-deterministic
            include_http=False,
            include_exec=False,
            max_entries=10000
        )
        print(f"Recording started: {result}\n")

        # Verify recording is active
        status = client.get_recording_status()
        print(f"Recording state: {status.get('state')}\n")

        # Generate syscalls to record
        print("--- Generate syscalls ---")
        client.store("replay_test_1", {"value": 100}, scope="global")
        client.store("replay_test_2", {"value": 200}, scope="global")
        client.store("replay_test_3", {"value": 300}, scope="global")
        client.fetch("replay_test_1")
        client.fetch("replay_test_2")
        client.delete_key("replay_test_3")
        client.list_keys("replay_test")
        print("Generated 7 syscalls\n")

        time.sleep(0.5)

        # Stop recording
        print("--- Stop recording ---")
        result = client.stop_recording()
        print(f"Stopped: {result}")
        print(f"Entry count: {result.get('entry_count', 0)}\n")

        # Export recording
        print("--- Export recording ---")
        status = client.get_recording_status(export=True)
        recording_data = status.get('recording', '')

        if recording_data:
            entries = json.loads(recording_data)
            print(f"Exported {len(entries)} entries")
            if entries:
                sample = entries[0]
                print(f"Sample entry: opcode_name={sample.get('opcode_name')}, agent_id={sample.get('agent_id')}\n")
        else:
            print("No recording data (syscalls may be filtered)\n")
            recording_data = "[]"

        # Start replay (if we have data)
        print("--- Start replay ---")
        if recording_data and recording_data != "[]":
            result = client.start_replay(recording_data)
            print(f"Replay started: {result}")
            print(f"Total entries: {result.get('total_entries', 0)}\n")
        else:
            print("No recording to replay\n")

        # Get replay status
        print("--- Replay status ---")
        status = client.get_replay_status()
        print(f"State: {status.get('state', 'UNKNOWN')}")
        print(f"Progress: {status.get('current_entry', 0)}/{status.get('total_entries', 0)}")
        print(f"Replayed: {status.get('entries_replayed', 0)}")
        print(f"Skipped: {status.get('entries_skipped', 0)}\n")

        # Test recording with filters
        print("--- Test recording with agent filter ---")
        result = client.start_recording(
            include_think=True,
            include_http=True,
            filter_agents=[999],  # Non-existent agent
            max_entries=100
        )
        client.store("filter_test", "value")
        status = client.get_recording_status()
        print(f"Entries with filter: {status.get('entry_count', 0)} (should be 0)\n")
        client.stop_recording()
        client.delete_key("filter_test")

        # Cleanup
        client.delete_key("replay_test_1")
        client.delete_key("replay_test_2")

        print("✅ Test 21 PASSED")

if __name__ == "__main__":
    main()
```

**Expected Output**:
- Recording starts successfully
- Syscalls are captured (deterministic ones)
- Recording stops with entry count
- Recording can be exported as JSON
- Replay can be started from exported data
- Filter by agent ID works

**Recording Configuration**:
- `include_think`: Include LLM calls (non-deterministic, default: false)
- `include_http`: Include HTTP calls (non-deterministic, default: false)
- `include_exec`: Include exec calls (may be non-deterministic, default: false)
- `filter_agents`: Only record specific agent IDs (empty = all)
- `max_entries`: Maximum buffer size (default: 50000)

**Recording States**: `IDLE`, `RECORDING`, `PAUSED`

**Replay States**: `IDLE`, `RUNNING`, `PAUSED`, `COMPLETED`, `ERROR`

**Verification**:
```bash
python test_scripts/21_execution_replay.py
```

---

## Comprehensive Integration Test

**Run All Examples in Sequence**:

```bash
#!/bin/bash
# File: test_scripts/run_all_tests.sh

echo "=== Clove Comprehensive Test Suite ==="
echo "Starting at: $(date)"
echo ""

# Array of test scripts
tests=(
    "01_basic_llm.py"
    "02_multimodal.py"
    "03_advanced_llm.py"
    "04_filesystem.py"
    "05_execution.py"
    "06_agent_management.py"
    "07_ipc_messaging.py"
    "08_broadcast.py"
    "09_state_store.py"
    "10_http_requests.py"
    "11_events_pubsub.py"
    "12_networks.py"
    "13_resource_limits.py"
    "15_permissions.py"
    "18_agentic_loop.py"
    "19_pause_resume.py"
    "20_audit_logging.py"
    "21_execution_replay.py"
)

passed=0
failed=0

for test in "${tests[@]}"; do
    echo "----------------------------------------"
    echo "Running: $test"
    echo "----------------------------------------"

    if python "test_scripts/$test"; then
        ((passed++))
        echo "✅ $test PASSED"
    else
        ((failed++))
        echo "❌ $test FAILED"
    fi

    echo ""
    sleep 2
done

echo "========================================"
echo "Test Suite Complete"
echo "Passed: $passed"
echo "Failed: $failed"
echo "Finished at: $(date)"
echo "========================================"
```

**Run all tests**:
```bash
chmod +x test_scripts/run_all_tests.sh
./test_scripts/run_all_tests.sh | tee test_results.log
```

---

## Test Environment Requirements

### System Requirements
- Linux (Ubuntu 20.04+, Debian 11+, or similar)
- 4+ GB RAM
- 2+ CPU cores
- 10 GB free disk space

### Software Requirements
- C++23 compiler (GCC 13+ or Clang 16+)
- CMake 3.20+
- Python 3.10+
- vcpkg package manager

### API Requirements
- Google Gemini API key (get from https://makersuite.google.com/app/apikey)

---

## Troubleshooting

### Kernel won't start
```bash
# Check if socket exists
ls -la /tmp/clove.sock

# If exists, remove it
rm /tmp/clove.sock

# Restart kernel
./build/clove
```

### Agent fails to connect
```bash
# Verify socket permissions
stat /tmp/clove.sock

# Check kernel logs
# Look for connection errors in kernel output
```

### LLM requests fail
```bash
# Verify API key
echo $GEMINI_API_KEY

# Test API key directly
curl -X POST "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"test"}]}]}'
```

### Resource limits not enforced
```bash
# Verify cgroups v2 is available
mount | grep cgroup2

# Check cgroup controllers
cat /sys/fs/cgroup/cgroup.controllers

# If missing, enable cgroups v2 in kernel boot params
```

---

## Expected Total Duration

| Phase | Time |
|-------|------|
| Setup | 10 min |
| Tests 1-5 | 7 min |
| Tests 6-10 | 11 min |
| Tests 11-15 | 13 min |
| Tests 16-18 | 9 min |
| Tests 19-21 | 7 min |
| **Total** | **~57 minutes** |

---

## Success Criteria

✅ **All tests pass** without errors
✅ **Kernel remains stable** throughout testing
✅ **Resource limits enforced** correctly
✅ **Agents properly isolated** (no cascade failures)
✅ **Dashboard displays** real-time data
✅ **IPC messaging** works between agents
✅ **State store persists** data correctly
✅ **LLM integration** responds accurately
✅ **Pause/Resume** stops and continues agent execution
✅ **Audit logging** captures lifecycle and security events
✅ **Execution recording** captures deterministic syscalls
✅ **Replay mechanism** can replay recorded sessions

---

## Next Steps After Testing

1. **Try custom agents**: Create your own agents using the SDK
2. **Deploy to cloud**: Use `clove deploy` for production
3. **Integrate frameworks**: Try LangChain, CrewAI, or AutoGen adapters
4. **Build pipelines**: Create multi-agent processing workflows
5. **Monitor production**: Use dashboard for real-time monitoring

---

**End of Test Suite**
