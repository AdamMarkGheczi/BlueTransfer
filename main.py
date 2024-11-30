import customtkinter
from tkinter import filedialog
import connection
import queue
from misc import convert_file_size
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

# file = open(file_path, "rb")


info_queue = queue.Queue()

connection.initialise_receiver_sockets(info_queue)

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

        # Entry for IP Address
        self.ip_entry = customtkinter.CTkEntry(self.sending_frame, placeholder_text="Enter IP Address")
        self.ip_entry.grid(row=0, column=1, sticky="e", padx=10, pady=(10, 5))

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

        self.check_queue()

    def create_transfer_request_popup(self, info, socket):
        popup = customtkinter.CTkToplevel()
        popup.attributes('-topmost', True)
        popup.title("File Transfer Request")
        popup.geometry("450x150")
        popup.resizable(False, False)
        popup.after(10, lambda: (popup.focus_force()))
        print(info)
        message = f"{socket.getpeername()[0]} sent you a transfer request!\nFile: {info["file_name"]}\nSize: {convert_file_size(info["file_size"])}\nSHA-1: {info["sha1"]}"

        message_label = customtkinter.CTkLabel(
            popup, text=message, justify="left"
        )
        message_label.pack(pady=20)

        def on_accept():
            connection.processed_info_queue.put((connection.packet_type.TRANSFER_ACCEPT, socket))
            popup.destroy()

        accept_button = customtkinter.CTkButton(popup, text="Accept", command=on_accept)
        accept_button.pack(side="left", padx=20, pady=10)

        def on_reject():
            connection.processed_info_queue.put((connection.packet_type.TRANSFER_REJECT, socket))
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_reject)

        reject_button = customtkinter.CTkButton(popup, text="Reject", command=on_reject)
        reject_button.pack(side="right", padx=20, pady=10)

    def check_queue(self):
        while not info_queue.empty():
            (info, socket) = info_queue.get()
            if info["type"] == connection.packet_type.FILE_HEADER:
                self.create_transfer_request_popup(info, socket)

        self.root.after(100, self.check_queue)

    file_id = 0
    def create_file_sender_window(self):
        self.file_path = ""
        transfer_window = customtkinter.CTkToplevel(self.root)
        transfer_window.title("Initiate Transfer")
        transfer_window.geometry("400x320")
        
        transfer_window.after(10, lambda: (transfer_window.focus_force()))

        file_label = customtkinter.CTkLabel(transfer_window, text="Selected File: None", wraplength=380, anchor="w", justify="left")
        file_label.pack(pady=10, padx=10, fill="x")

        def browse_file():
            path = filedialog.askopenfilename()
            transfer_window.focus_force()
            if path:
                file_label.configure(text=f"Selected File: {path}")
                self.file_path = path


        browse_button = customtkinter.CTkButton(transfer_window, text="Browse File", command=browse_file)
        browse_button.pack(pady=10, padx=10)

        ip_label = customtkinter.CTkLabel(transfer_window, text="Enter Receiver's IP:")
        ip_label.pack(pady=10, padx=10)

        ip_entry = customtkinter.CTkEntry(transfer_window, placeholder_text="ipv4")
        ip_entry.pack(pady=10, padx=10)

        status_label = customtkinter.CTkLabel(transfer_window, text="Status: Waiting for input", anchor="w", wraplength=380)
        status_label.pack(pady=10, padx=10, fill="x")

        def transfer():
            if not self.file_path or not ip_entry.get():
                status_label.configure(text="Status: Please select a file and enter a valid IP address.")
            else:
                try:
                    status_label.configure(text=f"Status: Sending transfer request...")
                    connection.transfer_file(ip_entry.get(), self.file_path)
                except Exception as e:
                    status_label.configure(text=f"Status: Error - {str(e)}")
                    
        request_button = customtkinter.CTkButton(transfer_window, text="Transfer", command=transfer)
        request_button.pack(pady=10, padx=10)

    def update_file_status(self, file_id, new_status):
        if file_id in self.file_entries:
            file_entry = self.file_entries[file_id]
            file_entry["status"] = new_status
            file_entry["label"].configure(text=f"{file_entry['label'].cget('text')}\nStatus: {new_status}")

    def delete_file(self, file_id):
        if file_id in self.file_entries:
            file_entry = self.file_entries[file_id]
            file_entry["frame"].destroy()
            del self.file_entries[file_id]



root = customtkinter.CTk()
app = TransferApp(root)
root.mainloop()
