"""
LLDP Network Analyzer - Professional UI with PyQt6
Modern card-based design with clean architecture
"""

import sys
import os
from typing import Optional
import io
from datetime import datetime

# Print redirector to avoid emoji encoding errors
class SafeWriter:
    """Safe writer that handles emoji characters without encoding errors"""
    def __init__(self, original_writer):
        self.original_writer = original_writer

    def write(self, text):
        # If original_writer is None (console=False mode), silently discard
        if self.original_writer is None:
            return len(text) if text else 0

        try:
            return self.original_writer.write(text)
        except (UnicodeEncodeError, AttributeError):
            # Replace problematic characters or handle missing attributes
            try:
                safe_text = text.encode('ascii', 'replace').decode('ascii')
                return self.original_writer.write(safe_text)
            except:
                return len(text) if text else 0

    def flush(self):
        if self.original_writer is not None:
            try:
                return self.original_writer.flush()
            except:
                pass

# Redirect stdout to safe writer (handles None case for console=False)
sys.stdout = SafeWriter(getattr(sys, 'stdout', None))
sys.stderr = SafeWriter(getattr(sys, 'stderr', None))
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QGroupBox, QPushButton, QComboBox,
    QProgressBar, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette

# Import from clean architecture
from lldp import LLDPCaptureListener
from lldp.model import LLDPDevice
from lldp.view_model import to_view, DeviceView, GREEN_BADGE, BLUE_BADGE, YELLOW_BADGE, PURPLE_BADGE
from lldp.utils import safe_get


class InfoCard(QGroupBox):
    """Modern info card widget"""

    def __init__(self, title: str):
        super().__init__(title)
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 12px;
                font-size: 14px;
                font-weight: 600;
                color: #e2e8f0;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px 0 4px;
            }
        """)
        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.setLayout(self.layout)

    def add_row(self, name: str, value: str = "—") -> QLabel:
        """Add a row to the card"""
        row = QHBoxLayout()

        label_name = QLabel(name)
        label_value = QLabel(value)
        label_value.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Apply specific styles to each label
        label_name.setStyleSheet("color:#94a3b8; font-size:13px;")
        label_value.setStyleSheet("color:#22c55e; font-weight:600; font-size:13px;")

        row.addWidget(label_name)
        row.addWidget(label_value)
        self.layout.addLayout(row)

        return label_value

    def update_row(self, label: QLabel, value: str):
        """Update a row's value"""
        label.setText(value)


