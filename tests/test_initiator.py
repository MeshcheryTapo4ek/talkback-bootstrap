"""
Simple script to exercise TalkBackInitiator
and send periodic keep-alive pings.
"""

import time
import sys
from talkback import TalkBackInitiator

# ─── Configuration Constants ────────────────────────────────────────────────
RTSP_URL = "rtsp://admin:yqRg!Br8@172.17.32.94:554/Preview_01_sub"
CLIENT_PORT = 5000       # UDP port for RTP/RTCP (override default_settings)
VERBOSE = False          # True - DEBUG logs; False - INFO logs
KEEPALIVE_INTERVAL = 20  # seconds between OPTIONS pings
TOTAL_PINGS = 10         # how many keep-alives to send before exiting
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    # instantiate with our constants
    tb = TalkBackInitiator(
        RTSP_URL, 
        client_port=CLIENT_PORT, 
        verbose=VERBOSE,
    )
    try:
        host, port = tb.start()
        print(f"[+] Talk-back started on {host}:{port}")

        for i in range(1, TOTAL_PINGS + 1):
            time.sleep(KEEPALIVE_INTERVAL)
            ok = tb.keep_alive()
            status = "OK" if ok else "FAIL"
            print(f"[{i}/{TOTAL_PINGS}] Keep-alive: {status}")
    except Exception as e:
        print(f"[!] Error during talk-back: {e}", file=sys.stderr)
    finally:
        tb.terminate()
        print("[*] Talk-back terminated.")

if __name__ == "__main__":
    main()
