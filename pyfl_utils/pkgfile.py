import os
import sys


if getattr(sys, 'frozen', False):
    # we are running in a bundle
    frozen = 'ever so'
    BUNDLE_DIR = sys._MEIPASS
else:
    # we are running in a normal Python environment
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = os.path.dirname(BUNDLE_DIR)


def read_file(rel_path):
    file_path = os.path.join(BUNDLE_DIR, rel_path)

    with open(file_path, 'r') as file:
        content = file.read()

    return content
