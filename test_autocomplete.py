#!/usr/bin/env python3
"""
Test script for CLI autocomplete functionality.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import readline
    readline_available = True
except ImportError:
    readline_available = False

if readline_available:
    print("Readline is available")
    
    # Test autocomplete function
    class TestAutocomplete:
        def __init__(self):
            self.commands = ['help', 'quit', 'hire', 'fire', 'assign']
            self.matches = []
        
        def autocomplete(self, text, state):
            if state == 0:
                if not text:
                    self.matches = self.commands[:]
                else:
                    self.matches = [cmd for cmd in self.commands if cmd.startswith(text)]
            
            try:
                return self.matches[state]
            except IndexError:
                return None
    
    # Set up autocomplete
    test_autocomplete = TestAutocomplete()
    readline.set_completer(test_autocomplete.autocomplete)
    readline.parse_and_bind("tab: complete")
    
    print("Autocomplete setup complete")
    print("Available commands:", test_autocomplete.commands)
    print("Try typing 'h' and pressing TAB to see autocomplete in action")
else:
    print("Readline is not available")