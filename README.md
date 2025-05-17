# talkback-bootstrap

**Minimal, low-level ONVIF RTSP talk-back initiator**  
Battle-tested on Reolink firmwares where ONVIF/SDK-based flows fail.  
Establishes two-way audio by **hand-crafting the RTSP flow**: `DESCRIBE → SETUP → PLAY`  
Can Keep session alive with periodic `OPTIONS`.  

---

## ✨ Features

- ✅ Pure Python (≥3.10), no C dependencies
- 🛠️ Works with picky Reolink firmwares that reject standard ONVIF/SDK talk-back
- 📡 Full RTSP handshake built from scratch
- 🔍 Switch between clean `INFO` logs and full RTSP wire dump (`DEBUG`)
- 🧼 Clean, minimal API

---
## 🚀 Quick start

```python
from talkback import TalkBackInitiator

tb = TalkBackInitiator("rtsp://user:pass@cam/Preview_01_sub", verbose=True)
ip, port = tb.start()        # start RTSP session

# here you can start pushing ant RTP to ip:port with aoirtc or smth..
# ...

tb.keep_alive()              # send keepalive once (usually, session is alive for 60 secs)
tb.terminate()               # send TEARDOWN
```

---

## 📦 Installation

<details>
<summary><strong>With <code>uv</code></strong></summary>

```bash
uv venv
source .venv/bin/activate
uv pip install -e .

# (optional) run tests
uv run tests/test_initiator.py
```
</details>

<details>
<summary><strong>With Poetry</strong></summary>

```bash
poetry install
poetry run pytest -q

# (optional) run tests
poetry run python tests/test_initiator.py
```
</details>

<details>
<summary><strong>Vanilla pip</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e .

# (optional) run tests
python tests/test_initiator.py
```
</details>

---

## 🔍 Sample logs

```
2025-05-17  INFO  Connected to 192.168.1.100:554
2025-05-17  INFO  Received digest challenge (realm=BC Streaming Media)
2025-05-17  INFO  Authenticated DESCRIBE succeeded
2025-05-17  INFO  Extracted Content-Base: rtsp://192.168.1.100/Preview_01_sub/
2025-05-17  INFO  Found talk-back control track: track3
2025-05-17  INFO  Session established: D7EE6915
2025-05-17  INFO  Camera back-channel port: 6974
2025-05-17  INFO  PLAY succeeded (CSeq=4)
2025-05-17  INFO  Talk-back session started: 192.168.1.100:6974
...
2025-05-17  INFO  OPTIONS keep-alive successful (CSeq=5)
...
2025-05-17  INFO  Sent TEARDOWN (CSeq=15)
2025-05-17  INFO  RTSP talk-back session terminated
```

> Set env var `TALKBACK_LOG_LEVEL=DEBUG` to see full RTSP dump (requests and responses).

---

## ⚙️ Why low-level?


> “Tried `onvif-zeep-2`, other Python libs, even ONVIF CLI tools —  
> nothing could reliably trigger the *BackChannel* on some Reolink firmware versions.  
> Cameras responded with 401 or 403, and none of the standard methods worked.  
>  
> After digging through ONVIF + RTSP docs, I ended up writing this module from scratch —  
> just enough to get the job done.”  

If the usual wrappers and SDKs can’t bring the channel up — this module runs the handshake  
directly: from `DESCRIBE` to `PLAY`, with all the necessary flags.


---

## 🗂 Project layout

```
src/talkback/
  ├── initiator.py      # handshake logic
  ├── settings.py       # config via pydantic-settings
  └── utils.py          # URL parser + logger
tests/
  └── test_initiator.py # basic test
```

- `uv.lock` for reproducible installs
- `.python-version` is ignored unless you enforce `pyenv`

---

## 📝 License

**MIT** — do what you want, just please share improvements 
