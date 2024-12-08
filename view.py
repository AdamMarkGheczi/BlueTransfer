import customtkinter
from tkinter import filedialog
from misc import convert_file_size

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

class TransferApp:
    def __init__(self, title, presenter):
        self.presenter = presenter
        self.root = customtkinter.CTk()
        self.root.geometry("900x500")
        # self.root.title("BlueTransfer")
        self.root.title(title)

        self.transfer_frames = {}
        self.sending_windows_status_labels = []

        # Configure main grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.main_frame = customtkinter.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        # Sending Section
        self.sending_frame = customtkinter.CTkFrame(self.main_frame)
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
        self.receiving_frame = customtkinter.CTkFrame(self.main_frame)
        self.receiving_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.receiving_frame.grid_rowconfigure(1, weight=1)
        self.receiving_frame.grid_columnconfigure(0, weight=1)

        receiving_label = customtkinter.CTkLabel(self.receiving_frame, text="RECEIVING", font=("Arial", 18, "bold"))
        receiving_label.grid(row=0, column=0, sticky="w", pady=(10, 5), padx=(10, 0))

        self.receiving_list = customtkinter.CTkScrollableFrame(self.receiving_frame, width=350)
        self.receiving_list.grid(row=1, column=0, sticky="nsew", pady=10, padx=10)

        def on_closing():
            active_transfers = self.presenter.check_for_active_transfers()
            if active_transfers:
                response = self.__show_yes_no_messagebox()
                if response:
                    self.root.destroy()
            else:
                self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)

    def create_generic_popup(self, message, title="Notification"):
        popup = customtkinter.CTkToplevel()
        popup.title(title)

        popup.geometry("450x150")
        popup.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")

        popup.after(10, lambda: (popup.focus_force()))

        message_label = customtkinter.CTkLabel(popup, text=message, wraplength=380, anchor="w", justify="left")
        message_label.pack(pady=20)

    def __show_yes_no_messagebox(self):
        """Displays a Yes/No messagebox and returns the user's choice."""
        messagebox = customtkinter.CTkToplevel()
        messagebox.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")

        response = {"value": False}

        def on_yes():
            response["value"] = True
            messagebox.destroy()

        def on_no():
            response["value"] = False
            messagebox.destroy()

        messagebox.title("Active Transfers!")
        messagebox.geometry("450x150")

        label = customtkinter.CTkLabel(
            messagebox,
            text="You have active transfers. Do you still want to exit?",
            wraplength=380,
            anchor="w",
            justify="left",
        )
        label.pack(pady=20)

        button_frame = customtkinter.CTkFrame(messagebox)
        button_frame.pack(pady=10)

        yes_button = customtkinter.CTkButton(button_frame, text="Yes", command=on_yes)
        yes_button.pack(side="left", padx=10, expand=True)

        no_button = customtkinter.CTkButton(button_frame, text="No", command=on_no)
        no_button.pack(side="right", padx=10, expand=True)

        messagebox.wait_window()
        return response["value"]

    def create_transfer_request_popup(self, info):
        '''info dictionary: transfer_uuid, ip, file_name, file_size, hash'''
        popup = customtkinter.CTkToplevel()
        popup.title("File Transfer Request")
        popup.geometry("400x320")
        popup.geometry(f"+{self.root.winfo_rootx() + 100}+{self.root.winfo_rooty() - 10}")
        popup.after(100, lambda: (popup.focus_force()))

        transfer_uuid = info["transfer_uuid"]
        ip = info["ip"]
        file_name = info["file_name"]
        file_size = convert_file_size(info["file_size"])
        hash = info["hash"]

        message = f"{ip} sent you a transfer request!\nFile: {file_name}\nSize: {file_size}\nSHA-1: {hash}"

        message_label = customtkinter.CTkLabel(popup, text=message, wraplength=380, anchor="w", justify="left")
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
        file_sender_window.after(10, lambda: file_sender_window.focus_force())

        file_label = customtkinter.CTkLabel(file_sender_window, text="No selected file", wraplength=380, anchor="n", justify="left")
        file_label.pack(pady=10, padx=10, fill="x")

        file_path = None
        
        def browse_file():
            nonlocal file_path
            path = filedialog.askopenfilename()
            file_sender_window.focus_force()
            if path:
                file_label.configure(text=f"{path}")
                file_path = path

        browse_button = customtkinter.CTkButton(file_sender_window, text="Browse File", command=browse_file)
        browse_button.pack(pady=10, padx=10)

        ip_label = customtkinter.CTkLabel(file_sender_window, text="Enter Receiver's IP:")
        ip_label.pack(pady=10, padx=10)

        ip_entry = customtkinter.CTkEntry(file_sender_window, placeholder_text="ipv4")
        ip_entry.pack(pady=10, padx=10)

        status_label = customtkinter.CTkLabel(file_sender_window, text="", wraplength=380, anchor="n", justify="left")
        status_label.pack(pady=10, padx=10, fill="x")
        
        self.sending_windows_status_labels.append(status_label)
        index = len(self.sending_windows_status_labels) - 1

        def send_transfer_request():
            if not file_path or not ip_entry.get():
                self.create_generic_popup("Please select a file and enter a valid IP address!")
                return
            self.presenter.send_transfer_request(ip_entry.get(), file_path, index)

        request_button = customtkinter.CTkButton(file_sender_window, text="Transfer", command=send_transfer_request)
        request_button.pack(pady=10, padx=10)




    def update_status_label(self, label_index, text):
        if self.sending_windows_status_labels[label_index]:
            self.sending_windows_status_labels[label_index].configure(text=text)


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
        display_X = info["display_X"]

        info_text = f"{file_name}\n"
        if is_outbound:
            info_text += f"To: {ip}\n"
        else:
            info_text += f"From: {ip}\n"

        info_text += f"{convert_file_size(transferred)}/{convert_file_size(file_size)}\nSpeed: {convert_file_size(transfer_speed)}/s\nSha-1: {hash}\nStatus: {status}"

        if not self.transfer_frames.get(transfer_uuid):
            frame = None
            if is_outbound:
                frame = customtkinter.CTkFrame(self.sending_list)
            else:
                frame = customtkinter.CTkFrame(self.receiving_list)

            frame.pack(fill="x", pady=5)

            frame.grid_columnconfigure(0, weight=1)

            info_label = customtkinter.CTkLabel(
                frame, text=info_text, anchor="w", justify="left", wraplength=380
            )
            info_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w")

            self.transfer_frames[transfer_uuid] = {
                "frame": frame,
                "label": info_label,
                "removed": False
            }

            def handle_pause_button():
                self.presenter.toggle_pause_transfer(transfer_uuid)

            def handle_cancel_button():
                self.presenter.cancel_transfer(transfer_uuid)

            pause_button = customtkinter.CTkButton(frame, text="Pause", width=50, command=handle_pause_button)
            pause_button.grid(row=1, column=0, padx=5, pady=5, sticky="e")

            cancel_button = customtkinter.CTkButton(frame, text="Cancel", width=50, command=handle_cancel_button)
            cancel_button.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        else:
            if self.transfer_frames[transfer_uuid]["removed"] == False:
                info_label = self.transfer_frames[transfer_uuid]["label"]
                info_label.configure(text=info_text)

        if display_X:
            frame = self.transfer_frames[transfer_uuid]["frame"]
            
            for widget in frame.grid_slaves(row=1):
                widget.grid_forget()

            def handle_x_button():
                self.transfer_frames[transfer_uuid]["frame"].pack_forget()
                self.transfer_frames[transfer_uuid]["removed"] = True

            x_button = customtkinter.CTkButton(frame, text="X", width=50, command=handle_x_button)
            x_button.grid(row=1, column=1, padx=5, pady=5, sticky="w" )

    def delete_transferring_frame_ui(self, transfer_uuid):
        self.transfer_frames[transfer_uuid]["frame"].destroy()
        del self.transfer_frames[transfer_uuid]

    def launch(self):
        self.root.mainloop()