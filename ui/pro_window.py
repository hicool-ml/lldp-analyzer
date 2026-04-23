"""
LLDP Network Analyzer - Professional UI with PyQt6
Modern card-based design with clean architecture
"""

import sys
import os
from typing import Optional
import io
from datetime import datetime
import json  #  Required for export functions
import csv   #  Required for CSV export
from collections import deque  # 优化: 高效队列管理
from pathlib import Path  # 优化C: 跨平台路径处理

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
    QProgressBar, QMessageBox, QTextEdit, QPlainTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QTextCharFormat, QColor

# Import from clean architecture
from lldp import LLDPCaptureListener
from lldp.model import LLDPDevice
from lldp.cdp.model import CDPDevice
from lldp.port_profile import PortRole, NetworkIntent, PortIntentProfile, infer_port_intent
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
        # Set minimum size to prevent text cutoff
        self.setMinimumWidth(250)
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
        # Ensure text doesn't get cut off
        label_value.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        label_value.setWordWrap(False)

        # Set stretch factors to prevent text cutoff
        row.addWidget(label_name, 1)  # Name gets 1/4 space
        row.addWidget(label_value, 3)  # Value gets 3/4 space
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
    debug_log = pyqtSignal(str)  #  新增：DEBUG日志信号

    class InterfaceScannerThread(QThread):
        """
        异步网卡扫描线程 - 避免UI冻结

        优化B: 将耗时的网卡扫描操作移到后台线程
        """
        finished = pyqtSignal(list)  # 信号：扫描完成，返回有效接口列表

        def run(self):
            """执行网卡扫描 - 在后台线程中运行"""
            try:
                from scapy.all import get_working_ifaces

                print(f"[DEBUG] ===== Async Interface Scanning Started =====", flush=True)

                all_interfaces = list(get_working_ifaces())
                valid_interfaces = []

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
                        valid_interfaces.append(iface)
                        print(f"[DEBUG] Added interface: {iface.description} ({iface.name})", flush=True)

                print(f"[DEBUG] Async scanning found {len(valid_interfaces)} valid interfaces", flush=True)
                print(f"[DEBUG] ===== Async Interface Scanning Complete =====", flush=True)

                # 发出完成信号，传递有效接口列表
                self.finished.emit(valid_interfaces)

            except Exception as e:
                print(f"[ERROR] Async interface scanning failed: {e}", flush=True)
                import traceback
                traceback.print_exc()
                # 发出空列表表示失败
                self.finished.emit([])

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLDP Network Analyzer v2.0 - Semantic Inference Engine")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("background-color:#0f172a; font-family:'Segoe UI Variable','Microsoft YaHei UI';")

        #  设置窗口图标
        self._set_window_icon()

        # Core components (clean architecture)
        self.listener = None
        self.current_device: Optional[LLDPDevice] = None
        self.discovered_devices = []

        # Build UI
        self.setup_ui()

        # Logging configuration
        self.log_buffer = []
        self.debug_enabled = False
        self.debug_log_queue = deque(maxlen=1000)  # 优化: 使用deque避免内存问题
        self.debug_log_timer = None

        # Setup logging
        self.setup_logging()

        # Setup DEBUG output capture
        self.setup_debug_capture()

        # Connect DEBUG log signal
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
        # CRITICAL: Use QueuedConnection to ensure slots run in main thread, not capture thread
        self.log("连接基础信号槽...", "DEBUG")
        self.device_discovered.connect(self._on_device_discovered_ui, Qt.ConnectionType.QueuedConnection)
        self.capture_complete.connect(self._on_capture_complete_ui, Qt.ConnectionType.QueuedConnection)
        self.log("基础信号槽连接完成", "DEBUG")

    def _set_window_icon(self):
        """
        🔥 Set window icon from file (Enhanced with Windows taskbar support)

        优化C: 使用pathlib.Path进行跨平台路径处理
        注意: AppUserModelID已在main()中在QApplication创建前设置
        """
        from PyQt6.QtGui import QIcon

        # 查找图标文件 - 使用pathlib.Path
        meipass = getattr(sys, '_MEIPASS', '')
        current_dir = Path(__file__).parent.parent

        icon_paths = [
            # 开发环境：使用相对路径
            current_dir / 'lldp_icon.png',
            current_dir / 'lldp_icon.ico',
            # 打包后：在sys._MEIPASS中查找
            Path(meipass) / 'lldp_icon.png',
            Path(meipass) / 'lldp_icon.ico',
            # 当前目录
            Path('lldp_icon.png'),
            Path('lldp_icon.ico'),
        ]

        for icon_path in icon_paths:
            if icon_path.exists():
                try:
                    icon = QIcon(str(icon_path))  # QIcon需要字符串路径
                    self.setWindowIcon(icon)
                    print(f"[DEBUG] ✅ Window icon loaded: {icon_path}")
                    return
                except Exception as e:
                    print(f"[WARNING] Failed to load icon {icon_path}: {e}")
                    continue

        print(f"[WARNING] No icon file found, using default icon")

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

        # Connect debug_checkbox signal after UI creation
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

            #  Start debug log processing timer
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
                    #  线程安全：将日志放入队列，而不是直接调用UI方法
                    self.debug_log_queue.append(message)
                else:
                    self.original_print(*args, **kwargs)

            builtins.print = custom_print
            self.log("详细DEBUG日志已启用", "INFO")
        else:  # Unchecked
            self.debug_enabled = False
            builtins.print = self.original_print

            #  Stop debug log processing timer
            if self.debug_log_timer:
                self.debug_log_timer.stop()
                self.debug_log_timer = None

            # 清空队列
            self.debug_log_queue.clear()

            self.log("详细DEBUG日志已禁用", "INFO")

    def _process_debug_log_queue(self):
        """
        处理DEBUG日志队列 - 在主线程中执行

        修复: 使用deque避免逻辑错误，提高性能
        """
        if not self.debug_log_queue:
            return

        #  优化：限制DEBUG日志显示，防止阻塞UI
        max_display = 100  # 最多显示100条DEBUG日志
        current_count = len(self.debug_log_queue)

        # 如果队列太大，直接清空多余部分
        if current_count > max_display:
            # 使用log方法而不是log_raw，因为log支持level参数
            self.log(f"DEBUG日志过多（{current_count}条），已自动清理", "WARNING")
            # deque会自动管理maxlen，这里只需要处理多余的元素
            excess = current_count - 50
            for _ in range(excess):
                if self.debug_log_queue:
                    self.debug_log_queue.popleft()

        # 批量处理，每次最多5条，避免阻塞UI
        batch_size = 5
        processed = 0

        while self.debug_log_queue and processed < batch_size:
            # 修复: 使用popleft()而不是pop(0)，deque的popleft()是O(1)操作
            message = self.debug_log_queue.popleft()

            #  只显示重要的DEBUG日志，过滤掉详细的数据包解析
            if any(keyword in message for keyword in [
                'Device found', 'VLAN:', 'H3C Private TLV',
                '已发现', '完成', 'SUCCESS', 'ERROR', 'WARNING'
            ]):
                self.log_raw(message)
            elif '[DEBUG] Processed' in message:
                # 每100个包显示一次进度
                self.log_raw(message)

            processed += 1

    def _on_debug_log_ui(self, message: str):
        """DEBUG日志UI更新槽 - 在主线程中执行"""
        self.log_raw(message)

    def log(self, message: str, level: str = "INFO"):
        """Add log message to the log display - Performance optimized with QPlainTextEdit"""
        import datetime

        #  安全检查：debug_checkbox可能还未初始化
        if hasattr(self, 'debug_checkbox') and level == "DEBUG":
            if not self.debug_checkbox.isChecked():
                return  # Skip DEBUG messages unless checkbox is checked

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        #  添加到日志缓冲区（用于自动保存）
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_buffer.append(log_entry)

        #  性能优化：使用QTextCharFormat而不是HTML
        color_map = {
            "INFO": "#94a3b8",
            "DEBUG": "#f59e0b",
            "SUCCESS": "#22c55e",
            "WARNING": "#f59e0b",
            "ERROR": "#ef4444"
        }

        color_hex = color_map.get(level, "#94a3b8")
        formatted_message = f"[{timestamp}] {message}"

        # 使用QTextCharFormat进行高性能文本渲染
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        format = QTextCharFormat()
        format.setForeground(QColor(color_hex))

        cursor.insertText(formatted_message + "\n", format)

        #  节流优化：避免频繁滚动导致的UI卡顿
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:
            scrollbar.setValue(scrollbar.maximum())

    def log_raw(self, message: str):
        """Add raw DEBUG output ( for detailed packet parsing) - Performance optimized"""
        #  安全检查：确保UI组件存在且debug_checkbox已勾选
        if not hasattr(self, 'debug_checkbox') or not self.debug_checkbox.isChecked():
            return

        if not hasattr(self, 'log_text'):
            return

        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        #  性能优化：使用纯文本而不是HTML
        formatted_message = f"[{timestamp}] {message}"

        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)

        format = QTextCharFormat()
        format.setForeground(QColor("#64748b"))

        cursor.insertText(formatted_message + "\n", format)

        #  节流优化：限制滚动频率
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar.value() >= scrollbar.maximum() - 10:
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

        #  UX优化：添加网卡刷新按钮
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedWidth(40)
        refresh_btn.setToolTip("刷新网络适配器列表")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #f1f5f9;
                border: 1px solid #475569;
                border-radius: 4px;
                padding: 6px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: #475569;
                border: 1px solid #64748b;
            }
            QPushButton:pressed {
                background: #1e293b;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_interfaces)
        adapter_row.addWidget(refresh_btn)

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
        #  NEW: Port Semantic Profile (协议语义推断)
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
        self.port_role.setText("—")  # 初始状态
        self.port_role.setStyleSheet("color:#94a3b8; font-style:italic;")
        self.protocol.setText("—")
        self.protocol.setStyleSheet("color:#94a3b8; font-style:italic;")
        self.port_id.setText("—")
        self.port_id.setStyleSheet("color:#94a3b8; font-style:italic;")

        self.port_type.setText("—")
        self.port_desc.setText("—")
        self.port_vlan.setText("—")
        self.protocol_vlan.setText("—")
        self.macphy.setText("—")
        self.link_agg.setText("—")
        self.mtu.setText("—")
        self.poe.setText("—")
        self.capabilities.setText("—")
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

        title = QLabel("运行日志")
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
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        #  性能优化：限制最大行数，防止内存溢出和UI卡顿
        self.log_text.setMaximumBlockCount(200)  # 降低到200行，提升性能
        self.log_text.setStyleSheet("""
            QPlainTextEdit {
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
        """
        Refresh network adapter list - 异步版本避免UI冻结

        优化B: 使用后台线程进行网卡扫描，避免UI冻结
        """
        try:
            # 显示扫描状态
            self.adapter_combo.clear()
            self.interfaces = []
            self.status_label.setText("正在扫描网络适配器...")
            self.start_btn.setEnabled(False)
            self.log("开始异步扫描网络接口...", "DEBUG")

            # 创建并启动扫描线程
            self.interface_scanner = self.InterfaceScannerThread()
            self.interface_scanner.finished.connect(self._on_interface_scan_complete)
            self.interface_scanner.start()

        except Exception as e:
            print(f"[ERROR] Interface scan failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: 无法扫描网络适配器")
            QMessageBox.critical(self, "严重错误", f"无法扫描网络适配器！\n\n错误信息: {e}")

    def _on_interface_scan_complete(self, valid_interfaces):
        """
        网卡扫描完成回调 - 在主线程中执行

        Args:
            valid_interfaces: 扫描到的有效网卡列表
        """
        try:
            # 更新接口列表
            self.interfaces = valid_interfaces

            # 清空并重新填充下拉菜单
            self.adapter_combo.clear()

            # 添加找到的接口
            for iface in valid_interfaces:
                display_text = f"{iface.description} ({iface.name})"
                self.adapter_combo.addItem(display_text, iface)
                self.log(f"添加网卡: {display_text}", "DEBUG")

            self.log(f"异步扫描完成，找到 {len(self.interfaces)} 个有效网卡", "SUCCESS")

            if self.interfaces:
                self.start_btn.setEnabled(True)
                self.status_label.setText(f"找到 {len(self.interfaces)} 个网络适配器")

                # 优化4: 自动选择最佳网卡
                self._auto_select_best_interface()
            else:
                self.start_btn.setEnabled(False)
                self.status_label.setText("未找到合适的网络适配器")
                self.log("未找到合适的网络适配器", "WARNING")
                QMessageBox.warning(self, "网络接口问题",
                    "未找到合适的网络适配器！\n\n"
                    "可能的原因：\n"
                    "1. 没有安装Npcap驱动\n"
                    "2. 没有物理网络连接\n"
                    "3. 网络适配器被禁用\n\n"
                    "请检查网络连接后重试。")

        except Exception as e:
            print(f"[ERROR] Interface scan callback failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: 网卡扫描处理失败")

        except Exception as e:
            print(f"[DEBUG] Error scanning interfaces: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: 无法扫描网络适配器")
            QMessageBox.critical(self, "严重错误", f"无法扫描网络适配器！\n\n错误信息: {e}")

    def _auto_select_best_interface(self):
        """
        自动选择最佳网络接口

        优化: 基于启发式规则选择最可能的LLDP设备连接口
        优先级: 有IP > 知名厂商 > 标准命名 > 第一个
        """
        if not self.interfaces:
            return

        best_interface = None
        best_score = -1

        for iface in self.interfaces:
            score = 0
            reasons = []

            # 评分规则1: 有IP地址（说明网络已连接）
            if hasattr(iface, 'ip') and iface.ip:
                score += 100
                reasons.append(f"有IP({iface.ip})")

            # 评分规则2: 知名网卡制造商（更可能是物理连接）
            desc_lower = iface.description.lower()
            if any(brand in desc_lower for brand in ['intel', 'realtek', 'broadcom', 'qualcomm']):
                score += 50
                reasons.append("知名厂商")

            # 评分规则3: 标准以太网命名
            if 'ethernet' in desc_lower or '以太网' in desc_lower:
                score += 30
                reasons.append("标准以太网")

            # 评分规则4: 避免测试/调试接口
            if any(test_term in desc_lower for test_term in ['test', 'debug', 'virtual', 'loopback']):
                score -= 100
                reasons.append("测试接口(扣分)")

            # 评分规则5: 接口命名优先级
            name_lower = iface.name.lower()
            if name_lower in ['eth0', 'en0', 'eth1']:  # Linux/macOS主网口
                score += 20
                reasons.append("主网口命名")
            elif name_lower.startswith('eth') or name_lower.startswith('en'):
                score += 10
                reasons.append("标准命名")

            # 评分规则6: PCI接口（通常是物理网卡）
            if 'pci' in desc_lower:
                score += 15
                reasons.append("PCI接口")

            print(f"[DEBUG] Interface {iface.name} scored {score}: {', '.join(reasons)}")

            if score > best_score:
                best_score = score
                best_interface = iface

        # 选择得分最高的接口
        if best_interface:
            index = self.interfaces.index(best_interface)
            self.adapter_combo.setCurrentIndex(index)

            selection_reasons = []
            if hasattr(best_interface, 'ip') and best_interface.ip:
                selection_reasons.append(f"已配置IP: {best_interface.ip}")
            if best_score > 50:
                selection_reasons.append("知名厂商或标准命名")

            reason_text = "，".join(selection_reasons) if selection_reasons else "默认选择"
            self.log(f"自动选择网卡: {best_interface.description} ({reason_text})", "SUCCESS")
            print(f"[DEBUG] Auto-selected: {best_interface.description} (score: {best_score})")
        else:
            # 如果没有最佳选择，默认选择第一个
            self.adapter_combo.setCurrentIndex(0)
            self.log(f"使用默认网卡: {self.interfaces[0].description}", "INFO")

    def start_capture(self):
        """Start LLDP capture"""
        #  UX优化：立即禁用按钮，防止双击
        self.start_btn.setEnabled(False)
        self.start_btn.repaint()  # 强制重绘，确保UI立即更新

        print(f"[DEBUG] ===== start_capture called =====", flush=True)

        if not hasattr(self, 'interfaces') or not self.interfaces:
            print(f"[DEBUG] No interfaces available!", flush=True)
            QMessageBox.warning(self, "警告", "请先选择网络适配器！\n\n没有找到可用的网络适配器。")
            return

        print(f"[DEBUG] Available interfaces: {len(self.interfaces)}", flush=True)

        # Get selected interface
        current_data = self.adapter_combo.currentData()
        if not current_data:
            self.log("没有选择网络适配器", "ERROR")
            print(f"[DEBUG] No interface selected!", flush=True)
            QMessageBox.warning(self, "警告", "请选择一个网络适配器！")
            return

        interface = current_data
        self.log(f"选择网卡: {interface.description}", "INFO")
        print(f"[DEBUG] Selected interface: {interface.description} ({interface.name})", flush=True)
        print(f"[DEBUG] Starting capture on: {interface.description}", flush=True)

        # 物理链路检查 - 避免盲目捕获
        print(f"[DEBUG] Checking physical link status...", flush=True)
        has_ip = hasattr(interface, 'ip') and interface.ip is not None

        if has_ip:
            self.log(f"网卡IP: {interface.ip} - 链路正常", "SUCCESS")
            print(f"[DEBUG] Interface has IP: {interface.ip}", flush=True)
            print(f"[DEBUG] Physical link appears to be UP", flush=True)
        else:
            self.log(f"网卡无IP地址 - 链路可能未连接", "WARNING")
            print(f"[DEBUG] Interface has NO IP address!", flush=True)
            print(f"[DEBUG] Physical link might be DOWN!", flush=True)

            # 弹出警告对话框
            reply = QMessageBox.question(
                self,
                "物理链路警告",
                f"选中网卡没有IP地址，可能物理链路未连接：\n\n"
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
            print(f"[DEBUG] STARTING CAPTURE PROCESS", flush=True)
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

        except PermissionError as e:
            # 优化: 专门处理权限错误
            error_msg = f"网络访问权限不足:\n\n{str(e)}\n\n" \
                      f"请尝试以下解决方案:\n" \
                      f"1. 以管理员身份运行程序\n" \
                      f"2. 检查防火墙设置\n" \
                      f"3. 检查杀毒软件是否拦截\n" \
                      f"4. 关闭其他可能占用网卡的工具"
            self.log(f"权限错误: {e}", "ERROR")
            print(f"[ERROR] Permission denied: {e}")
            QMessageBox.critical(self, "权限错误", error_msg)
            self.capture_complete_update()

        except OSError as e:
            # 优化: 处理系统级网络错误
            if "Operation not permitted" in str(e) or "Permission denied" in str(e):
                error_msg = f"网络访问被拒绝:\n\n{str(e)}\n\n" \
                          f"请尝试以下解决方案:\n" \
                          f"1. 以管理员身份运行程序\n" \
                          f"2. 检查网络适配器状态\n" \
                          f"3. 重启网络服务"
            elif "No such device" in str(e) or "does not exist" in str(e):
                error_msg = f"网络适配器不存在:\n\n{str(e)}\n\n" \
                          f"请检查:\n" \
                          f"1. 网卡是否被禁用\n" \
                          f"2. 网卡驱动是否正常\n" \
                          f"3. 网线是否连接"
            else:
                error_msg = f"系统网络错误:\n\n{str(e)}"

            self.log(f"系统错误: {e}", "ERROR")
            print(f"[ERROR] OS Error: {e}")
            QMessageBox.critical(self, "系统错误", error_msg)
            self.capture_complete_update()

        except Exception as e:
            # 通用错误处理
            import traceback
            error_details = traceback.format_exc()
            self.log(f"捕获启动失败: {e}", "ERROR")
            print(f"[ERROR] Capture failed: {e}")
            print(f"[DEBUG] Traceback:\n{error_details}")

            # 向用户显示友好的错误信息
            user_friendly_msg = f"捕获启动失败:\n\n{str(e)}\n\n" \
                              f"技术详情已记录到日志文件"
            QMessageBox.critical(self, "启动失败", user_friendly_msg)
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
        #  MINIMAL: Only emit signal - nothing else!
        # The QueuedConnection ensures this runs in the main thread, not here
        self.device_discovered.emit(device)

    def _on_device_discovered_ui(self, device):
        """UI update slot - runs in main thread, thread-safe"""
        try:
            #  暂停DEBUG日志处理，确保UI更新优先
            if self.debug_log_timer:
                self.debug_log_timer.stop()

            # Determine device type
            is_cdp = isinstance(device, CDPDevice)
            is_lldp = isinstance(device, LLDPDevice)

            # Update device list first (in main thread)
            self.discovered_devices.append(device)
            self.current_device = device

            # Update UI display (MVVM架构：不需要协议类型参数)
            self.update_device_display(device)

            # Update device count
            count = len(self.discovered_devices)
            self.device_count_label.setText(f"已发现: {count} 台设备")
            self.log(f"设备已发现: {device.get_display_name()}", "SUCCESS")

            #  恢复DEBUG日志处理
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
        """
        Update device info cards - 彻底解耦架构

        架构原则: UI层不应该有任何协议判断逻辑
        所有的协议差异化（LLDP vs CDP）都在to_view()中处理
        """
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

            #  NEW: Port Intent Profile Display (网络意图可视化)
            self.port_role.setText(view.port_role_summary)
            self.port_role.setStyleSheet(view.port_role_badge)

            #  UX优化：让端口角色可点击查看推断依据
            self.port_role.setCursor(Qt.CursorShape.PointingHandCursor)
            # 使用lambda闭包保存当前设备引用
            self.port_role.mousePressEvent = lambda e, device=device: self._show_port_profile_details(e)

            # Log the inference
            self.log(f"端口角色推断: {view.port_intent.role.value}", "INFO")

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

    def _show_port_profile_details(self, event):
        """Show port profile inference details dialog"""
        if not hasattr(self, 'current_device') or not self.current_device:
            return

        try:
            from lldp.view_model import to_view
            view = to_view(self.current_device)

            # 创建推断依据对话框
            dialog = QMessageBox(self)
            dialog.setWindowTitle("端口角色推断依据")

            #  专业UI：根据置信度设置图标
            confidence = view.port_intent.confidence
            if confidence >= 90:
                icon = QMessageBox.Icon.Information
                title = f"🎯 {view.port_role_summary}"
            elif confidence >= 70:
                icon = QMessageBox.Icon.Warning
                title = f"[分析] {view.port_role_summary}"
            else:
                icon = QMessageBox.Icon.Question
                title = f"[详情] {view.port_role_summary}"

            dialog.setIcon(icon)
            dialog.setText(title)

            # 推断依据详情 - 增强版：显示网络意图分析
            evidence_text = "TLV证据：\n\n"
            for i, evidence in enumerate(view.port_intent.tlv_evidence, 1):
                evidence_text += f"{i}. {evidence}\n"

            # 添加运维洞察和配置建议
            insight_text = f"\n运维洞察:\n{view.port_intent.operational_insight}\n\n"
            insight_text += f"配置建议:\n{view.port_intent.configuration_suggestion}"

            if view.port_intent.auto_discovery_issues:
                insight_text += f"\n\n发现问题:\n"
                for issue in view.port_intent.auto_discovery_issues:
                    insight_text += f"• {issue}\n"

            dialog.setDetailedText(evidence_text + insight_text)
            dialog.setStandardButtons(QMessageBox.StandardButton.Ok)

            #  UX：根据端口角色设置对话框样式
            role = view.port_intent.role
            if role.value in ["Core Infrastructure", "Uplink (LAG)"]:
                dialog.setStyleSheet("""
                    QMessageBox {
                        background: #ede9fe;
                    }
                    QLabel {
                        color: #5b21b6;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)
            elif role.value == "Anomaly Detected":
                dialog.setStyleSheet("""
                    QMessageBox {
                        background: #fee2e2;
                    }
                    QLabel {
                        color: #991b1b;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)
            else:
                dialog.setStyleSheet("""
                    QMessageBox {
                        background: #f1f5f9;
                    }
                    QLabel {
                        color: #1e293b;
                        font-weight: bold;
                        font-size: 14px;
                    }
                """)

            dialog.exec()

        except Exception as e:
            print(f"[ERROR] Failed to show port profile details: {e}")
            import traceback
            traceback.print_exc()

    def export_data(self):
        """Export discovered devices - with format auto-completion"""
        #  检查是否有设备可导出
        if not self.discovered_devices:
            QMessageBox.warning(self, "警告",
                "没有可导出的设备数据！\n\n"
                "请先捕获设备后再导出。\n\n"
                "操作步骤：\n"
                "1. 选择网络适配器\n"
                "2. 点击'开始捕获'\n"
                "3. 插入网线到设备\n"
                "4. 等待设备自动发现")
            return

        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime

        # Ask for save location and format
        file_filter = "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)"
        default_filename = f"lldp_devices_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出LLDP设备信息",
            default_filename,
            file_filter
        )

        if not file_path:
            return

        # 优化4: 自动补全文件扩展名（如果用户没有手动输入）
        if not any(file_path.endswith(ext) for ext in ['.json', '.csv', '.txt']):
            # 根据选择的过滤器自动添加扩展名
            if 'JSON' in selected_filter:
                file_path += '.json'
            elif 'CSV' in selected_filter:
                file_path += '.csv'
            elif 'Text' in selected_filter:
                file_path += '.txt'
            else:
                # 默认使用json
                file_path += '.json'

        try:
            # 优化D: 设置等待光标，提供用户反馈
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.status_label.setText("正在导出数据...")

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
            import traceback
            traceback.print_exc()

        finally:
            # 优化D: 恢复光标和状态
            QApplication.restoreOverrideCursor()
            self.status_label.setText("导出完成")

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
                #  NEW: Port Semantic Profile
                'port_role': view.port_intent.role.value,
                'port_confidence': view.port_intent.confidence,
                'network_intent': view.port_intent.intent.value if view.port_intent.intent else '未知',
                'tlv_evidence': view.port_intent.tlv_evidence,
                'operational_insight': view.port_intent.operational_insight,
                'configuration_suggestion': view.port_intent.configuration_suggestion,
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

        #  修复编码：使用utf-8-sig确保Windows Excel正确识别UTF-8
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            #  NEW: Header with port role
            writer.writerow([
                '端口角色', '置信度', '推断依据',
                '系统名称', '设备MAC', '端口ID', '端口描述',
                '管理IP', 'VLAN', '速率/双工', '链路聚合', '最大帧长', 'PoE', '系统描述'
            ])

            # Data rows - using ViewModel
            for device in self.discovered_devices:
                view = to_view(device)

                #  CSV健壮性：清理特殊字符，防止Excel行序错乱
                def clean_csv_field(text):
                    """清理CSV字段中的特殊字符"""
                    if not text:
                        return ""
                    text = str(text)
                    # 替换换行符和制表符
                    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                    # 移除其他控制字符
                    text = ''.join(char for char in text if ord(char) >= 32 or char in ' \n\r\t')
                    return text.strip()

                writer.writerow([
                    #  NEW: Port Semantic Profile
                    clean_csv_field(view.port_intent.role.value),
                    f"{view.port_intent.confidence}%",
                    clean_csv_field(view.port_intent.intent.value if view.port_intent.intent else '未知'),
                    clean_csv_field(" / ".join(view.port_intent.tlv_evidence)),
                    # Original fields with special character cleaning
                    clean_csv_field(view.system_name),
                    clean_csv_field(view.mac),
                    clean_csv_field(view.port_id),
                    clean_csv_field(view.port_desc),
                    clean_csv_field(view.ip),
                    clean_csv_field(view.vlan),
                    clean_csv_field(view.macphy),
                    clean_csv_field(view.link_agg),
                    clean_csv_field(view.mtu),
                    clean_csv_field(view.poe),
                    clean_csv_field((safe_get(device, 'system_description') or '—')[:30])
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

                #  NEW: Port Intent Profile (Network Intent Analysis)
                f.write(f"【端口角色】{view.port_intent.role.value}\n")
                f.write(f"【网络意图】{view.port_intent.intent.value if view.port_intent.intent else '未知'}\n")
                f.write(f"【置信度】{view.port_intent.confidence}%\n")
                f.write(f"【受管设备】{'是' if view.port_intent.is_managed else '否'}\n")
                f.write(f"\n【TLV证据】\n")
                for evidence in view.port_intent.tlv_evidence:
                    f.write(f"  • {evidence}\n")
                f.write(f"\n【运维洞察】\n{view.port_intent.operational_insight}\n")
                f.write(f"\n【配置建议】\n{view.port_intent.configuration_suggestion}\n")
                if view.port_intent.auto_discovery_issues:
                    f.write(f"\n【发现问题】\n")
                    for issue in view.port_intent.auto_discovery_issues:
                        f.write(f"  • {issue}\n")
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
        """
        Window close event - 线程安全的资源清理

        优化: 确保线程安全退出，防止资源泄漏和竞态条件
        """
        try:
            # 优化1: 防止重复关闭
            if hasattr(self, '_is_closing'):
                if self._is_closing:
                    event.accept()
                    return
            self._is_closing = True

            self.log("正在关闭应用...", "INFO")

            # 优化2: 按正确顺序停止定时器（先停止生产者，再停止消费者）
            if hasattr(self, 'debug_log_timer') and self.debug_log_timer:
                self.debug_log_timer.stop()

            if hasattr(self, 'progress_timer') and self.progress_timer:
                self.progress_timer.stop()

            # 优化3: 安全停止网络监听器（等待线程完全退出）
            if hasattr(self, 'listener') and self.listener:
                self.listener.stop()
                # 等待监听器线程完全退出（防止竞态条件）
                if hasattr(self.listener, 'thread') and self.listener.thread:
                    wait_time = 0
                    while self.listener.thread.is_alive() and wait_time < 2000:  # 最多等待2秒
                        QApplication.processEvents()
                        import time
                        time.sleep(0.1)
                        wait_time += 100
                    if self.listener.thread.is_alive():
                        self.log("警告: 监听器线程未能在2秒内退出", "WARNING")

            # 优化4: 处理剩余的日志队列（防止日志丢失）
            if hasattr(self, 'debug_log_queue') and self.debug_log_queue:
                queue_size = len(self.debug_log_queue)
                if queue_size > 0:
                    self.log(f"处理剩余日志条目: {queue_size} 条", "INFO")
                    self._process_debug_log_queue()

            # 优化5: 保存配置（如果需要）
            # 这里可以添加保存用户偏好设置的逻辑

            self.log("应用已安全关闭", "SUCCESS")
            event.accept()

        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")
            import traceback
            traceback.print_exc()
            # 即使清理失败，也允许关闭窗口（防止卡死）
            event.accept()


def main():
    """Main entry point - with High DPI support"""
    try:
        # 优化5: 启用高DPI支持（高分屏适配）
        # 这必须在创建QApplication之前设置
        import os
        os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        os.environ['QT_SCALE_FACTOR'] = '1'

        # 🔥 关键修复: Windows任务栏图标 - AppUserModelID必须在QApplication创建前设置
        if os.name == 'nt':  # Windows系统
            try:
                import ctypes
                app_id = 'com.hicool.lldpanalyzer.300'  # v3.0 App ID
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
                print(f"[DEBUG] ✅ Windows AppUserModelID set: {app_id}")
            except Exception as e:
                print(f"[WARNING] Failed to set Windows AppUserModelID: {e}")

        # 在PyQt6中，High DPI支持默认启用，但我们可以设置一些属性
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt

        app = QApplication(sys.argv)

        # PyQt6的高DPI支持是自动启用的，无需手动设置
        app.setStyle("Fusion")

        #  设置应用程序图标（任务栏和窗口标题栏）
        from PyQt6.QtGui import QIcon

        # 查找图标文件 - 使用pathlib.Path（优化C）
        meipass = getattr(sys, '_MEIPASS', '')
        current_dir = Path(__file__).parent.parent

        icon_paths = [
            # 开发环境：使用相对路径
            current_dir / 'lldp_icon.png',
            current_dir / 'lldp_icon.ico',
            # 打包后：在sys._MEIPASS中查找
            Path(meipass) / 'lldp_icon.png',
            Path(meipass) / 'lldp_icon.ico',
            # 当前目录
            Path('lldp_icon.png'),
            Path('lldp_icon.ico'),
        ]

        icon_loaded = False
        for icon_path in icon_paths:
            if icon_path.exists():
                try:
                    app_icon = QIcon(str(icon_path))  # QIcon需要字符串路径
                    app.setWindowIcon(app_icon)
                    icon_loaded = True
                    break
                except Exception as e:
                    continue

        if not icon_loaded:
            # 如果图标文件不存在，使用默认图标
            pass

        #  添加全局异常处理器，防止程序静默崩溃
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

        #  保存错误信息
        try:
            import datetime
            error_log = f"lldp_analyzer_fatal_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(error_log, 'w', encoding='utf-8') as f:
                f.write(f"FATAL ERROR: {e}\n")
                traceback.print_exc(file=f)
            print(f"Error saved to: {error_log}")
        except:
            pass

        #  在GUI环境中显示错误对话框
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
