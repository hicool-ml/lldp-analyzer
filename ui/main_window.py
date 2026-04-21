"""
GUI Interface for LLDP Network Analyzer
Uses clean architecture: Capture -> Parser -> Model -> UI
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
from datetime import datetime
from typing import List, Optional

from lldp import LLDPCaptureListener
from lldp.model import LLDPDevice
from core.exporter import LLDPExporter


class LLDPAnalyzerGUI:
    """
    LLDP Network Analyzer GUI

    Clean architecture implementation:
    - UI Layer: Only responsible for rendering
    - Capture Layer: Separate thread with queue
    - Parser Layer: Pure functions, no side effects
    """

    def __init__(self, root: tk.Tk):
        """Initialize GUI"""
        self.root = root
        self.root.title("LLDP Network Analyzer v1.0.0 - Industrial Grade")
        self.root.geometry("1000x800")

        # Setup styles
        self.setup_styles()

        # Core components (clean separation)
        self.listener = LLDPCaptureListener()
        self.discovered_devices: List[LLDPDevice] = []
        self.current_device: Optional[LLDPDevice] = None

        # UI state
        self.is_capturing = False
        self.capture_start_time: Optional[float] = None

        # Build UI
        self.create_ui()

        # Initialize
        self.refresh_interfaces()

    def setup_styles(self):
        """Setup modern UI styles"""
        self.colors = {
            'bg_primary': '#1e3c72',
            'bg_secondary': '#2a5298',
            'text_white': '#ffffff',
            'text_accent': '#00ff00',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336'
        }

        self.root.configure(bg=self.colors['bg_primary'])

        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=self.colors['bg_primary'])
        style.configure('TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_white'],
                       font=('Microsoft YaHei UI', 10))
        style.configure('Header.TLabel',
                       font=('Microsoft YaHei UI', 16, 'bold'),
                       foreground=self.colors['text_accent'])
        style.configure('TButton',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=5)
        style.configure('Status.TLabel',
                       font=('Microsoft YaHei UI', 9),
                       foreground='#cccccc')

    def create_ui(self):
        """Create user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        self.create_header(main_frame)

        # Control panel
        self.create_control_panel(main_frame)

        # Progress
        self.create_progress_panel(main_frame)

        # Content area
        self.create_content_area(main_frame)

        # Status bar
        self.create_status_bar(main_frame)

    def create_header(self, parent):
        """Create header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header_frame,
                 text="🔌 LLDP Network Analyzer",
                 style='Header.TLabel').pack(side=tk.LEFT)

        ttk.Label(header_frame,
                 text="v1.0.0 | Industrial Grade Architecture",
                 style='Status.TLabel').pack(side=tk.RIGHT)

    def create_control_panel(self, parent):
        """Create control panel"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 15))

        # Adapter selection
        adapter_container = ttk.Frame(control_frame)
        adapter_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(adapter_container, text="网络适配器:").pack(side=tk.LEFT, padx=(0, 10))

        self.adapter_var = tk.StringVar()
        self.adapter_combo = ttk.Combobox(adapter_container,
                                         textvariable=self.adapter_var,
                                         state='readonly',
                                         width=30)
        self.adapter_combo.pack(side=tk.LEFT, padx=(0, 10))

        # Control buttons
        button_container = ttk.Frame(control_frame)
        button_container.pack(side=tk.RIGHT)

        self.start_btn = ttk.Button(button_container, text="▶️ 开始捕获",
                                   command=self.start_capture)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(button_container, text="⏹️ 停止",
                                  command=self.stop_capture, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.export_btn = ttk.Button(button_container, text="📥 导出",
                                     command=self.export_data, state=tk.DISABLED)
        self.export_btn.pack(side=tk.LEFT)

    def create_progress_panel(self, parent):
        """Create progress panel"""
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(progress_frame, text="捕获进度:").pack(side=tk.LEFT, padx=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame,
                                           variable=self.progress_var,
                                           maximum=100,
                                           length=400,
                                           mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT, padx=(10, 0))

        self.device_count_label = ttk.Label(progress_frame, text="(0 devices)")
        self.device_count_label.pack(side=tk.LEFT, padx=(10, 0))

    def create_content_area(self, parent):
        """Create content area"""
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(output_frame, text="LLDP设备发现结果:").pack(anchor=tk.W, pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(output_frame,
                                                     wrap=tk.WORD,
                                                     font=('Consolas', 10),
                                                     height=20,
                                                     bg='#0a0a0a',
                                                     fg='#00ff00')
        self.output_text.pack(fill=tk.BOTH, expand=True)

        self.show_welcome_message()

    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=(15, 0))

        self.status_label = ttk.Label(status_frame,
                                     text="就绪 | 选择适配器并开始捕获",
                                     style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)

        self.last_update_label = ttk.Label(status_frame,
                                          text="最后更新: --",
                                          style='Status.TLabel')
        self.last_update_label.pack(side=tk.RIGHT)

    def show_welcome_message(self):
        """Show welcome message"""
        welcome_text = """
╔════════════════════════════════════════════════════════════════════╗
║          LLDP Network Analyzer - Industrial Grade v1.0.0            ║
║              Professional LLDP Discovery Tool                         ║
╚════════════════════════════════════════════════════════════════════╝

🏗️  Architecture:
  • Clean 3-tier separation
  • Capture Layer → Parser Layer → UI Layer
  • Thread-safe queue-based design
  • Pure function protocol parser

✨ Features:
  • Real-time device discovery
  • Structured device model
  • Multiple export formats (JSON/CSV/XML)
  • CLI and GUI modes
  • Full LLDP TLV support

📊 Supported Information:
  • Device identification (Chassis ID, Port ID)
  • Network configuration (VLAN, Management IP)
  • Power over Ethernet (PoE) - IEEE 802.3at/bt
  • Device capabilities (Bridge, Router, etc.)
  • Auto-negotiation status

🚀 Ready to discover LLDP devices!
"""
        self.output_text.insert(tk.END, welcome_text)

    def refresh_interfaces(self):
        """Refresh network adapter list"""
        try:
            from scapy.all import get_working_ifaces

            interfaces = []
            for iface in get_working_ifaces():
                desc = iface.description.lower()
                if "ethernet" in desc and "virtual" not in desc:
                    interfaces.append(iface)

            if interfaces:
                adapter_names = [f"{iface.description} ({iface.name})"
                               for iface in interfaces]
                self.adapter_combo['values'] = adapter_names
                self.adapter_combo.current(0)
                self.selected_interface = interfaces[0]

        except Exception as e:
            self.show_error("接口扫描失败", str(e))

    def start_capture(self):
        """Start LLDP capture"""
        if not hasattr(self, 'selected_interface'):
            self.show_warning("请先选择网络适配器")
            return

        self.is_capturing = True
        self.capture_start_time = time.time()
        self.discovered_devices = []
        self.current_device = None

        # Update UI
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.DISABLED)
        self.output_text.delete(1.0, tk.END)

        # Show capture status
        self.show_capture_status()

        # Start capture with callbacks
        self.listener.start(
            interface=self.selected_interface,
            duration=30,
            on_device_discovered=self.on_device_discovered,
            on_capture_complete=self.on_capture_complete
        )

        # Start progress update
        self.update_progress()

    def stop_capture(self):
        """Stop capture"""
        self.listener.stop()
        self.is_capturing = False

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        if self.discovered_devices:
            self.export_btn.config(state=tk.NORMAL)

    def on_device_discovered(self, device: LLDPDevice):
        """Callback when device discovered"""
        self.discovered_devices.append(device)
        self.current_device = device

        # Update UI in main thread
        self.root.after(0, lambda: self.display_device(device))

        # Update device count
        self.root.after(0, lambda: self.device_count_label.config(
            text=f"({len(self.discovered_devices)} devices)"
        ))

    def on_capture_complete(self, devices: List[LLDPDevice]):
        """Callback when capture completes"""
        self.is_capturing = False

        self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

        if devices:
            self.root.after(0, lambda: self.export_btn.config(state=tk.NORMAL))

    def update_progress(self):
        """Update progress bar"""
        if not self.is_capturing:
            return

        if self.capture_start_time:
            elapsed = time.time() - self.capture_start_time
            progress = min((elapsed / 30) * 100, 100)
            self.progress_var.set(progress)
            remaining = max(30 - elapsed, 0)
            self.progress_label.config(text=f"{int(progress)}% ({int(remaining)}s)")

        self.root.after(100, self.update_progress)

    def show_capture_status(self):
        """Show capture status"""
        status = f"""
╔════════════════════════════════════════════════════════════════════╗
║                    LLDP 报文捕获中...                                ║
╚════════════════════════════════════════════════════════════════════╝

🔍 正在监听网络适配器: {self.selected_interface.description}
📡 接口名称: {self.selected_interface.name}
⏱️  捕获时长: 30秒
🎯 目标: LLDP报文 (EtherType 0x88CC)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏳ 等待LLDP报文...
💡 捕获到数据后会立即显示，无需等待！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

提示:
  • 请确保网络连接正常
  • 确认连接到支持LLDP的交换机
  • 捕获到的信息会实时显示在下方
"""
        self.output_text.insert(tk.END, status)

    def display_device(self, device: LLDPDevice):
        """Display discovered device"""
        # Build display
        output = []

        output.append("╔════════════════════════════════════════════════════════════════════╗")
        output.append("║                  ✅ LLDP设备发现成功！                             ║")
        output.append("╚════════════════════════════════════════════════════════════════════╝")
        output.append("")
        output.append(f"🎯 发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"📊 已发现设备: {len(self.discovered_devices)}")
        output.append("")

        # Device identification
        output.append("📋 设备标识:")
        output.append("─" * 65)

        if device.chassis_id:
            if device.chassis_id.is_mac_address():
                output.append(f"设备MAC地址: {device.chassis_id.value}")
            else:
                output.append(f"设备名称: {device.chassis_id.value}")
                if device.chassis_id.type.name != "MAC_ADDRESS":
                    output.append(f"注意: 这是设备的{device.chassis_id.type.name.lower()}, 不是MAC地址")
            output.append(f"ID类型: {device.chassis_id.type.name}")

        if device.system_name:
            output.append(f"系统名称: {device.system_name}")

        if device.system_description:
            desc = device.system_description
            if len(desc) > 60:
                desc = desc[:57] + "..."
            output.append(f"系统描述: {desc}")

        # Port information
        output.append("")
        output.append("🔌 连接端口信息:")
        output.append("─" * 65)

        if device.port_id:
            if device.port_id.is_mac_address():
                output.append(f"端口MAC地址: {device.port_id.value}")
            else:
                output.append(f"端口标识: {device.port_id.value}")
            output.append(f"ID类型: {device.port_id.type.name}")

        if device.port_description:
            output.append(f"端口描述: {device.port_description}")

        if device.management_ip:
            output.append(f"管理地址: {device.management_ip}")

        # VLAN
        if device.port_vlan:
            output.append("")
            output.append("🌐 VLAN配置:")
            output.append("─" * 65)
            output.append(f"端口VLAN: {device.port_vlan.vlan_id}")
            if device.port_vlan.tagged:
                output.append(f"VLAN模式: {'Tagged' if device.port_vlan.tagged else 'Untagged'}")

        # PoE
        if device.poe.supported:
            output.append("")
            output.append("⚡ PoE (Power over Ethernet):")
            output.append("─" * 65)
            output.append(f"PoE支持: 是")
            if device.poe.power_type:
                output.append(f"PoE类型: {device.poe.power_type}")
            if device.poe.power_class:
                output.append(f"功率等级: {device.poe.power_class}")

        # Capabilities
        caps = device.capabilities.get_enabled_capabilities()
        if caps:
            output.append("")
            output.append("📊 设备能力:")
            output.append("─" * 65)
            output.append(f"能力: {', '.join(caps)}")

        output.append("")
        output.append("═" * 65)

        if self.is_capturing:
            output.append("⏳ 捕获进行中... 数据会实时更新")
        else:
            output.append("✅ 捕获完成！")

        output.append("")

        result_text = "\n".join(output)
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(tk.END, result_text)

    def export_data(self):
        """Export discovered devices"""
        if not self.discovered_devices:
            self.show_warning("没有可导出的数据")
            return

        # Ask for file format
        format_dialog = tk.Toplevel(self.root)
        format_dialog.title("选择导出格式")
        format_dialog.geometry("300x150")
        format_dialog.transient(self.root)
        format_dialog.grab_set()

        ttk.Label(format_dialog, text="选择导出格式:",
                 font=('Microsoft YaHei UI', 12)).pack(pady=20)

        def export(fmt):
            filepath = filedialog.asksaveasfilename(
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}")],
                initialfile=f"lldp_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{fmt}"
            )

            if filepath:
                try:
                    if fmt == "json":
                        LLDPExporter.to_json(self.discovered_devices, filepath)
                    elif fmt == "csv":
                        LLDPExporter.to_csv(self.discovered_devices, filepath)
                    elif fmt == "xml":
                        LLDPExporter.to_xml(self.discovered_devices, filepath)

                    messagebox.showinfo("导出成功", f"数据已导出到:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("导出失败", f"导出失败:\n{str(e)}")

            format_dialog.destroy()

        btn_frame = ttk.Frame(format_dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="JSON", command=lambda: export("json")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="CSV", command=lambda: export("csv")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="XML", command=lambda: export("xml")).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Zabbix", command=lambda: export("zabbix")).pack(side=tk.LEFT, padx=5)

    def show_error(self, title, message):
        """Show error dialog"""
        messagebox.showerror(title, message)

    def show_warning(self, message):
        """Show warning dialog"""
        messagebox.showwarning("警告", message)


def main():
    """GUI entry point"""
    try:
        root = tk.Tk()
        app = LLDPAnalyzerGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("启动错误", f"程序启动失败: {str(e)}")


if __name__ == "__main__":
    main()
