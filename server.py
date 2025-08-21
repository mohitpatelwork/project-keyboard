import asyncio
import websockets
import json
import random
import string

# --- Server State ---
# This dictionary will store the active sessions.
# Key: session_id (e.g., "123-456")
# Value: A dictionary {'host': host_websocket, 'client': client_websocket}
SESSIONS = {}

def generate_session_id():
    """Generates a unique 6-character session ID."""
    while True:
        session_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if session_id not in SESSIONS:
            return session_id

async def relay_messages(session_id, sender_ws, receiver_ws):
    """Relays messages from a sender websocket to a receiver websocket."""
    try:
        async for message in sender_ws:
            if receiver_ws and receiver_ws.open:
                await receiver_ws.send(message)
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for a participant in session {session_id}.")
    finally:
        # When one participant disconnects, we can notify the other.
        if receiver_ws and receiver_ws.open:
            await receiver_ws.send(json.dumps({'type': 'partner_disconnected'}))
        print(f"Relay stopped for session {session_id}.")


async def handler(websocket, path):
    """
    Handles incoming websocket connections and routes them based on the initial message.
    """
    print(f"New connection from {websocket.remote_address}")
    try:
        # The first message determines the role of the connection (host or client)
        initial_message = await websocket.recv()
        data = json.loads(initial_message)
        role = data.get('role')

        if role == 'host':
            session_id = generate_session_id()
            SESSIONS[session_id] = {'host': websocket, 'client': None}
            print(f"Host registered for new session: {session_id}")
            
            # Send the session ID back to the host
            await websocket.send(json.dumps({'type': 'session_created', 'session_id': session_id}))

            # Wait for the client to connect
            while SESSIONS[session_id]['client'] is None:
                await asyncio.sleep(1) # Check every second
            
            client_ws = SESSIONS[session_id]['client']
            print(f"Client connected to session {session_id}. Starting relay.")
            await websocket.send(json.dumps({'type': 'client_connected'}))

            # Start relaying messages from host to client
            await relay_messages(session_id, websocket, client_ws)

        elif role == 'client':
            session_id = data.get('session_id')
            if session_id in SESSIONS and SESSIONS[session_id]['client'] is None:
                SESSIONS[session_id]['client'] = websocket
                host_ws = SESSIONS[session_id]['host']
                print(f"Client joined session: {session_id}")
                
                # Notify the host that the client has connected
                await host_ws.send(json.dumps({'type': 'client_connected'}))
                
                # Start relaying messages from client to host
                await relay_messages(session_id, websocket, host_ws)
            else:
                error_msg = "Session not found or already full."
                await websocket.send(json.dumps({'type': 'error', 'message': error_msg}))
                print(f"Client failed to join session {session_id}: {error_msg}")
                await websocket.close()

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection from {websocket.remote_address} closed.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # --- Cleanup Logic ---
        # Find which session this websocket belonged to and remove it
        session_to_remove = None
        for session_id, participants in SESSIONS.items():
            if websocket == participants['host'] or websocket == participants['client']:
                session_to_remove = session_id
                # Notify the other participant if they are still connected
                other_ws = participants['client'] if websocket == participants['host'] else participants['host']
                if other_ws and other_ws.open:
                    await other_ws.send(json.dumps({'type': 'partner_disconnected'}))
                break
        
        if session_to_remove:
            del SESSIONS[session_to_remove]
            print(f"Cleaned up session: {session_to_remove}")


async def main():
    # Render provides the PORT environment variable.
    # We'll use 8080 as a default for local testing.
    port = 8080
    host = '0.0.0.0' # Listen on all available network interfaces
    
    print(f"Starting websocket server on {host}:{port}...")
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())