class LLDPProfessionalWindow(QWidget):
    """Professional LLDP Network Analyzer Window"""

    # Define signals for thread-safe UI updates
    device_discovered = pyqtSignal(object)
    capture_complete = pyqtSignal(list)
    debug_log = pyqtSignal(str)  # 🔥 新增：DEBUG日志信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLDP Network Analyzer v2.0 - Semantic Inference Engine")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color:#0f172a; font-family:'Segoe UI Variable','Microsoft YaHei UI';")

        # 🔥 设置窗口图标
        self._set_window_icon()

        # Core components (clean architecture)
        self.listener = None
        self.current_device: Optional[LLDPDevice] = None
        self.discovered_devices = []

        # 🔥 Debug输出 - 现在输出到UI日志框
        # print("[DEBUG] ========================================", flush=True)
        # print("[DEBUG] LLDP Professional Window Initializing...", flush=True)
        # print("[DEBUG] CDP Support: ENABLED 🔥", flush=True)
        # print("[DEBUG] Debug Console: ACTIVE ✅", flush=True)
        # print("[DEBUG] ========================================", flush=True)

        # Build UI
        self.setup_ui()

        # 🔥 恢复日志功能，但要优化避免卡死UI
        self.log_buffer = []
        self.debug_enabled = False
        self.debug_log_queue = []  # 🔥 新增：DEBUG日志队列（线程安全）
        self.debug_log_timer = None  # 🔥 新增：DEBUG日志处理定时器

        # Setup logging
        self.setup_logging()

        # Setup DEBUG output capture
        self.setup_debug_capture()

        # 🔥 连接DEBUG日志信号
        self.debug_log.connect(self._on_debug_log_ui)

        # Auto-detect interfaces

        # Auto-detect interfaces
        self.log("开始自动检测网络接口...", "DEBUG")
        try:
            self.refresh_interfaces()
            self.log("网络接口检测完成", "DEBUG")
        except Exception as e:
            self.log(f"网络接口检测失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()

        # Connect signals to slots for thread-safe UI updates
        # 🔥 CRITICAL: Use QueuedConnection to ensure slots run in main thread, not capture thread
        self.log("连接基础信号槽...", "DEBUG")
        self.device_discovered.connect(self._on_device_discovered_ui, Qt.ConnectionType.QueuedConnection)
        self.capture_complete.connect(self._on_capture_complete_ui, Qt.ConnectionType.QueuedConnection)
        self.log("基础信号槽连接完成", "DEBUG")

    def _set_window_icon(self):
        """Set window icon from file"""
        from PyQt6.QtGui import QIcon
        import os

        # 查找图标文件
        meipass = getattr(sys, '_MEIPASS', '')
        icon_paths = [
            # 开发环境：使用相对路径
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lldp_icon.png'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lldp_icon.ico'),
            # 打包后：在sys._MEIPASS中查找
            os.path.join(meipass, 'lldp_icon.png'),
            os.path.join(meipass, 'lldp_icon.ico'),
            # 当前目录
            'lldp_icon.png',
            'lldp_icon.ico',
        ]

        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    icon = QIcon(icon_path)
                    self.setWindowIcon(icon)
                    return
                except Exception:
                    continue

        # 如果没有找到图标文件，使用默认图标
        pass

    def setup_ui(self):
        """Setup user interface"""
        main = QVBoxLayout()
        main.setSpacing(20)

        # Header section
        header = self.create_header()
        main.addLayout(header)

        # Content section (cards)
        content = self.create_content()
        main.addLayout(content)

        # Progress section
        progress = self.create_progress()
        main.addLayout(progress)

        # Log section
        log_section = self.create_log_section()
        main.addLayout(log_section)

        self.setLayout(main)

        # 🔥 在UI创建完成后连接debug_checkbox信号
        self.debug_checkbox.stateChanged.connect(self._on_debug_checkbox_changed)

    def setup_logging(self):
        """Setup logging to redirect print statements to UI"""
        self.log("系统初始化完成")
        self.log("LLDP/CDP 双协议支持已启用")
        self.log("准备就绪 - 请选择网络适配器")

    def setup_debug_capture(self):
        """Setup DEBUG output capture to show detailed packet parsing"""
        # Don't replace print function at startup - wait for user to check the checkbox
        import builtins
        self.original_print = builtins.print
        self.debug_enabled = False
        # No print replacement yet - will be done when user checks checkbox

    def _on_debug_checkbox_changed(self, state):
        """Handle debug checkbox state change"""
        import builtins

        if state == 2:  # Checked
            self.debug_enabled = True

            # 🔥 Start debug log processing timer
            if not self.debug_log_timer:
                self.debug_log_timer = QTimer()
                self.debug_log_timer.timeout.connect(self._process_debug_log_queue)
                self.debug_log_timer.start(50)  # 每50ms处理一次队列

            # Replace print function to capture DEBUG output
            def custom_print(*args, **kwargs):
                """Custom print function that captures DEBUG output"""
                message = ' '.join(str(arg) for arg in args)

                # Check if this is a DEBUG message
                if '[DEBUG]' in message or '[ERROR]' in message or 'Packet:' in message:
                    # 🔥 线程安全：将日志放入队列，而不是直接调用UI方法
                    self.debug_log_queue.append(message)
                else:
                    self.original_print(*args, **kwargs)

            builtins.print = custom_print
            self.log("详细DEBUG日志已启用", "INFO")
        else:  # Unchecked
            self.debug_enabled = False
            builtins.print = self.original_print

            # 🔥 Stop debug log processing timer
            if self.debug_log_timer:
                self.debug_log_timer.stop()
                self.debug_log_timer = None

            # 清空队列
            self.debug_log_queue.clear()

            self.log("详细DEBUG日志已禁用", "INFO")

    def _process_debug_log_queue(self):
        """处理DEBUG日志队列 - 在主线程中执行"""
        if not self.debug_log_queue:
            return

        # 🔥 优化：限制DEBUG日志显示，防止阻塞UI
        max_display = 100  # 最多显示100条DEBUG日志
        current_count = len(self.debug_log_queue)

        # 如果队列太大，直接清空多余部分
        if current_count > max_display:
            # 使用log方法而不是log_raw，因为log支持level参数
            self.log(f"DEBUG日志过多（{current_count}条），已自动清理", "WARNING")
            # 只保留最后50条
            self.debug_log_queue = self.debug_log_queue[-50:]

        # 批量处理，每次最多5条，避免阻塞UI
        batch_size = 5
        processed = 0

        while self.debug_log_queue and processed < batch_size:
            message = self.debug_log_queue.pop(0)

            # 🔥 只显示重要的DEBUG日志，过滤掉详细的数据包解析
            if any(keyword in message for keyword in [
                'Device found', 'VLAN:', 'H3C Private TLV',
                '已发现', '完成', 'SUCCESS', 'ERROR', 'WARNING'
            ]):
                self.log_raw(message)
            elif '[DEBUG] 📊 Processed' in message:
                # 每100个包显示一次进度
                self.log_raw(message)

            processed += 1

    def _on_debug_log_ui(self, message: str):
        """DEBUG日志UI更新槽 - 在主线程中执行"""
        self.log_raw(message)

    def log(self, message: str, level: str = "INFO"):
        """Add log message to the log display"""
        import datetime

        # 🔥 安全检查：debug_checkbox可能还未初始化
        if hasattr(self, 'debug_checkbox') and level == "DEBUG":
            if not self.debug_checkbox.isChecked():
                return  # Skip DEBUG messages unless checkbox is checked

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 🔥 添加到日志缓冲区（用于自动保存）
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_buffer.append(log_entry)

        # Color coding based on level
        color_map = {
            "INFO": "#94a3b8",
            "DEBUG": "#f59e0b",     # Orange for DEBUG
            "SUCCESS": "#22c55e",
            "WARNING": "#f59e0b",
            "ERROR": "#ef4444"
        }

        color = color_map.get(level, "#94a3b8")
        formatted_message = f'<span style="color:{color};">[{timestamp}] {message}</span>'

        self.log_text.append(formatted_message)

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def log_raw(self, message: str):
        """Add raw DEBUG output (for detailed packet parsing)"""
        # 🔥 安全检查：确保UI组件存在且debug_checkbox已勾选
        if not hasattr(self, 'debug_checkbox') or not self.debug_checkbox.isChecked():
            return

        if not hasattr(self, 'log_text'):
            return

        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Display raw debug output in monospace font
        formatted_message = f'<span style="color:#64748b; font-family:monospace;">[{timestamp}] {message}</span>'
        self.log_text.append(formatted_message)

        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _auto_save_log(self):
        """自动保存日志到文件，防止程序崩溃导致日志丢失"""
        try:
            if self.log_buffer and self.current_log_file:
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    for log_entry in self.log_buffer:
                        f.write(log_entry + '\n')
                # 清空已保存的日志
                self.log_buffer.clear()
        except Exception as e:
            print(f"[ERROR] Failed to auto-save log: {e}")

    def create_header(self):
        """Create header with controls"""
        layout = QHBoxLayout()

        # Left side - Title
        title_layout = QVBoxLayout()
        title = QLabel("LLDP Network Analyzer")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #e2e8f0;
        """)

        subtitle = QLabel("Professional Network Discovery Tool")
        subtitle.setStyleSheet("""
            font-size: 12px;
            color: #64748b;
        """)

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addLayout(title_layout)

        # Right side - Controls
        controls = QVBoxLayout()

        # Adapter selector
        adapter_row = QHBoxLayout()
        adapter_label = QLabel("网络适配器:")
        adapter_label.setStyleSheet("color:#94a3b8; font-size:13px;")

        self.adapter_combo = QComboBox()
        self.adapter_combo.setStyleSheet("""
            QComboBox {
                background:#1e293b;
                color:#cbd5e1;
                border:1px solid #334155;
                border-radius:4px;
                padding:6px 12px;
                min-width:250px;
            }
            QComboBox:hover {
                border:1px solid #475569;
            }
            QComboBox::drop-down {
                background:#1e293b;
                border:1px solid #334155;
            }
        """)

        adapter_row.addWidget(adapter_label)
        adapter_row.addWidget(self.adapter_combo)
        adapter_row.addStretch()

        # Buttons
        self.start_btn = QPushButton("开始捕获")
        self.stop_btn = QPushButton("停止")
        self.export_btn = QPushButton("导出")

        self.setup_button_style(self.start_btn, "#2563eb")
        self.setup_button_style(self.stop_btn, "#dc2626")
        self.setup_button_style(self.export_btn, "#059669")

        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_btn)
        button_row.addWidget(self.stop_btn)
        button_row.addWidget(self.export_btn)
        button_row.addStretch()

        # Add to controls
        controls.addLayout(adapter_row)
        controls.addLayout(button_row)

        layout.addLayout(controls)

        return layout

    def create_content(self):
        """Create content area with info cards"""
        layout = QHBoxLayout()
        layout.setSpacing(20)

        # Left card - Switch Info
        self.card_switch = InfoCard("设备信息")
        self.sw_name = self.card_switch.add_row("系统名称")
        self.sw_model = self.card_switch.add_row("设备型号")
        self.sw_serial = self.card_switch.add_row("序列号")
        self.sw_mac = self.card_switch.add_row("设备 MAC")
        self.sw_type = self.card_switch.add_row("ID类型")
        self.sw_ip = self.card_switch.add_row("管理地址")
        self.sw_software = self.card_switch.add_row("软件版本")
        self.lldp_med = self.card_switch.add_row("LLDP-MED能力")

        layout.addWidget(self.card_switch)

        # Right card - Port Info
        self.card_port = InfoCard("连接端口")
        # 🔥 NEW: Port Semantic Profile (协议语义推断)
        self.port_role = self.card_port.add_row("端口角色")  # 新增：显示推断的端口角色
        self.protocol = self.card_port.add_row("协议类型")
        self.port_id = self.card_port.add_row("端口 ID")
        self.port_type = self.card_port.add_row("ID类型")
        self.port_desc = self.card_port.add_row("端口描述")
        self.port_vlan = self.card_port.add_row("VLAN (Native)")
        self.protocol_vlan = self.card_port.add_row("协议VLAN")
        self.macphy = self.card_port.add_row("速率/双工")
        self.link_agg = self.card_port.add_row("链路聚合")
        self.mtu = self.card_port.add_row("最大帧长")
        self.poe = self.card_port.add_row("PoE")
        self.capabilities = self.card_port.add_row("设备能力")

        layout.addWidget(self.card_port)

        # Show initial state
        QTimer.singleShot(100, self.show_initial_state)

        return layout

    def show_initial_state(self):
        """Show initial waiting state"""
        # Switch info
        self.sw_name.setText("等待开始捕获")
        self.sw_name.setStyleSheet("color:#fbbf24; font-weight:600;")

        self.sw_model.setText("选择网络适配器并点击'开始捕获'")
        self.sw_model.setStyleSheet("color:#64748b;")

        self.sw_serial.setText("未知")
        self.sw_mac.setText("未知")
        self.sw_type.setText("未知")
        self.sw_ip.setText("未知")
        self.sw_software.setText("未知")
        self.lldp_med.setText("未知")

        # Port info
        self.port_role.setText("等待捕获...")  # NEW
        self.port_role.setStyleSheet("color:#94a3b8;")  # NEW
        self.protocol.setText("等待开始捕获")
        self.protocol.setStyleSheet("color:#fbbf24; font-weight:600;")
        self.port_id.setText("等待开始捕获")
        self.port_id.setStyleSheet("color:#fbbf24; font-weight:600;")

        self.port_type.setText("未知")
        self.port_desc.setText("未知")
        self.port_vlan.setText("未知")
        self.macphy.setText("未知")
        self.link_agg.setText("未知")
        self.mtu.setText("未知")
        self.poe.setText("未知")
        self.capabilities.setText("未知")

    def create_progress(self):
        """Create progress section"""
        layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background:#1e293b;
                border:1px solid #334155;
                border-radius:4px;
                height:8px;
                text-align:center;
            }
            QProgressBar::chunk {
                background:#22c55e;
                border-radius:3px;
            }
        """)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        # Status label
        self.status_label = QLabel("就绪 - 请选择网络适配器并开始捕获")
        self.status_label.setStyleSheet("""
            font-size:12px;
            color:#94a3b8;
        """)

        # Device count
        self.device_count_label = QLabel("已发现: 0 台设备")
        self.device_count_label.setStyleSheet("""
            font-size:12px;
            color:#64748b;
        """)

        # Bottom row
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.device_count_label)
        bottom_row.addStretch()

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addLayout(bottom_row)

        return layout

    def create_log_section(self):
        """Create log display section - Full version with checkbox"""
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Log header with checkbox
        header_layout = QHBoxLayout()

        title = QLabel("📋 运行日志")
        title.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #e2e8f0;
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Debug checkbox
        from PyQt6.QtWidgets import QCheckBox
        self.debug_checkbox = QCheckBox("显示详细DEBUG日志")
        self.debug_checkbox.setChecked(False)
        self.debug_checkbox.setStyleSheet("""
            QCheckBox {
                color: #94a3b8;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #475569;
                background: #1e293b;
            }
            QCheckBox::indicator:checked {
                background: #22c55e;
                border-color: #22c55e;
            }
        """)
        header_layout.addWidget(self.debug_checkbox)

        layout.addLayout(header_layout)

        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background:#1e293b;
                color:#94a3b8;
                border:1px solid #334155;
                border-radius:6px;
                padding:8px;
                font-family:'Consolas','Monaco',monospace;
                font-size:11px;
            }
            QScrollBar:vertical {
                background:#1e293b;
                width:8px;
                border-radius:4px;
            }
            QScrollBar::handle:vertical {
                background:#475569;
                border-radius:4px;
                min-height:20px;
            }
            QScrollBar::handle:vertical:hover {
                background:#64748b;
            }
        """)
        layout.addWidget(self.log_text)

        return layout

    def setup_button_style(self, button: QPushButton, color: str):
        """Setup modern button style"""
        button.setStyleSheet(f"""
            QPushButton {{
                background:{color};
                color:white;
                border-radius:6px;
                padding:10px 20px;
                font-size:14px;
                font-weight:600;
            }}
            QPushButton:hover {{
                opacity:0.9;
            }}
            QPushButton:disabled {{
                background:#334155;
                color:#64748b;
            }}
        """)

        # Connect signals
        if button.text() == "开始捕获":
            button.clicked.connect(self.start_capture)
        elif button.text() == "停止":
            button.clicked.connect(self.stop_capture)
        elif button.text() == "导出":
            button.clicked.connect(self.export_data)

    def refresh_interfaces(self):
        """Refresh network adapter list"""
        try:
            from scapy.all import get_working_ifaces

            self.adapter_combo.clear()
            self.interfaces = []

            self.log("开始扫描网络接口...", "DEBUG")
            print(f"[DEBUG] ===== Scanning for network interfaces =====", flush=True)

            all_interfaces = list(get_working_ifaces())
            self.log(f"发现 {len(all_interfaces)} 个网络接口", "DEBUG")
            print(f"[DEBUG] Found {len(all_interfaces)} total interfaces", flush=True)

            for iface in all_interfaces:
                print(f"[DEBUG] Checking interface: {iface.name}", flush=True)
                print(f"[DEBUG]  Description: {iface.description}", flush=True)

                # 只选择有线物理网卡，排除无线和虚拟网卡
                desc = iface.description.lower()
                name = iface.name.lower()

                # 排除条件：无线、虚拟、VPN、调试等网卡
                is_excluded = (
                    # 排除无线网卡
                    "wi-fi" in desc or "wifi" in desc or "wireless" in desc or
                    "802.11" in desc or "wlan" in name or "wi" in name or

                    # 排除虚拟网卡
                    "virtual" in desc or "hyper-v" in desc or "vmware" in desc or
                    "virtualbox" in desc or "vbox" in desc or "qemu" in desc or
                    "vnic" in desc or "vEthernet" in name or "vnic" in name or

                    # 排除VPN网卡
                    "vpn" in desc or "tap" in name or "tun" in name or
                    "point-to-point" in desc or "ppp" in name or

                    # 排除调试网卡
                    "ndis" in desc or "loopback" in desc or name == "lo" or
                    "bluetooth" in desc or "bt" in name or

                    # 排除WAN Miniport网卡（网络监控等）
                    "wan miniport" in desc or "miniport" in desc or
                    "network monitor" in desc or "monitor" in desc or

                    # 排除容器网卡
                    "docker" in desc or "bridge" in desc or "veth" in name or
                    "container" in desc
                )

                # 包含条件：必须是有线物理网卡的特征
                is_included = (
                    # 标准以太网描述
                    "ethernet" in desc or "以太网" in desc or
                    # 有线网卡制造商
                    "realtek" in desc or "intel" in desc or
                    "broadcom" in desc or "qualcomm" in desc or
                    "marvell" in desc or "killer" in desc or
                    # 控制器类型
                    ("controller" in desc and "network" in desc) or
                    "pci" in desc or "express" in desc or
                    # Linux有线网卡命名
                    name.startswith("eth") or name.startswith("en") or
                    # 通用网络适配器（必须包含adapter且不是虚拟的）
                    ("adapter" in desc and not is_excluded) or
                    # 简单的网卡描述（在Windows中常见）
                    ("network" in desc or "lan" in desc) and not is_excluded
                )

                is_valid = is_included and not is_excluded

                if is_valid:
                    self.interfaces.append(iface)
                    display_text = f"{iface.description} ({iface.name})"
                    self.adapter_combo.addItem(display_text, iface)
                    self.log(f"添加网卡: {display_text}", "DEBUG")
                    print(f"[DEBUG] ✅ Added interface: {display_text}", flush=True)

            self.log(f"扫描完成，找到 {len(self.interfaces)} 个有效网卡", "SUCCESS")
            print(f"[DEBUG] Found {len(self.interfaces)} valid network interfaces", flush=True)
            print(f"[DEBUG] ========================================", flush=True)

            if self.interfaces:
                self.start_btn.setEnabled(True)
                self.status_label.setText(f"找到 {len(self.interfaces)} 个网络适配器")
            else:
                self.start_btn.setEnabled(False)
                self.status_label.setText("⚠️ 未找到合适的网络适配器")
                self.log("未找到合适的网络适配器", "WARNING")
                QMessageBox.warning(self, "网络接口问题",
                    "未找到合适的网络适配器！\n\n"
                    "可能的原因：\n"
                    "1. 没有安装Npcap驱动\n"
                    "2. 没有物理网络连接\n"
                    "3. 网络适配器被禁用\n\n"
                    "请检查网络连接后重试。")

        except Exception as e:
            print(f"[DEBUG] ❌ Error scanning interfaces: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"❌ 错误: 无法扫描网络适配器")
            QMessageBox.critical(self, "严重错误", f"无法扫描网络适配器！\n\n错误信息: {e}")

    def start_capture(self):
        """Start LLDP capture"""
        print(f"[DEBUG] ===== start_capture called =====", flush=True)

        if not hasattr(self, 'interfaces') or not self.interfaces:
            print(f"[DEBUG] ❌ No interfaces available!", flush=True)
            QMessageBox.warning(self, "警告", "请先选择网络适配器！\n\n没有找到可用的网络适配器。")
            return

        print(f"[DEBUG] Available interfaces: {len(self.interfaces)}", flush=True)

        # Get selected interface
        current_data = self.adapter_combo.currentData()
        if not current_data:
            self.log("没有选择网络适配器", "ERROR")
            print(f"[DEBUG] ❌ No interface selected!", flush=True)
            QMessageBox.warning(self, "警告", "请选择一个网络适配器！")
            return

        interface = current_data
        self.log(f"选择网卡: {interface.description}", "INFO")
        print(f"[DEBUG] ✅ Selected interface: {interface.description} ({interface.name})", flush=True)
        print(f"[DEBUG] Starting capture on: {interface.description}", flush=True)

        # 🔍 物理链路检查 - 避免盲目捕获
        print(f"[DEBUG] 🔍 Checking physical link status...", flush=True)
        has_ip = hasattr(interface, 'ip') and interface.ip is not None

        if has_ip:
            self.log(f"网卡IP: {interface.ip} - 链路正常", "SUCCESS")
            print(f"[DEBUG] ✅ Interface has IP: {interface.ip}", flush=True)
            print(f"[DEBUG] ✅ Physical link appears to be UP", flush=True)
        else:
            self.log(f"网卡无IP地址 - 链路可能未连接", "WARNING")
            print(f"[DEBUG] ❌ Interface has NO IP address!", flush=True)
            print(f"[DEBUG] ❌ Physical link might be DOWN!", flush=True)

            # 弹出警告对话框
            reply = QMessageBox.question(
                self,
                "物理链路警告",
                f"⚠️ 选中网卡没有IP地址，可能物理链路未连接：\n\n"
                f"网卡: {interface.description}\n"
                f"状态: 无IP地址\n\n"
                f"请检查：\n"
                f"1. 网线是否插好？\n"
                f"2. 交换机是否开机？\n"
                f"3. 网卡是否启用？\n\n"
                f"是否继续捕获？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                print(f"[DEBUG] User cancelled capture due to no IP", flush=True)
                return

            print(f"[DEBUG] User chose to continue despite no IP", flush=True)

        # Initialize listener
        self.listener = LLDPCaptureListener()
        self.discovered_devices = []
        self.capture_start_time = 0
        self.is_capturing = True

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self.status_label.setText("正在捕获LLDP报文...")
        self.progress_bar.setValue(0)
        self.device_count_label.setText("已发现: 0 台设备")

        # Update status to show capturing
        QTimer.singleShot(100, lambda: self.show_capture_status())

        # Start progress timer
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(100)

        # Start capture with callbacks
        try:
            self.log("开始LLDP/CDP报文捕获...", "INFO")
            print(f"[DEBUG] ========================================", flush=True)
            print(f"[DEBUG] 🚀 STARTING CAPTURE PROCESS", flush=True)
            print(f"[DEBUG] Interface: {interface.description}", flush=True)
            print(f"[DEBUG] Interface Name: {interface.name}", flush=True)
            print(f"[DEBUG] Max Duration: 60 seconds (will stop early if device found!)", flush=True)
            print(f"[DEBUG] ========================================", flush=True)

            self.listener.start(
                interface=interface,
                duration=60,  # 最长60秒，发现设备后立即停止
                on_device_discovered=self.on_device_discovered,
                on_capture_complete=self.on_capture_complete
            )
            self.log("捕获进程已启动，最长60秒", "SUCCESS")
            print("[DEBUG] Capture started successfully")
        except Exception as e:
            self.log(f"捕获启动失败: {e}", "ERROR")
            print(f"[ERROR] Capture failed: {e}")
            QMessageBox.critical(self, "错误", f"捕获启动失败:\n{str(e)}")
            self.capture_complete_update()

    def show_capture_status(self):
        """Show capturing status in cards"""
        self.sw_name.setText("正在捕获LLDP报文...")
        self.sw_name.setStyleSheet("color:#22c55e; font-weight:600;")

        self.sw_mac.setText("等待设备发现...")
        self.sw_mac.setStyleSheet("color:#94a3b8;")

        self.port_id.setText("正在捕获LLDP报文...")
        self.port_id.setStyleSheet("color:#22c55e; font-weight:600;")

    def stop_capture(self):
        """Stop capture - Thread-safe!"""
        try:
            # Stop listener first
            if self.listener:
                self.listener.stop()

            # Update state
            self.is_capturing = False

            # Stop progress timer safely
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()

            # Update UI (use QTimer to ensure it runs in main thread)
            QTimer.singleShot(0, self._update_ui_after_stop)

        except Exception as e:
            self.log(f"停止捕获时出错: {e}", "ERROR")
            import traceback
            traceback.print_exc()

    def _update_ui_after_stop(self):
        """Update UI after stopping capture - runs in main thread"""
        try:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("捕获已停止")
            self.log("捕获已手动停止", "INFO")
        except Exception as e:
            self.log(f"更新停止状态失败: {e}", "ERROR")

    def on_device_discovered(self, device: LLDPDevice):
        """Callback when device discovered - runs in capture thread"""
        # 🔥 MINIMAL: Only emit signal - nothing else!
        # The QueuedConnection ensures this runs in the main thread, not here
        self.device_discovered.emit(device)

    def _on_device_discovered_ui(self, device: LLDPDevice):
        """UI update slot - runs in main thread, thread-safe"""
        try:
            # 🔥 暂停DEBUG日志处理，确保UI更新优先
            if self.debug_log_timer:
                self.debug_log_timer.stop()

            # Update device list first (in main thread)
            self.discovered_devices.append(device)
            self.current_device = device

            # Update UI display
            self.update_device_display(device)

            # Update device count
            count = len(self.discovered_devices)
            self.device_count_label.setText(f"已发现: {count} 台设备")
            self.log(f"设备已发现: {device.get_display_name()}", "SUCCESS")

            # 🔥 恢复DEBUG日志处理
            if self.debug_log_timer and self.debug_enabled:
                self.debug_log_timer.start(100)  # 改为100ms，降低优先级

        except Exception as e:
            self.log(f"UI更新失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()

    def on_capture_complete(self, devices: list):
        """Callback when capture completes - runs in capture thread"""
        device_count = len(devices)
        if device_count > 0:
            self.log(f"捕获完成，发现 {device_count} 台设备", "SUCCESS")
        else:
            self.log("捕获完成，未发现设备", "WARNING")
        print(f"[DEBUG] on_capture_complete called (capture thread)")
        self.is_capturing = False

        # Don't stop timer here - it will be stopped in main thread via signal

        # Emit signal to trigger UI update in main thread
        print(f"[DEBUG] Emitting capture_complete signal...")
        self.capture_complete.emit(devices)

    def _on_capture_complete_ui(self, devices: list):
        """UI update slot for capture complete - runs in main thread"""
        try:
            print(f"[DEBUG] _on_capture_complete_ui called (main thread)")

            # Stop progress timer in main thread
            if hasattr(self, 'progress_timer'):
                self.progress_timer.stop()

            self.capture_complete_update()
        except Exception as e:
            print(f"[ERROR] Capture complete UI update failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # 尝试基本的UI更新
            try:
                self.status_label.setText("捕获完成")
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
            except:
                pass

    def capture_complete_update(self):
        """Update UI after capture completes"""
        try:
            # 停止进度定时器
            if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
                self.progress_timer.stop()
                print("[DEBUG] Progress timer stopped", flush=True)

            self.progress_bar.setValue(100)
            self.status_label.setText("捕获完成")

            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

            if self.discovered_devices:
                self.export_btn.setEnabled(True)
        except Exception as e:
            print(f"[ERROR] capture_complete_update failed: {e}", flush=True)
            import traceback
            traceback.print_exc()

    def update_device_display(self, device):
        """Update device info cards - Clean architecture with ViewModel + PortProfile"""
        try:
            # Safety checks
            if not hasattr(self, 'sw_name') or not hasattr(self, 'protocol'):
                self.log("UI组件未就绪，跳过更新", "WARNING")
                return

            if device is None:
                self.log("设备对象为空，跳过更新", "WARNING")
                return

            # Convert to view model (clean separation)
            view = to_view(device)

            # 🔥 NEW: Port Semantic Profile Display (协议语义可视化)
            self.port_role.setText(view.port_role_summary)
            self.port_role.setStyleSheet(view.port_role_badge)

            # Log the inference
            self.log(f"端口角色推断: {view.port_profile}", "INFO")

            # Protocol
            self.protocol.setText(view.protocol)
            self.protocol.setStyleSheet(view.protocol_style)

            # Device Info
            self.sw_name.setText(view.system_name)
            self.sw_model.setText(view.device_model)
            self.sw_serial.setText(view.serial_number)
            self.sw_mac.setText(view.mac)
            self.sw_type.setText(view.id_type)
            self.sw_ip.setText(view.ip)
            self.sw_software.setText(view.software_version)
            self.lldp_med.setText(view.lldp_med)

            # Port Info
            self.port_id.setText(view.port_id)
            self.port_type.setText(view.port_type)
            self.port_desc.setText(view.port_desc)

            # VLAN
            self.port_vlan.setText(view.vlan)
            self.port_vlan.setStyleSheet(view.vlan_style)

            # Protocol VLAN
            self.protocol_vlan.setText(view.protocol_vlan)
            self.protocol_vlan.setStyleSheet(view.protocol_vlan_style)

            # Technical Info
            self.macphy.setText(view.macphy)
            self.link_agg.setText(view.link_agg)
            self.mtu.setText(view.mtu)
            self.poe.setText(view.poe)
            self.capabilities.setText(view.capabilities)

            # Update status
            status_text = f"已发现: {view.system_name}"
            self.status_label.setText(status_text)

            self.log("UI更新完成", "SUCCESS")

        except Exception as e:
            self.log(f"UI更新失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()

            try:
                self.sw_name.setText("显示错误")
                self.sw_mac.setText(str(e)[:50])
            except:
                pass
            # Device basic info - Enhanced for both LLDP and CDP
            if is_cdp:
                # CDP device properties
                cdp_device_id = getattr(device, 'device_id', None)
                cdp_system_name = getattr(device, 'system_name', None)
                cdp_platform = getattr(device, 'platform', None)

                # Display system name (priority) or device ID
                display_name = cdp_system_name or cdp_device_id or "未知CDP设备"
                print(f"[DEBUG] Setting sw_name to (CDP): {display_name}")
                self.sw_name.setText(display_name)

                # Display platform
                if cdp_platform:
                    print(f"[DEBUG] Setting sw_model to (CDP): {cdp_platform}")
                    self.sw_model.setText(cdp_platform)
                else:
                    self.sw_model.setText("未提供")

                # For CDP, we don't have chassis_id, use device_id or "N/A"
                self.sw_mac.setText("N/A (CDP协议)")
                self.sw_type.setText("CDP")

                # CDP doesn't typically provide serial number
                self.sw_serial.setText("未提供")

                # Software version for CDP
                cdp_sw_version = getattr(device, 'software_version', None)
                if cdp_sw_version:
                    print(f"[DEBUG] Setting sw_software to (CDP): {cdp_sw_version[:100]}")
                    self.sw_software.setText(cdp_sw_version[:100] + "..." if len(cdp_sw_version) > 100 else cdp_sw_version)
                else:
                    self.sw_software.setText("未提供")

                # CDP doesn't have LLDP-MED
                self.lldp_med.setText("N/A (CDP协议)")

                # Management addresses for CDP
                cdp_mgmt_addresses = getattr(device, 'management_addresses', None)
                if cdp_mgmt_addresses and len(cdp_mgmt_addresses) > 0:
                    # Get the first IPv4 address
                    ipv4_address = next((addr.address for addr in cdp_mgmt_addresses if addr.address_type == "IPv4"), None)
                    if ipv4_address:
                        print(f"[DEBUG] Setting sw_ip to (CDP): {ipv4_address}")
                        self.sw_ip.setText(ipv4_address)
                    else:
                        self.sw_ip.setText("未提供")
                else:
                    self.sw_ip.setText("未提供")

            else:
                # LLDP device properties (original logic)
                if device.chassis_id:
                    print(f"[DEBUG] Setting sw_mac to: {device.chassis_id.value}")
                    self.sw_mac.setText(device.chassis_id.value)
                    self.sw_type.setText(device.chassis_id.type.name)
                else:
                    self.sw_mac.setText("未提供")
                    self.sw_type.setText("未知")

                sys_name = device.system_name or "未知设备"
                print(f"[DEBUG] Setting sw_name to: {sys_name}")
                self.sw_name.setText(sys_name)

                # Device model (extracted from system description or private TLV)
                device_model = getattr(device, 'device_model', None) or getattr(device, 'product_model', None)
                if device_model:
                    print(f"[DEBUG] Setting sw_model to: {device_model}")
                    self.sw_model.setText(device_model)
                else:
                    # Fallback: try to extract from system description
                    if device.system_description:
                        desc_lines = device.system_description.split('\n')
                        for line in desc_lines:
                            if 'H3C' in line and 'Comware' not in line and len(line.strip()) > 10:
                                self.sw_model.setText(line.strip())
                                break
                        else:
                            self.sw_model.setText("未提供")
                    else:
                        self.sw_model.setText("未提供")

                # Serial number
                serial_number = getattr(device, 'serial_number', None)
                if serial_number:
                    print(f"[DEBUG] Setting sw_serial to: {serial_number}")
                    self.sw_serial.setText(serial_number)
                else:
                    self.sw_serial.setText("未提供")

                # Software version
                software_version = getattr(device, 'software_version', None)
                if software_version:
                    print(f"[DEBUG] Setting sw_software to: {software_version}")
                    self.sw_software.setText(software_version)
                else:
                    self.sw_software.setText("未提供")

                # Management address (IP)
                mgmt_ip = device.management_ip or "未提供"
                print(f"[DEBUG] Setting sw_ip to: {mgmt_ip}")
                self.sw_ip.setText(mgmt_ip)

                # LLDP-MED capabilities (only for LLDP)
                lldp_med_caps = getattr(device, 'lldp_med_capabilities', None)
                if lldp_med_caps and lldp_med_caps.get('capabilities'):
                    med_text = " / ".join(lldp_med_caps['capabilities'])
                    print(f"[DEBUG] Setting lldp_med to: {med_text}")
                    self.lldp_med.setText(med_text)
                else:
                    self.lldp_med.setText("未提供")

            # Port info - Enhanced for both LLDP and CDP
            if is_cdp:
                # CDP port info
                cdp_port_id = getattr(device, 'port_id', None)
                if cdp_port_id:
                    print(f"[DEBUG] Setting port_id to (CDP): {cdp_port_id}")
                    self.port_id.setText(cdp_port_id)
                else:
                    self.port_id.setText("未提供")

                self.port_type.setText("CDP端口标识")

                # CDP typically doesn't provide port description
                self.port_desc.setText("未提供")

            else:
                # LLDP port info (original logic)
                if device.port_id:
                    print(f"[DEBUG] Setting port_id to: {device.port_id.value}")
                    self.port_id.setText(device.port_id.value)
                    self.port_type.setText(device.port_id.type.name)
                else:
                    self.port_id.setText("未提供")
                    self.port_type.setText("未知")

                port_desc = device.port_description or "未知"
                print(f"[DEBUG] Setting port_desc to: {port_desc}")
                self.port_desc.setText(port_desc)

            # VLAN - Enhanced with CDP Native VLAN support!
            if is_cdp:
                # CDP device: Check for Native VLAN
                native_vlan = getattr(device, 'native_vlan', None)
                if native_vlan:
                    vlan_text = f"{native_vlan} (Native VLAN)"
                    self.port_vlan.setText(vlan_text)
                    # Highlight Native VLAN - this is the key info from CDP!
                    self.port_vlan.setStyleSheet("color:#10b981; font-weight:700; background:#d1fae5; padding:4px; border-radius:4px;")
                    print(f"[DEBUG] 🔥🔥🔥 CDP Native VLAN displayed: {native_vlan}")
                else:
                    self.port_vlan.setText("未提供")
                    self.port_vlan.setStyleSheet("")
            else:
                # LLDP device: Check multiple VLAN sources
                vlan_found = False

                # Priority 1: H3C private TLV (high confidence)
                h3c_vlan = getattr(device, 'h3c_native_vlan', None)
                if h3c_vlan:
                    vlan_text = f"{h3c_vlan} (H3C私有TLV)"
                    self.port_vlan.setText(vlan_text)
                    self.port_vlan.setStyleSheet("color:#f59e0b; font-weight:600; background:#fef3c7; padding:4px; border-radius:4px;")
                    print(f"[DEBUG] 🔥 H3C Private TLV VLAN displayed: {h3c_vlan}")
                    vlan_found = True

                # Priority 2: Standard LLDP port VLAN
                elif device.port_vlan:
                    vlan_text = f"{device.port_vlan.vlan_id}"

                    # 添加VLAN名称（如果有）
                    if hasattr(device.port_vlan, 'vlan_name') and device.port_vlan.vlan_name:
                        vlan_text += f" ({device.port_vlan.vlan_name})"
                    elif hasattr(device, 'vlans') and device.vlans:
                        # 如果port_vlan没有vlan_name，从vlans列表中查找
                        for v in device.vlans:
                            if hasattr(v, 'vlan_id') and v.vlan_id == device.port_vlan.vlan_id:
                                if hasattr(v, 'vlan_name') and v.vlan_name:
                                    vlan_text += f" ({v.vlan_name})"
                                    print(f"[DEBUG] Found VLAN name from vlans list: {v.vlan_name}")
                                    break

                    if hasattr(device.port_vlan, 'tagged') and device.port_vlan.tagged:
                        vlan_text += " (Tagged)"
                    else:
                        vlan_text += " (Untagged)"

                    self.port_vlan.setText(vlan_text)
                    self.port_vlan.setStyleSheet("color:#22c55e; font-weight:600; background:#dcfce7; padding:4px; border-radius:4px;")
                    print(f"[DEBUG] LLDP VLAN displayed: {vlan_text}")
                    vlan_found = True

                if not vlan_found:
                    self.port_vlan.setText("未提供")
                    self.port_vlan.setStyleSheet("")

            # 协议VLAN ID (Protocol VLAN) - 新增
            if hasattr(device, 'protocol_vlan_id') and device.protocol_vlan_id:
                self.protocol_vlan.setText(f"{device.protocol_vlan_id}")
                self.protocol_vlan.setStyleSheet("color:#8b5cf6; font-weight:600; background:#f3e8ff; padding:4px; border-radius:4px;")
                print(f"[DEBUG] Protocol VLAN displayed: {device.protocol_vlan_id}")
            else:
                self.protocol_vlan.setText("未提供")
                self.protocol_vlan.setStyleSheet("")

            # MAC/PHY Configuration
            if hasattr(device, 'macphy_config') and device.macphy_config:
                macphy = device.macphy_config
                if macphy.supported_speeds:
                    # Display all supported speeds
                    speeds_text = " / ".join(macphy.supported_speeds)
                    self.macphy.setText(speeds_text)
                elif macphy.speed:
                    # Fallback to current speed if no supported list
                    phy_text = f"{macphy.speed}"
                    if macphy.duplex:
                        phy_text += f" {macphy.duplex}"
                    self.macphy.setText(phy_text)
                elif device.autonegotiation and device.autonegotiation.get('supported'):
                    self.macphy.setText("自动协商")
                else:
                    self.macphy.setText("未提供")
            else:
                self.macphy.setText("未提供")

            # Link Aggregation
            if hasattr(device, 'link_aggregation') and device.link_aggregation:
                link_agg = device.link_aggregation
                if not link_agg.supported:
                    self.link_agg.setText("不支持")
                elif link_agg.enabled:
                    agg_text = "已启用"
                    if link_agg.aggregation_id:
                        agg_text += f" (组ID: {link_agg.aggregation_id})"
                    self.link_agg.setText(agg_text)
                else:
                    self.link_agg.setText("支持")
            else:
                self.link_agg.setText("未提供")

            # Maximum Frame Size (MTU)
            if device.max_frame_size:
                mtu_text = f"{device.max_frame_size} 字节"
                self.mtu.setText(mtu_text)
            else:
                self.mtu.setText("未提供")

            # PoE
            if hasattr(device, 'poe') and device.poe and device.poe.supported:
                poe_parts = []

                # 电源类型
                if device.poe.power_source:
                    if 'PSE' in device.poe.power_source:
                        poe_parts.append("供电设备")
                    elif 'PD' in device.poe.power_source:
                        poe_parts.append("受电设备")

                # 功率信息
                if device.poe.power_allocated:
                    power_w = device.poe.power_allocated / 1000
                    if power_w >= 1:
                        poe_parts.append(f"{power_w:.1f}W")
                    else:
                        poe_parts.append(f"{device.poe.power_allocated}mW")

                # 优先级
                if device.poe.power_priority:
                    poe_parts.append(f"优先级:{device.poe.power_priority}")

                # 类型和等级
                if device.poe.power_class:
                    poe_parts.append(f"({device.poe.power_class})")
                if device.poe.power_type:
                    poe_parts.append(f"[{device.poe.power_type}]")

                self.poe.setText(" / ".join(poe_parts))
            else:
                self.poe.setText("不支持")

            # Capabilities - 显示所有支持的能力
            if hasattr(device, 'capabilities') and device.capabilities:
                all_caps = device.capabilities.get_all_capabilities()
                print(f"[DEBUG UI] All capabilities to display: {all_caps}")
                if all_caps:
                    cap_text = " / ".join(all_caps)
                    self.capabilities.setText(cap_text)
                    print(f"[DEBUG UI] Set capabilities text to: {cap_text}")
                else:
                    self.capabilities.setText("未知")
                    print(f"[DEBUG UI] No capabilities found, showing '未知'")
            else:
                self.capabilities.setText("未知")
                print(f"[DEBUG UI] No capabilities object, showing '未知'")

            # Update status
            status_text = f"已发现: {device.get_display_name()}"
            print(f"[DEBUG] Setting status_label to: {status_text}")
            self.status_label.setText(status_text)

            print(f"[DEBUG] UI update completed successfully")

        except Exception as e:
            print(f"[ERROR] Failed to update display: {e}")
            import traceback
            traceback.print_exc()

            # 🔥 安全的错误显示，防止二次崩溃
            try:
                self.sw_name.setText("显示错误")
                self.sw_mac.setText(str(e)[:50])
                self.log(f"UI更新失败: {str(e)}", "ERROR")
            except Exception as e2:
                print(f"[ERROR] Even error display failed: {e2}")
                # 最后的错误记录
                with open("lldp_ui_error.txt", "a", encoding="utf-8") as f:
                    f.write(f"UI Update Error: {e}\n")
                    f.write(f"Error Display Error: {e2}\n")
                    traceback.print_exc(file=f)

    def update_progress(self):
        """Update progress bar - Optimized for minimal CPU usage"""
        try:
            if self.is_capturing:
                if self.capture_start_time == 0:
                    from time import time
                    self.capture_start_time = time()

                from time import time
                elapsed = time() - self.capture_start_time

                # 修正：捕获时长是60秒（支持LLDP/CDP），不是30秒
                progress = min(int((elapsed / 60) * 100), 100)
                self.progress_bar.setValue(progress)

                # 简单的剩余时间显示
                remaining = max(0, 60 - elapsed)
                if remaining > 0:
                    self.status_label.setText(f"捕获中... 剩余 {int(remaining)}s")
                else:
                    self.status_label.setText("捕获中... 即将完成")
        except Exception as e:
            # Silently ignore progress update errors to prevent spam
            pass

    def export_data(self):
        """Export discovered devices"""
        if not self.discovered_devices:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return

        from PyQt6.QtWidgets import QFileDialog
        import json
        from datetime import datetime

        # Ask for save location and format
        file_filter = "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出LLDP设备信息",
            f"lldp_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            file_filter
        )

        if not file_path:
            return

        try:
            # Export based on file extension
            if file_path.endswith('.json'):
                self._export_json(file_path)
            elif file_path.endswith('.csv'):
                self._export_csv(file_path)
            else:
                self._export_text(file_path)

            QMessageBox.information(self, "成功",
                                    f"成功导出 {len(self.discovered_devices)} 台设备到:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def _export_json(self, file_path: str):
        """Export to JSON format - using ViewModel with PortProfile"""
        data = {
            'export_time': datetime.now().isoformat(),
            'device_count': len(self.discovered_devices),
            'devices': []
        }

        for device in self.discovered_devices:
            view = to_view(device)
            device_data = {
                # 🔥 NEW: Port Semantic Profile
                'port_role': view.port_profile.role.value,
                'port_confidence': view.port_profile.confidence,
                'port_reasons': view.port_profile.reasons,
                # Original fields
                'system_name': view.system_name,
                'mac': view.mac,
                'port_id': view.port_id,
                'vlan': view.vlan,
                'macphy': view.macphy,
                'link_agg': view.link_agg,
                'mtu': view.mtu,
                'poe': view.poe,
                'capabilities': view.capabilities,
                'protocol': view.protocol,
                'ip': view.ip,
                'device_model': view.device_model,
                'capture_interface': safe_get(device, 'capture_interface')
            }
            data['devices'].append(device_data)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _export_csv(self, file_path: str):
        """Export to CSV format - using ViewModel with PortProfile"""
        import csv

        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)

            # 🔥 NEW: Header with port role
            writer.writerow([
                '端口角色', '置信度', '推断依据',
                '系统名称', '设备MAC', '端口ID', '端口描述',
                '管理IP', 'VLAN', '速率/双工', '链路聚合', '最大帧长', 'PoE', '系统描述'
            ])

            # Data rows - using ViewModel
            for device in self.discovered_devices:
                view = to_view(device)

                writer.writerow([
                    # 🔥 NEW: Port Semantic Profile
                    view.port_profile.role.value,
                    f"{view.port_profile.confidence}%",
                    " / ".join(view.port_profile.reasons),
                    # Original fields
                    view.system_name,
                    view.mac,
                    view.port_id,
                    view.port_desc,
                    view.ip,
                    view.vlan,
                    view.macphy,
                    view.link_agg,
                    view.mtu,
                    view.poe,
                    (safe_get(device, 'system_description') or '—')[:30]
                ])

    def _export_text(self, file_path: str):
        """Export to formatted text - using ViewModel with PortProfile"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("LLDP设备发现报告 - 端口语义推断\n")
            f.write("="*70 + "\n\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"设备数量: {len(self.discovered_devices)}\n\n")

            for i, device in enumerate(self.discovered_devices, 1):
                view = to_view(device)

                f.write("-"*70 + "\n")
                f.write(f"设备 #{i}\n")
                f.write("-"*70 + "\n")

                # 🔥 NEW: Port Semantic Profile
                f.write(f"【端口角色】{view.port_profile.role.value}\n")
                f.write(f"【置信度】{view.port_profile.confidence}%\n")
                f.write(f"【推断依据】\n")
                for reason in view.port_profile.reasons:
                    f.write(f"  - {reason}\n")
                f.write("\n")

                # Device Info
                f.write(f"系统名称: {view.system_name}\n")
                f.write(f"设备MAC: {view.mac}\n")
                f.write(f"端口ID: {view.port_id}\n")
                f.write(f"端口描述: {view.port_desc}\n")
                f.write(f"管理IP: {view.ip}\n")
                f.write(f"速率/双工: {view.macphy}\n")
                f.write(f"链路聚合: {view.link_agg}\n")
                f.write(f"最大帧长: {view.mtu}\n")
                f.write(f"VLAN: {view.vlan}\n")
                f.write(f"PoE: {view.poe}\n")
                f.write(f"设备能力: {view.capabilities}\n")
                f.write("\n")

    def closeEvent(self, event):
        """Window close event - cleanup resources"""
        try:
            # Stop DEBUG log timer
            if hasattr(self, 'debug_log_timer') and self.debug_log_timer:
                self.debug_log_timer.stop()

            # Stop capture
            if hasattr(self, 'listener') and self.listener:
                self.listener.stop()

            # Stop progress timer
            if hasattr(self, 'progress_timer') and self.progress_timer:
                self.progress_timer.stop()

            event.accept()
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")
            event.accept()


def main():
    """Main entry point"""
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        # 🔥 设置应用程序图标（任务栏和窗口标题栏）
        from PyQt6.QtGui import QIcon
        import os

        # 查找图标文件（支持开发环境和打包后环境）
        meipass = getattr(sys, '_MEIPASS', '')
        icon_paths = [
            # 开发环境：使用相对路径
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lldp_icon.png'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lldp_icon.ico'),
            # 打包后：在sys._MEIPASS中查找
            os.path.join(meipass, 'lldp_icon.png'),
            os.path.join(meipass, 'lldp_icon.ico'),
            # 当前目录
            'lldp_icon.png',
            'lldp_icon.ico',
        ]

        icon_loaded = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    app_icon = QIcon(icon_path)
                    app.setWindowIcon(app_icon)
                    icon_loaded = True
                    break
                except Exception as e:
                    continue

        if not icon_loaded:
            # 如果图标文件不存在，使用默认图标
            pass

        # 🔥 添加全局异常处理器，防止程序静默崩溃
        def handle_exception(exc_type, exc_value, exc_traceback):
            """全局异常处理器"""
            import traceback
            import datetime

            # 保存错误信息到文件
            error_log = f"lldp_analyzer_crash_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                with open(error_log, 'w', encoding='utf-8') as f:
                    f.write(f"LLDP Analyzer Crash Report\n")
                    f.write(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Error Type: {exc_type.__name__}\n")
                    f.write(f"Error Message: {exc_value}\n")
                    f.write(f"\n=== Traceback ===\n")
                    traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
                print(f"[CRITICAL] Program crashed! Error saved to: {error_log}")
            except:
                pass

            # 显示错误对话框
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "程序崩溃",
                    f"程序遇到严重错误:\n\n"
                    f"{exc_type.__name__}: {exc_value}\n\n"
                    f"错误信息已保存到:\n{error_log}\n\n"
                    f"请将此文件发送给开发者进行分析。"
                )
            except:
                pass

        # 安装全局异常处理器
        sys.excepthook = handle_exception

        print("[DEBUG] Creating LLDP Professional Window...")
        window = LLDPProfessionalWindow()
        print("[DEBUG] Window created successfully")
        print("[DEBUG] Showing window...")
        window.show()
        print("[DEBUG] Window shown, starting event loop...")

        sys.exit(app.exec())
    except Exception as e:
        print(f"[FATAL ERROR] Main application error: {e}", flush=True)
        import traceback
        traceback.print_exc()

        # 🔥 保存错误信息
        try:
            import datetime
            error_log = f"lldp_analyzer_fatal_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"FATAL ERROR: {e}\n")
                traceback.print_exc(file=f)
            print(f"Error saved to: {error_log}")
        except:
            pass

        # 🔥 在GUI环境中显示错误对话框
        try:
            # 检查是否已经有QApplication实例
            app_instance = QApplication.instance()
            if app_instance is None:
                # 创建临时QApplication来显示错误对话框
                temp_app = QApplication(sys.argv)
                QMessageBox.critical(None, "严重错误", f"程序启动失败:\n\n{str(e)}\n\n错误信息已保存到日志文件。")
                del temp_app  # 删除临时实例
            else:
                # 使用已有的QApplication实例
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(None, "严重错误", f"程序启动失败:\n\n{str(e)}\n\n错误信息已保存到日志文件。")
        except:
            print("无法显示错误对话框，程序将退出。")
        sys.exit(1)


if __name__ == "__main__":
    main()
