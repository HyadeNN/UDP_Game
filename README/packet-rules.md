# Packet Reasonability Rules in UDP Game

## Packet Structure
A packet consists of three numbers: `(SEQ;ACK;DL)`
- SEQ: Sequence number
- ACK: Acknowledgment number
- DL: Data length

## Basic Rules

### 1. First Packet
- Any packet is valid as the first packet in the conversation
- Example: (1;1;10) is a valid first packet

### 2. Resend Packets
When a packet is resent:
- Must maintain the same data length as the original packet
- If DL is changed in a resend, sender loses 1 HP
- Example: If original was (1;1;10), resend must be (1;1;10), not (1;1;20)

### 3. ACK Numbers
After receiving a packet, there are several reasonable options for ACK numbers:

#### A. Acknowledging Latest Packet
- ACK = Previous_SEQ + Previous_DL
- Example:
  ```
  Received: (1;1;10)
  Valid response acknowledging receipt: ACK = 1 + 10 = 11
  ```

#### B. Acknowledging Earlier Packet
- ACK = Earlier_SEQ + Earlier_DL
- Used when acknowledging only previous packets
- Example:
  ```
  P1 sends: (1;1;10)
  P2 sends: (1;1;20)
  P1 sends: (11;21;10)  # ACK=21 acknowledges P2's packet (1+20=21)
  ```

#### C. No Acknowledgment
- Keep previous ACK number
- Acts like packets weren't received
- Example:
  ```
  P1 sends: (1;1;10)
  P2 sends: (1;1;20)
  P1 can send: (11;1;10)  # Keeping ACK=1, acting like no receipt
  ```

## Example Scenarios

### Scenario 1: Basic Communication
```
P1 sends: (1;1;10)
P2's reasonable options:
1. (1;11;20)  # Acknowledging P1's packet (ACK = 1+10)
2. (1;1;20)   # No acknowledgment
```

### Scenario 2: Multiple Packets
```
P1 sends: (1;1;10)
P2 sends: (1;1;20)
P1's reasonable options:
1. (11;21;10)  # Acknowledging P2's packet (ACK = 1+20)
2. (11;11;10)  # Only acknowledging first packet
3. (11;1;10)   # No acknowledgment
```

### Scenario 3: Triple Duplicate ACKs
```
If receiver sees same ACK three times:
- Sender must resend the requested packet
- Example:
  P1: (1;1;10)
  P2: (1;1;20)
  P2: (1;1;20)
  P2: (1;1;20)
  P1 must resend the packet or lose 1 HP
```

## Important Notes

1. **Sequence Numbers (SEQ)**:
   - Can be any number
   - No strict rules for SEQ values
   - Often incremented but not required

2. **Data Length (DL)**:
   - Can be any number for new packets
   - Must match original in resends
   - Common practice: maintain consistent DL per player

3. **Health Reduction Cases**:
   - Sending unreasonable packets (invalid ACK)
   - Changing DL in resend packets
   - Failing to resend when triple duplicate ACKs received

4. **Common Strategy**:
   - Keep track of received packets
   - Calculate valid ACK numbers based on SEQ+DL
   - Maintain consistent DL for your packets
   - Monitor duplicate ACKs for resend requests
