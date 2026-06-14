import customtkinter as ctk
import serial.tools.list_ports
from src.lang import get_texts

class RobotPanel(ctk.CTkFrame):
    """
    Panel quản lý truyền thông với Delta Robot / PLC.
    Hỗ trợ hai phương thức truyền thông:
    1. Serial COM: Kết nối trực tiếp qua cổng COM ảo/vật lý.
    2. TCP/IP (PLC): Kết nối Client-Server tới PLC qua mạng Ethernet.
    """
    def __init__(self, master, on_connect_callback, on_disconnect_callback, on_send_manual_callback, **kwargs):
        super().__init__(master, **kwargs)

        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = on_disconnect_callback
        self.on_send_manual_callback = on_send_manual_callback

        self.is_connected = False
        self._texts = get_texts()

        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self,
            text=self._texts["robot_title"],
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)

        # ---------------- 1. KHU VỰC KẾT NỐI (TABVIEW) ----------------
        self.tabview = ctk.CTkTabview(self, height=250)
        self.tabview.pack(fill=ctk.X, padx=10, pady=5)

        self.tab_serial = self.tabview.add("Serial COM")
        self.tab_tcp    = self.tabview.add("TCP/IP (PLC)")

        self.tab_serial.grid_columnconfigure(1, weight=1)
        self.tab_tcp.grid_columnconfigure(1, weight=1)

        # --- CẤU HÌNH TAB SERIAL COM ---
        self.lbl_port = ctk.CTkLabel(self.tab_serial, text=self._texts["robot_port_label"])
        self.lbl_port.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.port_combo = ctk.CTkComboBox(self.tab_serial, values=["COM1", "COM2", "COM3", "COM4"])
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_refresh = ctk.CTkButton(self.tab_serial, text="🔄", width=30, command=self.refresh_ports)
        self.btn_refresh.grid(row=0, column=2, padx=(0, 5), pady=5)

        self.lbl_baud = ctk.CTkLabel(self.tab_serial, text=self._texts["robot_baud_label"])
        self.lbl_baud.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.baud_combo = ctk.CTkComboBox(self.tab_serial, values=["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.set("115200")
        self.baud_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.btn_connect = ctk.CTkButton(
            self.tab_serial, text="CONNECT",
            fg_color="#4CAF50", hover_color="#45a049", command=self.connect_serial
        )
        self.btn_connect.grid(row=2, column=0, columnspan=3, padx=5, pady=3, sticky="ew")

        self.btn_disconnect = ctk.CTkButton(
            self.tab_serial, text="DISCONNECT",
            fg_color="#f44336", hover_color="#d32f2f", state="disabled", command=self.disconnect_serial
        )
        self.btn_disconnect.grid(row=3, column=0, columnspan=3, padx=5, pady=3, sticky="ew")

        self.status_bar = ctk.CTkFrame(self.tab_serial, fg_color="transparent")
        self.status_bar.grid(row=4, column=0, columnspan=3, padx=5, pady=3, sticky="w")

        self.lbl_status_led = ctk.CTkLabel(
            self.status_bar,
            text=self._texts["robot_status_off"],
            text_color="#f44336", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_status_led.pack(side=ctk.LEFT)

        # --- CẤU HÌNH TAB TCP/IP (PLC) ---
        self.lbl_ip = ctk.CTkLabel(self.tab_tcp, text=self._texts["robot_ip_label"])
        self.lbl_ip.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.entry_ip = ctk.CTkEntry(self.tab_tcp, placeholder_text="192.168.1.10")
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.lbl_port_tcp = ctk.CTkLabel(self.tab_tcp, text=self._texts["robot_tcp_port_label"])
        self.lbl_port_tcp.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.entry_port_tcp = ctk.CTkEntry(self.tab_tcp, placeholder_text="5000")
        self.entry_port_tcp.insert(0, "5000")
        self.entry_port_tcp.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

        self.btn_connect_tcp = ctk.CTkButton(
            self.tab_tcp, text="CONNECT",
            fg_color="#4CAF50", hover_color="#45a049", command=self.connect_tcp
        )
        self.btn_connect_tcp.grid(row=2, column=0, columnspan=3, padx=5, pady=3, sticky="ew")

        self.btn_disconnect_tcp = ctk.CTkButton(
            self.tab_tcp, text="DISCONNECT",
            fg_color="#f44336", hover_color="#d32f2f", state="disabled", command=self.disconnect_tcp
        )
        self.btn_disconnect_tcp.grid(row=3, column=0, columnspan=3, padx=5, pady=3, sticky="ew")

        self.status_bar_tcp = ctk.CTkFrame(self.tab_tcp, fg_color="transparent")
        self.status_bar_tcp.grid(row=4, column=0, columnspan=3, padx=5, pady=3, sticky="w")

        self.lbl_status_led_tcp = ctk.CTkLabel(
            self.status_bar_tcp,
            text=self._texts["robot_status_off"],
            text_color="#f44336", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_status_led_tcp.pack(side=ctk.LEFT)

        # ---------------- 2. KHU VỰC ĐIỀU KHIỂN ROBOT THỦ CÔNG ----------------
        self.manual_group = ctk.CTkFrame(self)
        self.manual_group.pack(fill=ctk.X, padx=10, pady=5)

        self.lbl_manual_title = ctk.CTkLabel(
            self.manual_group, text=self._texts["robot_manual_title"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.lbl_manual_title.grid(row=0, column=0, columnspan=4, padx=10, pady=(5, 2), sticky="w")

        self.lbl_x = ctk.CTkLabel(self.manual_group, text=self._texts["robot_x"])
        self.lbl_x.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_x = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="0.0")
        self.entry_x.insert(0, "0.0")
        self.entry_x.grid(row=1, column=1, padx=5, pady=5)

        self.lbl_y = ctk.CTkLabel(self.manual_group, text=self._texts["robot_y"])
        self.lbl_y.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_y = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="0.0")
        self.entry_y.insert(0, "0.0")
        self.entry_y.grid(row=1, column=3, padx=5, pady=5)

        self.lbl_z = ctk.CTkLabel(self.manual_group, text=self._texts["robot_z"])
        self.lbl_z.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_z = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="200.0")
        self.entry_z.insert(0, "200.0")
        self.entry_z.grid(row=2, column=1, padx=5, pady=5)

        self.btn_send_manual = ctk.CTkButton(
            self.manual_group, text=self._texts["robot_btn_send"],
            command=self.send_manual
        )
        self.btn_send_manual.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        # Quét cổng COM khi khởi tạo
        self.refresh_ports()

    def apply_lang(self, texts: dict):
        """Cập nhật toàn bộ text theo ngôn ngữ mới."""
        self._texts = texts
        self.title_label.configure(text=texts["robot_title"])
        self.lbl_port.configure(text=texts["robot_port_label"])
        self.lbl_baud.configure(text=texts["robot_baud_label"])
        self.lbl_ip.configure(text=texts["robot_ip_label"])
        self.lbl_port_tcp.configure(text=texts["robot_tcp_port_label"])
        self.lbl_manual_title.configure(text=texts["robot_manual_title"])
        self.lbl_x.configure(text=texts["robot_x"])
        self.lbl_y.configure(text=texts["robot_y"])
        self.lbl_z.configure(text=texts["robot_z"])
        self.btn_send_manual.configure(text=texts["robot_btn_send"])
        # Cập nhật đèn trạng thái nếu đang ở trạng thái ngắt kết nối
        if not self.is_connected:
            self.lbl_status_led.configure(text=texts["robot_status_off"])
            self.lbl_status_led_tcp.configure(text=texts["robot_status_off"])

    def refresh_ports(self):
        """Dò quét cổng COM khả dụng trong hệ điều hành."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        no_port_text = self._texts["robot_no_port"]
        if ports:
            self.port_combo.configure(values=ports)
            self.port_combo.set(ports[0])
        else:
            self.port_combo.configure(values=[no_port_text])
            self.port_combo.set(no_port_text)

    def connect_serial(self):
        """Kích hoạt kết nối Serial và cập nhật trạng thái UI."""
        if self.is_connected:
            return
        port = self.port_combo.get()
        baudrate = int(self.baud_combo.get())
        if port == self._texts["robot_no_port"]:
            return

        success = self.on_connect_callback("SERIAL", port, baudrate)
        if success:
            self.is_connected = True
            self.btn_connect.configure(state="disabled")
            self.btn_disconnect.configure(state="normal")
            self.lbl_status_led.configure(
                text=self._texts["robot_status_on"].format(info=port),
                text_color="#4CAF50"
            )
            self.btn_connect_tcp.configure(state="disabled")

    def disconnect_serial(self):
        """Kích hoạt ngắt kết nối Serial và cập nhật trạng thái UI."""
        self.on_disconnect_callback("SERIAL")
        self.is_connected = False
        self.btn_connect.configure(state="normal")
        self.btn_disconnect.configure(state="disabled")
        self.lbl_status_led.configure(
            text=self._texts["robot_status_off"], text_color="#f44336"
        )
        self.btn_connect_tcp.configure(state="normal")

    def connect_tcp(self):
        """Kích hoạt kết nối TCP/IP PLC và cập nhật trạng thái UI."""
        if self.is_connected:
            return
        ip = self.entry_ip.get().strip()
        if not ip:
            return
        try:
            port = int(self.entry_port_tcp.get().strip())
        except ValueError:
            return

        success = self.on_connect_callback("TCP", ip, port)
        if success:
            self.is_connected = True
            self.btn_connect_tcp.configure(state="disabled")
            self.btn_disconnect_tcp.configure(state="normal")
            self.lbl_status_led_tcp.configure(
                text=self._texts["robot_status_on"].format(info=f"{ip}:{port}"),
                text_color="#4CAF50"
            )
            self.btn_connect.configure(state="disabled")

    def disconnect_tcp(self):
        """Kích hoạt ngắt kết nối TCP/IP và cập nhật trạng thái UI."""
        self.on_disconnect_callback("TCP")
        self.is_connected = False
        self.btn_connect_tcp.configure(state="normal")
        self.btn_disconnect_tcp.configure(state="disabled")
        self.lbl_status_led_tcp.configure(
            text=self._texts["robot_status_off"], text_color="#f44336"
        )
        self.btn_connect.configure(state="normal")

    def send_manual(self):
        """Thu thập dữ liệu tọa độ X, Y, Z từ ô nhập và gửi đi."""
        try:
            x = float(self.entry_x.get())
            y = float(self.entry_y.get())
            z = float(self.entry_z.get())
            self.on_send_manual_callback(x, y, z)
        except ValueError:
            pass

    def get_connection_info(self):
        """Trả về thông tin kết nối hiện tại."""
        active_tab = self.tabview.get()
        if active_tab == "Serial COM":
            return {
                "mode": "SERIAL",
                "port": self.port_combo.get(),
                "baudrate": int(self.baud_combo.get()) if self.baud_combo.get().isdigit() else 115200,
                "is_connected": self.is_connected
            }
        else:
            return {
                "mode": "TCP",
                "ip": self.entry_ip.get().strip(),
                "port": int(self.entry_port_tcp.get().strip()) if self.entry_port_tcp.get().strip().isdigit() else 5000,
                "is_connected": self.is_connected
            }
