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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
