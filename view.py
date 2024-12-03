import customtkinter
from tkinter import filedialog
from misc import convert_file_size

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

class TransferApp:
    def __init__(self, title, presenter):
        self.presenter = presenter
        self.root = customtkinter.CTk()
        self.root.geometry("850x500")
        # self.root.title("BlueTransfer")
        self.root.title(title)

        self.transfer_frames = {}
        # Main Tab
        self.tabview = customtkinter.CTkTabview(self.root, corner_radius=0)
        self.tabview.grid(row=0, column=0, sticky="nsew")
        self.tabview.add("Transfers")
        self.tabview.add("Contacts")
        self.tabview._segmented_button.grid(sticky="nw", padx=10, pady=10)

        # Configure main grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Transfers tab
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

        self.add_send_button = customtkinter.CTkButton(self.sending_frame, text="Send new file...", command=self.__create_file_sender_window)
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

    def create_generic_popup(self, message, title="Notification"):
        popup = customtkinter.CTkToplevel()
        popup.title(title)

        popup.geometry("450x150")
        popup.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")

        popup.after(10, lambda: (popup.focus_force()))

        message_label = customtkinter.CTkLabel(popup, text=message, justify="left")
        message_label.pack(pady=20)

    def create_transfer_request_popup(self, info):
        '''info dictionary: transfer_uuid, ip, file_name, file_size, hash'''
        popup = customtkinter.CTkToplevel()
        popup.title("File Transfer Request")
        popup.geometry("400x320")
        popup.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")
        popup.resizable(False, False)
        popup.after(100, lambda: (popup.focus_force()))

        transfer_uuid = info["transfer_uuid"]
        ip = info["ip"]
        file_name = info["file_name"]
        file_size = convert_file_size(info["file_size"])
        hash = info["hash"]

        message = f"{ip} sent you a transfer request!\nFile: {file_name}\nSize: {file_size}\nSHA-1: {hash}"

        message_label = customtkinter.CTkLabel(popup, text=message, justify="left")
        message_label.pack(pady=20)

        def on_accept():
            path = filedialog.askdirectory()
            if path:
                self.presenter.accept_inbound_transfer(transfer_uuid, path)
                popup.destroy()

        def on_reject():
            self.presenter.reject_inbound_transfer(transfer_uuid)
            popup.destroy()

        accept_button = customtkinter.CTkButton(popup, text="Accept", command=on_accept)
        accept_button.pack(side="left", padx=20, pady=10)

        reject_button = customtkinter.CTkButton(popup, text="Reject", command=on_reject)
        reject_button.pack(side="right", padx=20, pady=10)

        popup.protocol("WM_DELETE_WINDOW", on_reject)

    def __create_file_sender_window(self):
        file_sender_window = customtkinter.CTkToplevel(self.root)
        file_sender_window.title("Initiate Transfer")
        file_sender_window.geometry("400x320")
        file_sender_window.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")

        file_sender_window.after(10, lambda: (file_sender_window.focus_force()))

        file_label = customtkinter.CTkLabel(file_sender_window, text="No selected file", wraplength=380, anchor="n", justify="center")
        file_label.pack(pady=10, padx=10, fill="x")

        self.file_path = None

        def browse_file():
            path = filedialog.askopenfilename()
            file_sender_window.focus_force()
            if path:
                file_label.configure(text=f"{path}")
                self.file_path = path

        browse_button = customtkinter.CTkButton(file_sender_window, text="Browse File", command=browse_file)
        browse_button.pack(pady=10, padx=10)

        ip_label = customtkinter.CTkLabel(file_sender_window, text="Enter Receiver's IP:")
        ip_label.pack(pady=10, padx=10)

        ip_entry = customtkinter.CTkEntry(file_sender_window, placeholder_text="ipv4")
        ip_entry.pack(pady=10, padx=10)

        def send_transfer_request():
            destination_ip = ip_entry.get()
            if not self.file_path or not destination_ip:
                self.create_generic_popup("Please select a file and enter a valid IP address!")
                return
            
            self.presenter.send_transfer_request(destination_ip, self.file_path)
                    
        request_button = customtkinter.CTkButton(file_sender_window, text="Transfer", command=send_transfer_request)
        request_button.pack(pady=10, padx=10)

    def sync_transferring_frame_to_ui(self, info):
        '''info dictionary: transfer_uuid, ip, hash, file_name, file_size, transfer_speed, transferred, is_outbound, status'''

        transfer_uuid = info["transfer_uuid"]
        ip = info["ip"]
        hash = info["hash"]
        file_name = info["file_name"]
        file_size = info["file_size"]
        transfer_speed = info["transfer_speed"]
        transferred = info["transferred"]
        is_outbound = info["is_outbound"]
        status = info["status"]

        if not self.transfer_frames[transfer_uuid].get():
            if is_outbound:
                frame = customtkinter.CTkFrame(self.sending_list)
            else:
                frame = customtkinter.CTkFrame(self.receiving_list)

            self.transfer_frames[transfer_uuid] = frame
            frame.pack(fill="x", padx=5, pady=5)

            info_text = f"{file_name}\nFrom: {ip}\n{convert_file_size(transferred)}/{convert_file_size(file_size)}\nSpeed: {convert_file_size(transfer_speed)}/s\nSha-1: {hash}\nStatus: {status}"

            info_label = customtkinter.CTkLabel(frame, text=info_text)
            info_label.pack(side="left", fill="x", expand=True, padx=5)

            pause_button = customtkinter.CTkButton(frame, text="Pause", width=50, command=self.presenter.toggle_pause_transfer(info))
            pause_button.pack(side="right", padx=5)

            cancel_button = customtkinter.CTkButton(frame, text="Cancel", width=50, command=self.presenter.cancel_transfer(info))
            cancel_button.pack(side="right", padx=5)
        else:
            info_text = f"{file_name}\nFrom: {ip}\n{convert_file_size(transferred)}/{convert_file_size(file_size)}\nSpeed: {convert_file_size(transfer_speed)}/s\nSha-1: {hash}\nStatus: {status}"
            
            frame = self.transfer_frames[transfer_uuid]
            info_label = frame.children["info_label"]
            info_label.configure(text=info_text)

    def delete_transferring_frame_ui(self, transfer_uuid):
        self.transfer_frames[transfer_uuid].destroy()
        del self.transfer_frames[transfer_uuid]

    def launch(self):
        self.root.mainloop()