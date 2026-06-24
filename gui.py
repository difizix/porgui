# gui.py is now a wrapper that imports and executes app.py
import sys
import os

# Insert workspace directory into sys.path to guarantee clean relative imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app
