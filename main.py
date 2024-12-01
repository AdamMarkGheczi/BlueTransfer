import customtkinter
from tkinter import filedialog
import connection
import queue
from misc import convert_file_size
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

# file = open(file_path, "rb")


ui_queue = queue.Queue()

sending_ui_labels = {}
receiving_ui_labels = {}

connection.initialise_receiver_sockets(ui_queue)

class TransferApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("850x500")
        self.root.title("BlueTransfer")

        # Track file entries in a dictionary
        self.file_entries = {}

        # Main Tab View
        self.tabview = customtkinter.CTkTabview(root, corner_radius=0)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview.add("Transfers")
        self.tabview.add("Contacts")
        self.tabview._segmented_button.grid(sticky="nw", padx=10, pady=10)

        # Configure main grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Transfers Tab Layout
        self.transfers_tab = self.tabview.tab("Transfers")
        self.transfers_tab.grid_rowconfigure(0, weight=1)
        self.transfers_tab.grid_columnconfigure(0, weight=1)
        self.transfers_tab.grid_columnconfigure(1, weight=1)

        # Sending Section
        self.sending_frame = customtkinter.CTkFrame(self.transfers_tab)
        self.sending_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.sending_frame.grid_rowconfigure(1, weight=1)
        self.sending_frame.grid_columnconfigure(0, weight=1)

        sending_label = customtkinter.CTkLabel(self.sending_frame, text="SENDING", font=("Arial", 18, "bold"))
        sending_label.grid(row=0, column=0, sticky="w", pady=(10, 5), padx=(10, 0))

        self.add_send_button = customtkinter.CTkButton(
            self.sending_frame, text="Send new file...", command=self.create_file_sender_window
        )
        self.add_send_button.grid(row=0, column=2, sticky="e", padx=10, pady=(10, 5))

        self.sending_list = customtkinter.CTkScrollableFrame(self.sending_frame, width=350)
        self.sending_list.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=10, padx=10)

        # Receiving Section
        self.receiving_frame = customtkinter.CTkFrame(self.transfers_tab)
        self.receiving_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.receiving_frame.grid_rowconfigure(1, weight=1)
        self.receiving_frame.grid_columnconfigure(0, weight=1)

        receiving_label = customtkinter.CTkLabel(self.receiving_frame, text="RECEIVING", font=("Arial", 18, "bold"))
        receiving_label.grid(row=0, column=0, sticky="w", pady=(10, 5), padx=(10, 0))

        self.receiving_list = customtkinter.CTkScrollableFrame(self.receiving_frame, width=350)
        self.receiving_list.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)

        self.check_queue_and_update_transfers()

    def create_transfer_request_popup(self, info, socket):
        popup = customtkinter.CTkToplevel()
        popup.title("File Transfer Request")
        popup.geometry("450x150")
        popup.resizable(False, False)
        popup.after(100, lambda: (popup.focus_force()))
        
        ip = socket.getpeername()[0]
        file_name = info["file_name"]
        file_size = convert_file_size(info["file_size"])
        hash = info["sha1"]
        message = f"{ip} sent you a transfer request!\nFile: {file_name}\nSize: {file_size}\nSHA-1: {hash}"

        message_label = customtkinter.CTkLabel(
            popup, text=message, justify="left"
        )
        message_label.pack(pady=20)

        def on_accept():
            path = filedialog.askdirectory()
            if path:
                connection.add_to_active_inbound_transfers(socket.getpeername()[0], info["file_name"], info["file_size"], info["sha1"], f"{path}/{info["file_name"]}")
                connection.send_response(connection.packet_type.TRANSFER_ACCEPT, socket)
                socket.close()
                self.add_transfering_file(ip, hash, receiving=True)
                popup.destroy()

        accept_button = customtkinter.CTkButton(popup, text="Accept", command=on_accept)
        accept_button.pack(side="left", padx=20, pady=10)

        def on_reject():
            connection.send_response(connection.packet_type.TRANSFER_REJECT, socket)
            socket.close()
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_reject)

        reject_button = customtkinter.CTkButton(popup, text="Reject", command=on_reject)
        reject_button.pack(side="right", padx=20, pady=10)

    def transfer_request_rejected_notification(self, info):
        popup = customtkinter.CTkToplevel()
        popup.title("File Transfer Request Rejected")
        popup.geometry("450x150")
        popup.resizable(False, False)
        popup.after(10, lambda: (popup.focus_force()))
        
        message = f"{info["ip"]} rejected your transfer request!"

        message_label = customtkinter.CTkLabel(popup, text=message, justify="left")
        message_label.pack(pady=20)


    file_id = 0
    def create_file_sender_window(self):
        self.file_path = ""
        transfer_window = customtkinter.CTkToplevel(self.root)
        transfer_window.title("Initiate Transfer")
        transfer_window.geometry("400x320")
        main_x = self.root.winfo_rootx()
        main_y = self.root.winfo_rooty()
        transfer_window.geometry(f"+{main_x + 100}+{main_y-10}")

        transfer_window.after(10, lambda: (transfer_window.focus_force()))

        file_label = customtkinter.CTkLabel(transfer_window, text="Selected File: None", wraplength=380, anchor="n", justify="center")
        file_label.pack(pady=10, padx=10, fill="x")

        def browse_file():
            path = filedialog.askopenfilename()
            transfer_window.focus_force()
            if path:
                file_label.configure(text=f"{path}")
                self.file_path = path


        browse_button = customtkinter.CTkButton(transfer_window, text="Browse File", command=browse_file)
        browse_button.pack(pady=10, padx=10)

        ip_label = customtkinter.CTkLabel(transfer_window, text="Enter Receiver's IP:")
        ip_label.pack(pady=10, padx=10)

        ip_entry = customtkinter.CTkEntry(transfer_window, placeholder_text="ipv4")
        ip_entry.pack(pady=10, padx=10)

        status_label = customtkinter.CTkLabel(transfer_window, text="Status: Waiting for input", anchor="n", wraplength=380)
        status_label.pack(pady=10, padx=10, fill="x")

        def transfer():
            if not self.file_path or not ip_entry.get():
                status_label.configure(text="Status: Please select a file and enter a valid IP address.")
            else:
                try:
                    status_label.configure(text="Status: Transfer request sent...")
                    connection.initiate_transfer(ip_entry.get(), self.file_path, ui_queue)
                except Exception as e:
                    status_label.configure(text=f"Status: Error - {str(e)}")
                    
        request_button = customtkinter.CTkButton(transfer_window, text="Transfer", command=transfer)
        request_button.pack(pady=10, padx=10)

    def add_transfering_file(self, ip, reference_hash, receiving):
        if receiving:
            frame = customtkinter.CTkFrame(self.receiving_list)
        else:
            frame = customtkinter.CTkFrame(self.sending_list)

        frame.pack(fill="x", padx=5, pady=5)

        file_label = customtkinter.CTkLabel(frame, text="FileName1\nSha-256: 12345...\n500MB/1.17GB 30MB/s", anchor="w", justify="left")
        file_label.pack(side="left", fill="x", expand=True, padx=5)

        stop_button = customtkinter.CTkButton(frame, text="Pause", width=50, command=lambda: self.pause_transfer(ip, reference_hash, stop_button, from_sending_peer=True))
        stop_button.pack(side="right", padx=5)

        delete_button = customtkinter.CTkButton(frame, text="Cancel", width=50)
        delete_button.pack(side="right", padx=5)

        if receiving:
            receiving_ui_labels[(ip, reference_hash)] = file_label
        else:
            sending_ui_labels[(ip, reference_hash)] = file_label

    def update_file_statuses_ui(self):
        for (ip, reference_hash), label in sending_ui_labels.items():
            file_name = connection.active_outbound_transfers[ip][reference_hash]["file_name"]
            file_size = connection.active_outbound_transfers[ip][reference_hash]["file_size"]
            file_hash = reference_hash

            info_text=f"{file_name}\nSha-1: {file_hash}\n -MB/{convert_file_size(file_size)} -MB/s"

            label.configure(text=info_text)

        for (ip, reference_hash), label in receiving_ui_labels.items():
            file_name = connection.active_inbound_transfers[ip][reference_hash]["file_name"]
            file_size = connection.active_inbound_transfers[ip][reference_hash]["file_size"]
            file_hash = reference_hash

            info_text=f"{file_name}\nSha-1: {file_hash}\n -MB/{convert_file_size(file_size)} -MB/s"

            label.configure(text=info_text)

    def pause_transfer(ip, reference_hash, stop_button, from_sending_peer):
        connection.toggle_transfer_pause(ip, reference_hash, from_sending_peer=from_sending_peer)
        if stop_button["text"] == "Pause":
            stop_button.configure(text="Resume")
        else:
            stop_button.configure(text="Pause")

    def delete_file(self, file_id):
        if file_id in self.file_entries:
            file_entry = self.file_entries[file_id]
            file_entry["frame"].destroy()
            del self.file_entries[file_id]

    def check_queue_and_update_transfers(self):
        while not ui_queue.empty():
            (info, socket) = ui_queue.get()
            if info["type"] == connection.packet_type.FILE_HEADER:
                self.create_transfer_request_popup(info, socket)
            if info["type"] == connection.packet_type.TRANSFER_REJECT:
                self.transfer_request_rejected_notification(info)
            if info["type"] == connection.packet_type.TRANSFER_ACCEPT:
                self.add_transfering_file(info["ip"], info["reference_hash"], receiving=False)
            if info["type"] == connection.packet_type.TRANSFER_FINISHED or info["type"] == connection.packet_type.TRANSFER_CANCELLED:
                ip = info["ip"]
                reference_hash = info["reference_hash"]
                if info["receiving"]:
                    del receiving_ui_labels[(ip,reference_hash)]
                else:
                    del sending_ui_labels[(ip,reference_hash)]

        self.update_file_statuses_ui()

        self.root.after(100, self.check_queue_and_update_transfers)

root = customtkinter.CTk()
app = TransferApp(root)
root.mainloop()
