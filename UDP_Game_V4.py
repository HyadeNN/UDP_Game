# game_client.py
import tkinter as tk
from tkinter import ttk, messagebox
import socket
import json
import threading
import time
from datetime import datetime
from typing import List, Dict, Set, Tuple, Optional


class Packet:
    def __init__(self, seq: int, ack: int, dl: int, packet_number: int = None, is_resend: bool = False):
        self.seq = seq
        self.ack = ack
        self.dl = dl
        self.packet_number = packet_number
        self.is_resend = is_resend
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "seq": self.seq,
            "ack": self.ack,
            "dl": self.dl,
            "packet_number": self.packet_number,
            "is_resend": self.is_resend
        }

    @staticmethod
    def from_dict(data: dict) -> 'Packet':
        return Packet(
            data["seq"],
            data["ack"],
            data["dl"],
            data.get("packet_number"),
            data.get("is_resend", False)
        )


class GameClient:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP Network Game")

        # Game state
        self.health = 5
        self.opponent_health = 5
        self.opponent_name = None
        self.can_send = True
        self.send_cooldown = 7
        self.receive_cooldown = 3
        self.last_send_time = None
        self.last_receive_time = None
        self.received_packets: List[Packet] = []
        self.sent_packets: List[Packet] = []
        self.ack_counts: Dict[Tuple[int, int], int] = {}
        self.last_data_length = None
        self.packet_counter = 0
        self.seen_packet_numbers: Set[int] = set()

        # Socket setup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening = False

        self.setup_ui()
        self.start_cooldown_thread()

    def setup_ui(self):
        # Connection Frame
        connection_frame = ttk.LabelFrame(self.root, text="Connection", padding="5")
        connection_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(connection_frame, text="Player Name:").grid(row=0, column=0, padx=5)
        self.player_name = ttk.Entry(connection_frame)
        self.player_name.grid(row=0, column=1, padx=5)
        self.player_name.insert(0, "Player -> ")

        ttk.Label(connection_frame, text="Source IP:").grid(row=1, column=0, padx=5)
        self.source_ip = ttk.Entry(connection_frame)
        self.source_ip.insert(0, "192.168.1.43")
        self.source_ip.grid(row=1, column=1, padx=5)

        ttk.Label(connection_frame, text="Source Port:").grid(row=1, column=2, padx=5)
        self.source_port = ttk.Entry(connection_frame, width=10)
        self.source_port.grid(row=1, column=3, padx=5)
        self.source_port.insert(0, "12345")

        ttk.Label(connection_frame, text="Destination IP:").grid(row=2, column=0, padx=5)
        self.dest_ip = ttk.Entry(connection_frame)
        self.dest_ip.insert(0, "192.168.1.43")
        self.dest_ip.grid(row=2, column=1, padx=5)

        ttk.Label(connection_frame, text="Destination Port:").grid(row=2, column=2, padx=5)
        self.dest_port = ttk.Entry(connection_frame, width=10)
        self.dest_port.grid(row=2, column=3, padx=5)
        self.dest_port.insert(0, "54321")

        self.start_button = ttk.Button(connection_frame, text="Start", command=self.start_game)
        self.start_button.grid(row=3, column=0, columnspan=4, pady=10)

        # Status Frame
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.player_health_label = ttk.Label(status_frame, text="Your HP: 5")
        self.player_health_label.grid(row=0, column=0, padx=20)

        self.opponent_health_label = ttk.Label(status_frame, text="Opponent HP: 5")
        self.opponent_health_label.grid(row=0, column=1, padx=20)

        self.cooldown_label = ttk.Label(status_frame, text="Ready to send")
        self.cooldown_label.grid(row=0, column=2, padx=20)

        # Message Frame
        message_frame = ttk.LabelFrame(self.root, text="Message", padding="5")
        message_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        ttk.Label(message_frame, text="SEQ:").grid(row=0, column=0, padx=5)
        self.seq_input = ttk.Entry(message_frame, width=10)
        self.seq_input.grid(row=0, column=1, padx=5)

        ttk.Label(message_frame, text="ACK:").grid(row=0, column=2, padx=5)
        self.ack_input = ttk.Entry(message_frame, width=10)
        self.ack_input.grid(row=0, column=3, padx=5)

        ttk.Label(message_frame, text="Data Length:").grid(row=0, column=4, padx=5)
        self.dl_input = ttk.Entry(message_frame, width=10)
        self.dl_input.grid(row=0, column=5, padx=5)

        self.send_button = ttk.Button(message_frame, text="Send", command=self.send_packet)
        self.send_button.grid(row=0, column=6, padx=10)

        # Main content frame
        content_frame = ttk.Frame(self.root)
        content_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5)

        # Left side - Packet tables
        tables_frame = ttk.Frame(content_frame)
        tables_frame.grid(row=0, column=0, padx=5)

        # Player names above tables
        self.sent_name_label = ttk.Label(tables_frame, text="Your Packets")
        self.sent_name_label.grid(row=0, column=0)

        self.received_name_label = ttk.Label(tables_frame, text="Opponent's Packets")
        self.received_name_label.grid(row=0, column=1)

        # Packet tables with reduced width
        sent_frame = ttk.Frame(tables_frame)
        sent_frame.grid(row=1, column=0, padx=2)

        self.sent_tree = ttk.Treeview(sent_frame, columns=("#", "SEQ", "ACK", "DL"),
                                      show="headings", height=10)
        for col in ("#", "SEQ", "ACK", "DL"):
            self.sent_tree.heading(col, text=col)
            self.sent_tree.column(col, width=40)
        self.sent_tree.grid(row=0, column=0)

        received_frame = ttk.Frame(tables_frame)
        received_frame.grid(row=1, column=1, padx=2)

        self.received_tree = ttk.Treeview(received_frame, columns=("#", "SEQ", "ACK", "DL"),
                                          show="headings", height=10)
        for col in ("#", "SEQ", "ACK", "DL"):
            self.received_tree.heading(col, text=col)
            self.received_tree.column(col, width=40)
        self.received_tree.grid(row=0, column=0)

        # Right side - Logs and Reasonable packets
        info_frame = ttk.Frame(content_frame)
        info_frame.grid(row=0, column=1, padx=5)

        # Game Logs
        log_label = ttk.Label(info_frame, text="Game Logs")
        log_label.grid(row=0, column=0)

        self.log_text = tk.Text(info_frame, height=10, width=50)
        self.log_text.grid(row=1, column=0, pady=5)

        # Reasonable Packets
        reasonable_label = ttk.Label(info_frame, text="Reasonable Next Packets")
        reasonable_label.grid(row=2, column=0, pady=(10, 0))

        self.reasonable_text = tk.Text(info_frame, height=10, width=50)
        self.reasonable_text.grid(row=3, column=0, pady=5)

    def log_event(self, message: str):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("1.0", f"[{timestamp}] {message}\n")

    def update_reasonable_packets(self):
        """Update the display of reasonable next packets"""
        self.reasonable_text.delete("1.0", tk.END)

        if not self.received_packets:
            self.reasonable_text.insert("1.0", "First packet - any packet is valid")
            return

        last_received = self.received_packets[-1]
        second_to_last = self.received_packets[-2] if len(self.received_packets) > 1 else None

        reasonable = ["Reasonable next packets:"]
        reasonable.append(f"\n1. Acknowledging last packet:")
        reasonable.append(f"   - ACK={last_received.seq + last_received.dl} (any SEQ)")

        if second_to_last:
            reasonable.append(f"\n2. Acknowledging only first packet:")
            reasonable.append(f"   - ACK={second_to_last.seq + second_to_last.dl} (any SEQ)")

        reasonable.append(f"\n3. No acknowledgment:")
        reasonable.append(f"   - ACK={last_received.seq} (any SEQ)")
        reasonable.append(f"   - ACK=1 (fresh start)")

        self.reasonable_text.insert("1.0", "\n".join(reasonable))

    def is_packet_reasonable(self, new_packet: Packet) -> bool:
        """Validates if a packet is reasonable based on game rules."""
        if not self.received_packets:
            return True

        last_received = self.received_packets[-1]
        second_to_last = self.received_packets[-2] if len(self.received_packets) > 1 else None

        # Check resend packet data length consistency
        if new_packet.is_resend and self.last_data_length is not None:
            if new_packet.dl != self.last_data_length:
                self.log_event(f"Invalid resend: DL changed from {self.last_data_length} to {new_packet.dl}")
                return False

        reasonable_acks = {
            last_received.seq + last_received.dl,  # Full acknowledgment
            last_received.seq,  # No acknowledgment
            1  # Fresh start
        }

        if second_to_last:
            reasonable_acks.add(second_to_last.seq + second_to_last.dl)

        if new_packet.ack not in reasonable_acks:
            self.log_event(f"Invalid ACK: {new_packet.ack} not in {reasonable_acks}")
            return False

        return True

    def handle_health_reduction(self, reason: str):
        """Reduces health and updates UI based on given reason."""
        self.health -= 1
        self.player_health_label.config(text=f"{self.player_name.get()}'s HP: {self.health}")

        messages = {
            "unreasonable": "Sent unreasonable packet",
            "resend_dl": "Changed data length in resend",
            "failed_resend": "Failed to resend requested packet"
        }

        message = messages.get(reason, "Health reduced")
        self.log_event(f"Lost 1 HP: {message}")
        messagebox.showwarning("Health Reduced", message)

        # Immediately send a health update packet
        self.send_health_update()

    def send_health_update(self):
        """Send a packet just to update health"""
        try:
            data = {
                "health_update": True,
                "player_name": self.player_name.get(),
                "health": self.health
            }

            dest_ip = self.dest_ip.get()
            dest_port = int(self.dest_port.get())
            self.socket.sendto(json.dumps(data).encode(), (dest_ip, dest_port))

        except Exception as e:
            print(f"Failed to send health update: {str(e)}")

    def get_next_packet_number(self) -> int:
        """Get the next packet number in the sequence."""
        max_seen = max(self.seen_packet_numbers) if self.seen_packet_numbers else 0
        return max_seen + 1

    def send_packet(self):
        if not self.can_send:
            messagebox.showwarning("Cooldown", "Please wait for the cooldown to finish")
            return

        try:
            packet = Packet(
                seq=int(self.seq_input.get()),
                ack=int(self.ack_input.get()),
                dl=int(self.dl_input.get()),
                packet_number=self.get_next_packet_number()
            )

            if not self.is_packet_reasonable(packet):
                self.handle_health_reduction("unreasonable")
                return

            self.send_packet_internal(packet)

        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for SEQ, ACK, and Data Length")

    def send_packet_internal(self, packet: Packet):
        try:
            dest_ip = self.dest_ip.get()
            dest_port = int(self.dest_port.get())

            data = {
                **packet.to_dict(),
                "player_name": self.player_name.get(),
                "health": self.health
            }

            self.socket.sendto(json.dumps(data).encode(), (dest_ip, dest_port))

            # Update packet tracking
            self.seen_packet_numbers.add(packet.packet_number)
            self.sent_packets.append(packet)

            # Update sent packets table
            self.sent_tree.insert("", 0, values=(packet.packet_number, packet.seq, packet.ack, packet.dl))

            # Log the sent packet
            self.log_event(f"Sent: ({packet.seq};{packet.ack};{packet.dl})")

            # Update last data length for resend validation
            if not packet.is_resend:
                self.last_data_length = packet.dl

            # Start cooldown
            self.can_send = False
            self.last_send_time = datetime.now()

            # Update reasonable packets display
            self.update_reasonable_packets()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to send packet: {str(e)}")

    def check_resend_needed(self, ack: int, seq: int):
        """Checks if packet resend is needed based on duplicate ACKs."""
        ack_key = (ack, seq)
        self.ack_counts[ack_key] = self.ack_counts.get(ack_key, 0) + 1

        if self.ack_counts[ack_key] >= 3:
            self.log_event(f"Triple duplicate ACK ({ack}) received")

            # Check if we've already sent a packet with higher sequence number
            has_newer_packet = any(p.seq > ack for p in self.sent_packets)

            # Find the packet that needs to be resent
            for packet in self.sent_packets:
                if packet.seq == ack:
                    if has_newer_packet:
                        self.log_event(f"No resend needed - already sent newer packets")
                        return

                    packet.is_resend = True
                    self.log_event(f"Resending packet (SEQ={ack})")
                    self.send_packet_internal(packet)
                    return

            self.handle_health_reduction("failed_resend")

    def listen_for_packets(self):
        """Listen for incoming packets in a separate thread."""
        while self.listening:
            try:
                data, addr = self.socket.recvfrom(1024)
                packet_data = json.loads(data.decode())

                # Handle health update packets
                if packet_data.get("health_update"):
                    self.opponent_health = packet_data["health"]
                    self.opponent_name = packet_data["player_name"]
                    self.opponent_health_label.config(text=f"{self.opponent_name}'s HP: {self.opponent_health}")
                    self.log_event(f"Received health update: {self.opponent_name} HP={self.opponent_health}")
                    continue

                packet = Packet.from_dict(packet_data)

                # Update packet tracking
                self.seen_packet_numbers.add(packet.packet_number)
                self.received_packets.append(packet)

                # Update received packets table
                self.received_tree.insert("", 0, values=(packet.packet_number, packet.seq, packet.ack, packet.dl))

                # Log packet receipt
                self.log_event(f"Received: ({packet.seq};{packet.ack};{packet.dl})")

                # Start receive cooldown
                self.last_receive_time = datetime.now()

                # Update opponent info
                self.opponent_health = packet_data["health"]
                self.opponent_name = packet_data["player_name"]
                self.opponent_health_label.config(text=f"{self.opponent_name}'s HP: {self.opponent_health}")

                # Check for resend needed
                self.check_resend_needed(packet.ack, packet.seq)

                # Update reasonable packets display
                self.update_reasonable_packets()

            except Exception as e:
                print(f"Error receiving packet: {str(e)}")

    def start_game(self):
        """Initialize the game and start listening for packets."""
        try:
            source_port = int(self.source_port.get())
            self.socket.bind((self.source_ip.get(), source_port))

            # Start listening thread
            self.listening = True
            self.listen_thread = threading.Thread(target=self.listen_for_packets)
            self.listen_thread.daemon = True
            self.listen_thread.start()

            # Update UI labels with player name
            player_name = self.player_name.get()
            self.sent_name_label.config(text=f"{player_name}'s Packets")
            self.player_health_label.config(text=f"{player_name}'s HP: {self.health}")

            # Disable connection inputs
            for widget in [self.start_button, self.source_ip, self.source_port,
                           self.dest_ip, self.dest_port, self.player_name]:
                widget.config(state="disabled")

            self.log_event("Game started")
            messagebox.showinfo("Game Started", "Successfully connected! Game is ready to play.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start game: {str(e)}")

    def start_cooldown_thread(self):
        """Manage send and receive cooldowns."""

        def update_cooldowns():
            while True:
                now = datetime.now()
                send_blocked = False
                status_text = "Ready to send"

                # Check send cooldown
                if self.last_send_time:
                    send_elapsed = (now - self.last_send_time).total_seconds()
                    if send_elapsed < self.send_cooldown:
                        send_blocked = True
                        remaining = self.send_cooldown - send_elapsed
                        status_text = f"Send cooldown: {remaining:.1f}s"

                # Check receive cooldown
                if self.last_receive_time:
                    receive_elapsed = (now - self.last_receive_time).total_seconds()
                    if receive_elapsed < self.receive_cooldown:
                        send_blocked = True
                        remaining = self.receive_cooldown - receive_elapsed
                        status_text = f"Receive cooldown: {remaining:.1f}s"

                # Update UI and state
                self.can_send = not send_blocked
                self.cooldown_label.config(text=status_text)
                time.sleep(0.1)

        cooldown_thread = threading.Thread(target=update_cooldowns)
        cooldown_thread.daemon = True
        cooldown_thread.start()


if __name__ == "__main__":
    root = tk.Tk()
    client = GameClient(root)
    root.mainloop()


def send_packet_internal(self, packet: Packet):
    try:
        dest_ip = self.dest_ip.get()
        dest_port = int(self.dest_port.get())

        data = {
            **packet.to_dict(),
            "player_name": self.player_name.get(),
            "health": self.health
        }

        self.socket.sendto(json.dumps(data).encode(), (dest_ip, dest_port))

        # Update packet tracking
        self.seen_packet_numbers.add(packet.packet_number)
        self.sent_packets.append(packet)
        self.sent_tree.insert("", 0, values=(packet.packet_number, packet.seq, packet.ack, packet.dl))

        # Log the sent packet
        self.log_event(f"Sent: ({packet.seq};{packet.ack};{packet.dl})")

        # Update last data length for resend validation
        if not packet.is_resend:
            self.last_data_length = packet.dl

        # Start cooldown
        self.can_send = False
        self.last_send_time = datetime.now()

        # Update reasonable packets display
        self.update_reasonable_packets()

    except Exception as e:
        messagebox.showerror("Error", f"Failed to send packet: {str(e)}")