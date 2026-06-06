import customtkinter as ctk
import serial.tools.list_ports

class RobotPanel(ctk.CTkFrame):
    """
    Panel quản lý truyền thông với Delta Robot qua Serial (COM Port).
    Hỗ trợ dò cổng kết nối tự động, bắt lỗi kết nối và gửi lệnh chạy thử.
    """
    def __init__(self, master, on_connect_callback, on_disconnect_callback, on_send_manual_callback, **kwargs):
        super().__init__(master, **kwargs)
        
        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = on_disconnect_callback
        self.on_send_manual_callback = on_send_manual_callback
        
        self.is_connected = False
        
        # Tiêu đề Panel
        self.title_label = ctk.CTkLabel(
            self, 
            text="🤖 TRUYỀN THÔNG & ĐIỀU KHIỂN ROBOT", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=5)
        
        # ---------------- 1. KHU VỰC KẾT NỐI SERIAL ----------------
        self.conn_group = ctk.CTkFrame(self)
        self.conn_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm Serial Connection
        ctk.CTkLabel(
            self.conn_group, text="🔌 Thiết Lập Kết Nối Serial", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 2), sticky="w")
        
        # Chọn Cổng COM
        self.lbl_port = ctk.CTkLabel(self.conn_group, text="Cổng COM (Port):")
        self.lbl_port.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.port_combo = ctk.CTkComboBox(self.conn_group, values=["COM1", "COM2", "COM3", "COM4"])
        self.port_combo.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        self.btn_refresh = ctk.CTkButton(self.conn_group, text="🔄", width=30, command=self.refresh_ports)
        self.btn_refresh.grid(row=1, column=2, padx=(0, 10), pady=5)
        
        # Chọn Baudrate
        self.lbl_baud = ctk.CTkLabel(self.conn_group, text="Baudrate:")
        self.lbl_baud.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.baud_combo = ctk.CTkComboBox(self.conn_group, values=["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.set("115200")
        self.baud_combo.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Các nút bấm kết nối
        self.btn_connect = ctk.CTkButton(
            self.conn_group, text="CONNECT", fg_color="#4CAF50", hover_color="#45a049", command=self.connect
        )
        self.btn_connect.grid(row=3, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        
        self.btn_disconnect = ctk.CTkButton(
            self.conn_group, text="DISCONNECT", fg_color="#f44336", hover_color="#d32f2f", state="disabled", command=self.disconnect
        )
        self.btn_disconnect.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        
        # Đèn báo trạng thái kết nối
        self.status_bar = ctk.CTkFrame(self.conn_group, fg_color="transparent")
        self.status_bar.grid(row=5, column=0, columnspan=3, padx=10, pady=5, sticky="w")
        
        self.lbl_status_led = ctk.CTkLabel(
            self.status_bar, text="🔴 NGẮT KẾT NỐI", text_color="#f44336", font=ctk.CTkFont(size=11, weight="bold")
        )
        self.lbl_status_led.pack(side=ctk.LEFT)
 
        # ---------------- 2. KHU VỰC ĐIỀU KHIỂN ROBOT THỦ CÔNG ----------------
        self.manual_group = ctk.CTkFrame(self)
        self.manual_group.pack(fill=ctk.X, padx=10, pady=5)
        
        # Tiêu đề nhóm gửi lệnh thủ công
        ctk.CTkLabel(
            self.manual_group, text="🎮 Gửi Lệnh Thủ Công (Test)", font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, columnspan=4, padx=10, pady=(5, 2), sticky="w")
        
        # Ô nhập tọa độ X, Y, Z
        self.lbl_x = ctk.CTkLabel(self.manual_group, text="X (mm):")
        self.lbl_x.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_x = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="0.0")
        self.entry_x.insert(0, "0.0")
        self.entry_x.grid(row=1, column=1, padx=5, pady=5)
        
        self.lbl_y = ctk.CTkLabel(self.manual_group, text="Y (mm):")
        self.lbl_y.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_y = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="0.0")
        self.entry_y.insert(0, "0.0")
        self.entry_y.grid(row=1, column=3, padx=5, pady=5)
        
        self.lbl_z = ctk.CTkLabel(self.manual_group, text="Z (mm):")
        self.lbl_z.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.entry_z = ctk.CTkEntry(self.manual_group, width=65, placeholder_text="200.0")
        self.entry_z.insert(0, "200.0")
        self.entry_z.grid(row=2, column=1, padx=5, pady=5)
        
        # Nút gửi lệnh test
        self.btn_send_manual = ctk.CTkButton(
            self.manual_group, text="🚀 Gửi Lệnh Chạy", command=self.send_manual
        )
        self.btn_send_manual.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")

        # Quét cổng COM khi khởi tạo
        self.refresh_ports()

    def refresh_ports(self):
        """Dò quét cổng COM khả dụng trong hệ điều hành."""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if ports:
            self.port_combo.configure(values=ports)
            self.port_combo.set(ports[0])
        else:
            self.port_combo.configure(values=["Không tìm thấy COM"])
            self.port_combo.set("Không tìm thấy COM")

    def connect(self):
        """Kích hoạt kết nối và cập nhật trạng thái UI."""
        port = self.port_combo.get()
        baudrate = int(self.baud_combo.get())
        if port == "Không tìm thấy COM":
            return
            
        success = self.on_connect_callback(port, baudrate)
        if success:
            self.is_connected = True
            self.btn_connect.configure(state="disabled")
            self.btn_disconnect.configure(state="normal")
            self.lbl_status_led.configure(text=f"🟢 ĐÃ KẾT NỐI ({port})", text_color="#4CAF50")
            
    def disconnect(self):
        """Kích hoạt ngắt kết nối và cập nhật trạng thái UI."""
        self.on_disconnect_callback()
        self.is_connected = False
        self.btn_connect.configure(state="normal")
        self.btn_disconnect.configure(state="disabled")
        self.lbl_status_led.configure(text="🔴 NGẮT KẾT NỐI", text_color="#f44336")

    def send_manual(self):
        """Thu thập dữ liệu tọa độ X, Y, Z từ ô nhập và gửi đi."""
        try:
            x = float(self.entry_x.get())
            y = float(self.entry_y.get())
            z = float(self.entry_z.get())
            self.on_send_manual_callback(x, y, z)
        except ValueError:
            # Lỗi nhập liệu
            pass
            
    def get_connection_info(self):
        """Trả về thông tin kết nối hiện tại."""
        return {
            "port": self.port_combo.get(),
            "baudrate": int(self.baud_combo.get()),
            "is_connected": self.is_connected
        }
