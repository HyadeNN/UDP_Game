# UDP Network Game Documentation

## Imports
```python
import tkinter as tk
from tkinter import ttk, messagebox  # For GUI components
import socket     # For UDP networking
import json      # For packet serialization
import threading # For concurrent operations
import time      # For cooldown timing
from datetime import datetime  # For timestamps
from typing import List, Dict, Set, Tuple, Optional  # Type hints
```

## Classes

### Packet Class
Represents a network packet in the game.

```python
class Packet:
    def __init__(self, seq: int, ack: int, dl: int, packet_number: int = None, is_resend: bool = False):
```
- **Parameters**:
  - `seq`: Sequence number of the packet
  - `ack`: Acknowledgment number
  - `dl`: Data length
  - `packet_number`: Global packet sequence number
  - `is_resend`: Flag indicating if this is a resent packet

#### Methods:
- `to_dict()`: Converts packet to dictionary for transmission
- `from_dict()`: Creates packet from received dictionary data

### GameClient Class
Main game client handling UI, networking, and game logic.

```python
class GameClient:
    def __init__(self, root):
```
State variables:
- Health tracking (player and opponent)
- Cooldown timers (send/receive)
- Packet history
- Network socket
- UI elements

## Methods Documentation

### UI Setup Methods

#### `setup_ui(self)`
Creates all GUI elements:
- Connection panel (player name, IP, ports)
- Status panel (health, cooldown)
- Message input panel
- Packet history tables
- Logs and reasonable packets display

### Game Logic Methods

#### `is_packet_reasonable(self, new_packet: Packet) -> bool`
Validates if a packet follows game rules:
- Checks ACK numbers against previous packets
- Validates data length for resends
- Returns True if packet is valid

#### `handle_health_reduction(self, reason: str)`
Reduces player health and notifies:
- Reduces HP by 1
- Shows warning message
- Logs the event
- Sends health update to opponent

#### `send_health_update(self)`
Sends immediate health update packet:
- Contains only health and player info
- No game data

### Networking Methods

#### `send_packet(self)`
Handles user packet sending:
- Validates input values
- Creates new packet
- Checks if packet is reasonable
- Initiates sending

#### `send_packet_internal(self, packet: Packet)`
Internal packet sending logic:
- Serializes packet data
- Sends via UDP
- Updates UI and game state
- Starts cooldown timer

#### `listen_for_packets(self)`
Background thread for receiving packets:
- Handles regular packets and health updates
- Updates game state and UI
- Checks for resend needs
- Updates reasonable packets display

#### `check_resend_needed(self, ack: int, seq: int)`
Handles packet resend logic:
- Tracks duplicate ACKs
- Triggers resend after 3 duplicates
- Handles health reduction for failed resends

### Utility Methods

#### `log_event(self, message: str)`
Adds timestamped message to game log

#### `update_reasonable_packets(self)`
Updates display of valid next packets:
- Shows possible ACK values
- Explains packet rules
- Updates after each packet

#### `get_next_packet_number(self) -> int`
Generates sequential packet numbers:
- Synchronized between clients
- Based on highest seen number

### Game Control Methods

#### `start_game(self)`
Initializes game:
- Binds UDP socket
- Starts listener thread
- Updates UI state
- Disables connection inputs

#### `start_cooldown_thread(self)`
Manages cooldown timers:
- 7-second send cooldown
- 3-second receive cooldown
- Updates UI with remaining time

## Game Rules and Features

1. **Health System**
   - Players start with 5 HP
   - HP lost for:
     - Unreasonable packets
     - Invalid resend data length
     - Failed resend requests

2. **Packet Validation**
   - SEQ numbers: Can be any value
   - ACK numbers: Must acknowledge previous packets
   - Data Length: Must remain consistent for resends

3. **Resend Mechanism**
   - Triggered by 3 duplicate ACKs
   - Must maintain same data length
   - No penalty if newer packets sent

4. **Cooldown System**
   - Send cooldown: 7 seconds
   - Receive cooldown: 3 seconds
   - Visual countdown in UI

5. **UI Features**
   - Real-time packet history
   - Game event logs
   - Reasonable packet suggestions
   - Health and cooldown status
   - Global packet sequence numbers

## Usage Instructions

1. Start the game on two computers
2. Enter connection details:
   - Player names
   - IP addresses
   - Port numbers
3. Click Start to begin
4. Send packets following game rules
5. Monitor logs and reasonable packets
6. Maintain health by following protocol

The game ends when a player reaches 0 HP or disconnects.
