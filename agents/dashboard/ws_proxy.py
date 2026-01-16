#!/usr/bin/env python3
"""
WebSocket Proxy for AgentOS Dashboard

Bridges browser WebSocket clients to the AgentOS kernel Unix socket.
Provides real-time agent monitoring capabilities.
"""

import asyncio
import json
import sys
import os
from pathlib import Path
import argparse

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python_sdk'))

try:
    from agentos import AgentOSClient, SyscallOp
    import websockets
except ImportError as e:
    print(f"Error: Missing dependency - {e}")
    print("Install websockets: pip install websockets")
    sys.exit(1)


class DashboardProxy:
    def __init__(self, kernel_socket='/tmp/agentos.sock', ws_port=8765):
        self.kernel_socket = kernel_socket
        self.ws_port = ws_port
        self.clients = set()
        self.running = True

    async def handle_client(self, websocket, path):
        """Handle new WebSocket connection from browser"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        print(f"✓ Client connected from {client_addr}. Total clients: {len(self.clients)}")

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"✗ Client {client_addr} disconnected")
        except Exception as e:
            print(f"✗ Error handling client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            print(f"  Remaining clients: {len(self.clients)}")

    async def handle_message(self, websocket, message):
        """Translate WebSocket JSON to AgentOS syscall"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            # Connect to kernel
            with AgentOSClient(self.kernel_socket) as client:
                if msg_type == 'list_agents':
                    agents = client.list_agents()
                    response = {'type': 'agent_list', 'data': agents}
                    await websocket.send(json.dumps(response))

                elif msg_type == 'spawn_agent':
                    payload = data.get('payload', {})
                    result = client.spawn(**payload)
                    response = {'type': 'spawn_result', 'data': result}
                    await websocket.send(json.dumps(response))
                    # Broadcast update to all clients
                    await self.broadcast_agent_update()

                elif msg_type == 'kill_agent':
                    name = data.get('name')
                    result = client.kill(name=name)
                    response = {'type': 'kill_result', 'success': result}
                    await websocket.send(json.dumps(response))
                    # Broadcast update to all clients
                    await self.broadcast_agent_update()

                elif msg_type == 'echo':
                    # Test message
                    echo_result = client.echo(data.get('message', 'ping'))
                    response = {'type': 'echo_result', 'data': echo_result}
                    await websocket.send(json.dumps(response))

        except json.JSONDecodeError as e:
            error_response = {'type': 'error', 'message': f'Invalid JSON: {e}'}
            await websocket.send(json.dumps(error_response))
        except ConnectionError as e:
            error_response = {'type': 'error', 'message': f'Kernel connection failed: {e}'}
            await websocket.send(json.dumps(error_response))
        except Exception as e:
            error_response = {'type': 'error', 'message': str(e)}
            await websocket.send(json.dumps(error_response))
            print(f"✗ Error handling message: {e}")

    async def broadcast_metrics(self):
        """Poll kernel and broadcast metrics to all clients"""
        print("✓ Starting metrics broadcaster (1s interval)")

        while self.running:
            await asyncio.sleep(1)  # Update every second

            if not self.clients:
                continue

            try:
                # Get agent list from kernel
                with AgentOSClient(self.kernel_socket) as client:
                    agents = client.list_agents()

                # Get current timestamp
                timestamp = int(asyncio.get_event_loop().time() * 1000)

                # Broadcast to all connected clients
                message = json.dumps({
                    'type': 'metrics_update',
                    'timestamp': timestamp,
                    'agents': agents
                })

                # Send to all clients
                websockets.broadcast(self.clients, message)

            except ConnectionError:
                # Kernel not available, skip this iteration
                pass
            except Exception as e:
                print(f"✗ Error broadcasting metrics: {e}")

    async def broadcast_agent_update(self):
        """Send immediate update when agents change"""
        if not self.clients:
            return

        try:
            with AgentOSClient(self.kernel_socket) as client:
                agents = client.list_agents()

            timestamp = int(asyncio.get_event_loop().time() * 1000)

            message = json.dumps({
                'type': 'agent_update',
                'timestamp': timestamp,
                'agents': agents
            })

            websockets.broadcast(self.clients, message)
        except Exception as e:
            print(f"✗ Error broadcasting agent update: {e}")

    async def start(self):
        """Start WebSocket server and metrics broadcaster"""
        print("=" * 60)
        print("AgentOS Dashboard WebSocket Proxy")
        print("=" * 60)
        print(f"Kernel socket: {self.kernel_socket}")
        print(f"WebSocket port: {self.ws_port}")
        print()

        # Test kernel connection
        try:
            with AgentOSClient(self.kernel_socket) as client:
                result = client.echo("test")
                if result:
                    print("✓ Kernel connection verified")
                else:
                    print("✗ Warning: Kernel echo failed")
        except Exception as e:
            print(f"✗ Warning: Cannot connect to kernel: {e}")
            print("  The proxy will start anyway. Make sure the kernel is running.")

        print()
        print(f"✓ WebSocket server listening on ws://localhost:{self.ws_port}")
        print(f"✓ Open dashboard: http://localhost:8000")
        print(f"  (Run in another terminal: cd agents/dashboard && python3 -m http.server 8000)")
        print()

        async with websockets.serve(self.handle_client, 'localhost', self.ws_port):
            # Start metrics broadcasting task
            await self.broadcast_metrics()


async def main():
    parser = argparse.ArgumentParser(description='AgentOS Dashboard WebSocket Proxy')
    parser.add_argument('--socket', default='/tmp/agentos.sock',
                        help='Path to AgentOS kernel socket (default: /tmp/agentos.sock)')
    parser.add_argument('--port', type=int, default=8765,
                        help='WebSocket port to listen on (default: 8765)')

    args = parser.parse_args()

    proxy = DashboardProxy(kernel_socket=args.socket, ws_port=args.port)

    try:
        await proxy.start()
    except KeyboardInterrupt:
        print("\n\n✓ Shutting down gracefully...")
        proxy.running = False


if __name__ == '__main__':
    asyncio.run(main())
