#!/usr/bin/env python3
"""
Test script to verify that Context cleanup works properly.

This script should exit cleanly after the Context is closed,
demonstrating proper resource cleanup.
"""

import ausb

def test_context_cleanup():
    print("Creating Context...")
    ctx = ausb.Context(enable_hotplug=False)

    print("Listing devices...")
    device_count = 0
    for dev in ctx:
        device_count += 1
        try:
            print(f"  Device {device_count}: {dev.vendor_id:04x}:{dev.product_id:04x}")
        except:
            print(f"  Device {device_count}: (unable to read)")

        # Only list first 5 devices for brevity
        if device_count >= 5:
            break

    print(f"Found {device_count} device(s)")

    print("\nClosing Context...")
    ctx.close()

    print("Done! Should exit cleanly now.")

if __name__ == "__main__":
    print("Testing Context cleanup...")
    print("If this script hangs after 'Done!', the cleanup is not working.\n")

    test_context_cleanup()

    print("\nTest passed! Exited cleanly.")
