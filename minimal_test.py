#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal PyQt6 test - No network capture
"""

import sys

print("[TEST] Starting...")

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QGroupBox, QHBoxLayout
    from PyQt6.QtCore import Qt
    print("[OK] PyQt6 imported")
except ImportError as e:
    print(f"[FAIL] PyQt6: {e}")
    sys.exit(1)

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLDP Test")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("background-color:#0f172a;")

        layout = QVBoxLayout()

        # Title
        title = QLabel("LLDP Network Analyzer - UI Test")
        title.setStyleSheet("font-size:18px; color:#e2e8f0; font-weight:bold; padding:20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Card 1
        card1 = QGroupBox("交换机信息")
        card1.setStyleSheet("""
            QGroupBox {
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 14px;
                color: #e2e8f0;
                margin-top: 12px;
            }
        """)
        card1_layout = QVBoxLayout()

        self.sw_name = QLabel("Ruijie S2910-24GT4XS-L")
        self.sw_name.setStyleSheet("color:#cbd5e1; font-size:13px;")

        self.sw_mac = QLabel("C0:B8:E6:3E:3B:FC")
        self.sw_mac.setStyleSheet("color:#22c55e; font-weight:600; font-size:13px;")

        self.sw_ip = QLabel("192.168.1.1")
        self.sw_ip.setStyleSheet("color:#cbd5e1; font-size:13px;")

        card1_layout.addWidget(self.sw_name)
        card1_layout.addWidget(self.sw_mac)
        card1_layout.addWidget(self.sw_ip)
        card1.setLayout(card1_layout)

        layout.addWidget(card1)

        # Card 2
        card2 = QGroupBox("连接端口")
        card2.setStyleSheet(card1.styleSheet())
        card2_layout = QVBoxLayout()

        self.port_id = QLabel("GigabitEthernet 0/11")
        self.port_id.setStyleSheet("color:#cbd5e1; font-size:13px;")

        self.vlan = QLabel("2011 (Untagged)")
        self.vlan.setStyleSheet("color:#22c55e; font-weight:600; font-size:13px;")

        self.poe = QLabel("支持 (Class 0)")
        self.poe.setStyleSheet("color:#22c55e; font-weight:600; font-size:13px;")

        card2_layout.addWidget(self.port_id)
        card2_layout.addWidget(self.vlan)
        card2_layout.addWidget(self.poe)
        card2.setLayout(card2_layout)

        layout.addWidget(card2)

        # Status
        self.status = QLabel("✓ UI渲染正常 - 数据显示正确")
        self.status.setStyleSheet("""
            color: #22c55e;
            font-size: 14px;
            padding: 15px;
            background: #1e293b;
            border-radius: 6px;
        """)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        # Update button
        btn = QPushButton("测试更新")
        btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: white;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
        """)
        btn.clicked.connect(self.test_update)
        layout.addWidget(btn)

        self.setLayout(layout)

    def test_update(self):
        print("[TEST] Button clicked!")
        self.sw_name.setText("Updated Switch")
        self.sw_mac.setText("AA:BB:CC:DD:EE:FF")
        self.status.setText("✓ 数据更新成功！")
        print("[TEST] Data updated")


def main():
    print("[TEST] Creating application...")
    app = QApplication(sys.argv)

    print("[TEST] Creating window...")
    window = TestWindow()

    print("[TEST] Showing window...")
    window.show()

    print("[TEST] Starting event loop...")
    print("[TEST] Close the window to exit\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
