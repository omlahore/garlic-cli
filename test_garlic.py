#!/usr/bin/env python3
"""Offline self-check for the USB helper commands. Run: python3 test_garlic.py"""
import importlib.machinery, importlib.util, os, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader("garlic", os.path.join(HERE, "garlic"))
spec = importlib.util.spec_from_loader("garlic", loader)
g = importlib.util.module_from_spec(spec)
loader.exec_module(g)

ACCT = "0123456789abcdef"          # USB folder form
API = "efcdab8967452301"           # byte-reversed


def make_usb(root, acct=ACCT, title="CUSA08519", saves=("SRDR30000",)):
    d = os.path.join(root, "PS4", "SAVEDATA", acct, title)
    os.makedirs(d)
    for s in saves:
        open(os.path.join(d, s), "wb").write(b"\x01" + b"\0" * 15)
        open(os.path.join(d, s + ".bin"), "wb").write(b"\0" * 96)
    return d


def test_account_forms():
    assert g.swap_account_bytes(ACCT) == API
    assert g.swap_account_bytes(API) == ACCT
    assert g.norm_account("0x" + ACCT.upper()) == ACCT


def test_scan_and_pairs():
    with tempfile.TemporaryDirectory() as t:
        make_usb(t)
        data = g.scan_usb(t)
        assert data == {ACCT: {"CUSA08519": ["SRDR30000"]}}, data
        assert g.usb_account(t) == ACCT
        pairs = g.find_pairs(t)
        assert len(pairs) == 1 and pairs[0][1].endswith("SRDR30000.bin")
        assert g.infer_title([pairs[0][0]]) == "CUSA08519"


def test_install_from_zip():
    with tempfile.TemporaryDirectory() as t:
        usb = os.path.join(t, "usb")
        make_usb(usb)
        # community zip laid out like a PS4 export from another account
        src = os.path.join(t, "src")
        make_usb(src, acct="ffffffffffffffff", saves=("SRDR30001",))
        z = os.path.join(t, "dl.zip")
        with zipfile.ZipFile(z, "w") as zf:
            for d, _, fs in os.walk(src):
                for f in fs:
                    p = os.path.join(d, f)
                    zf.write(p, os.path.relpath(p, src))
        r = subprocess.run([sys.executable, os.path.join(HERE, "garlic"), "install", z, "--usb", usb],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        dest = os.path.join(usb, "PS4", "SAVEDATA", ACCT, "CUSA08519")
        assert os.path.isfile(os.path.join(dest, "SRDR30001"))
        assert os.path.isfile(os.path.join(dest, "SRDR30001.bin"))
        # bare files with explicit title
        r = subprocess.run([sys.executable, os.path.join(HERE, "garlic"), "install",
                            os.path.join(dest, "SRDR30001"), "--usb", usb, "-t", "cusa03041"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert os.path.isfile(os.path.join(usb, "PS4", "SAVEDATA", ACCT, "CUSA03041", "SRDR30001.bin"))


def test_usb_cmd_offline():
    with tempfile.TemporaryDirectory() as t:
        make_usb(t)
        r = subprocess.run([sys.executable, os.path.join(HERE, "garlic"), "usb", "--usb", t, "--offline", "-v"],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert ACCT in r.stdout and API in r.stdout and "CUSA08519" in r.stdout and "SRDR30000" in r.stdout


def test_catalog():
    r = subprocess.run([sys.executable, os.path.join(HERE, "garlic"), "catalog", "cusa08519"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Intro Skip" in r.stdout and "All Regions" in r.stdout




def test_reregion_sample_pick():
    """Re-region must take the destination title and sample from the USB, not the input."""
    with tempfile.TemporaryDirectory() as t:
        make_usb(t)                                   # your own US save
        assert g.usb_titles_for(t, ACCT) == ["CUSA08519"]
        sp, bp = g.usb_sample_pair(t, ACCT, "CUSA08519")
        assert sp.endswith("SRDR30000") and bp.endswith("SRDR30000.bin")
        # -K is a top-level flag, it has to precede the subcommand.
        r = subprocess.run([sys.executable, os.path.join(HERE, "garlic"), "-K", "x", "apply", t,
                            "--usb", t, "--reregion", "--title", "NOPE"],
                           capture_output=True, text=True)
        assert r.returncode == 1 and "your own region's title ID" in r.stderr, (r.stdout, r.stderr)
def _make_sfo(title="CUSA08519", acct_display="0123456789abcdef"):
    """Minimal param.sfo with the two fields re-region touches."""
    import struct
    keys = ["ACCOUNT_ID", "TITLE_ID"]
    kt = b""; koff = {}
    for k in keys:
        koff[k] = len(kt); kt += k.encode() + b"\0"
    vals = {"ACCOUNT_ID": (bytes.fromhex(acct_display)[::-1], 8, 8, 0x0404),
            "TITLE_ID": (title.encode() + b"\0", len(title) + 1, 12, 0x0204)}
    dt = b""; doff = {}
    for k in keys:
        raw, ln, mx, _f = vals[k]
        doff[k] = len(dt); dt += raw + b"\0" * (mx - len(raw))
    hdr_len = 0x14 + len(keys) * 0x10
    key_off = hdr_len
    data_off = key_off + len(kt)
    out = struct.pack("<IIIII", 0x46535000, 0x0101, key_off, data_off, len(keys))
    for k in keys:
        raw, ln, mx, fmt = vals[k]
        out += struct.pack("<HHIII", koff[k], fmt, ln, mx, doff[k])
    return out + kt + dt


def test_sfo_patch_roundtrip():
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, "param.sfo")
        open(p, "wb").write(_make_sfo())
        assert g.sfo_read_title(p) == "CUSA08519"
        g.sfo_patch(p, title_id="CUSA03041", account_display=ACCT)
        assert g.sfo_read_title(p) == "CUSA03041"
        off, ln, _mx = g.sfo_fields(p)["ACCOUNT_ID"]
        stored = open(p, "rb").read()[off:off + 8]
        # stored little-endian; reversed it is the USB folder / display form
        assert stored[::-1].hex() == ACCT, stored.hex()
        assert stored.hex() == API, "stored bytes are the raw API form"


def test_api_requests_identify_themselves():
    """urllib's default UA gets a 1010 from the CDN, so every API call must set one."""
    src = open(os.path.join(HERE, "garlic")).read()
    assert 'USER_AGENT = "garlic-cli/' in src
    assert '"User-Agent": USER_AGENT' in src


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
