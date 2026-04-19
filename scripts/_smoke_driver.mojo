# C1 smoke: call into max_brain.inference.get_max_version and print it.
from max_brain.inference import get_max_version

def main():
    var v = get_max_version()
    print("max version:", v)
