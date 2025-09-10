#!/usr/bin/env python3
"""
Test script to debug PyQt6 issues
"""

import sys
print(f"Python version: {sys.version}")
print(f"Platform: {sys.platform}")

try:
    print("Testing PyQt6 import...")
    import PyQt6
    print(f"PyQt6 version: {PyQt6.QtCore.PYQT_VERSION_STR}")
    print(f"Qt version: {PyQt6.QtCore.QT_VERSION_STR}")
    
    print("Testing PyQt6.QtCore import...")
    from PyQt6.QtCore import Qt
    print("PyQt6.QtCore imported successfully")
    
    print("Testing PyQt6.QtWidgets import...")
    from PyQt6.QtWidgets import QApplication
    print("PyQt6.QtWidgets imported successfully")
    
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    print("QApplication created successfully")
    
    print("All PyQt6 tests passed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()


