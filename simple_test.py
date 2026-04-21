#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for PyQt6 UI
"""

import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class SimpleTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLDP UI Test")
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color:#0f172a;")

        layout = QVBoxLayout()

        # Test label
        self.label = QLabel("测试文本")
        self.label.setStyleSheet("""
            font-size: 16px;
            color: #22c55e;
            font-weight: 600;
            padding: 20px;
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        # Test button
        btn = QPushButton("更新数据")
        btn.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: white;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
        """)
        btn.clicked.connect(self.update_data)
        layout.addWidget(btn)

        self.setLayout(layout)

    def update_data(self):
        print("[TEST] Button clicked!")
        self.label.setText("数据已更新")
        print("[TEST] Label updated")


def main():
    print("[TEST] Starting PyQt6 simple test...")
    app = QApplication(sys.argv)
    window = SimpleTestWindow()
    window.show()
    print(f"[TEST] Window shown")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
