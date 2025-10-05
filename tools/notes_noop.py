# NOOP helper for training the AI patch bridge.
# This file does nothing and is safe to add.
# Keep all real logic in existing wrappers and scripts.

def noop():
    """Return a static note to mark patch flow success."""
    return "ai-patch-bridge-ok"

if __name__ == "__main__":
    print(noop())
