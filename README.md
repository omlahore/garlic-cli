# garlic

CLI tool for PS4/PS5 save management via the [garlicsaves.com](https://garlicsaves.com) API.

Decrypt, encrypt, resign, and re-region PS4/PS5 saves from the command line. Auto-detects PS4 vs PS5 saves from file headers.

## Install

```bash
# Clone and add to PATH
git clone https://github.com/earthonion/garlic-cli.git
ln -s $(pwd)/garlic-cli/garlic ~/.local/bin/garlic

# Or just download the script
curl -o garlic https://raw.githubusercontent.com/earthonion/garlic-cli/main/garlic
chmod +x garlic
```

No dependencies — pure Python 3 stdlib.

## Setup

Get an API key from [garlicsaves.com/contribute](https://garlicsaves.com/contribute), then:

```bash
garlic config --key YOUR_API_KEY
```

Or set the `GARLIC_API_KEY` environment variable, or pass `-K KEY` to any command.

## Usage

### Decrypt

```bash
# PS4 save (requires sealed key)
garlic d SAVEFILE -k SAVEFILE.bin

# Auto-finds .bin if same name exists in directory
garlic d SAVEFILE

# PS5 save (no sealed key needed)
garlic d sdimg_savefile

# Exclude sce_sys from output
garlic d SAVEFILE -k SAVEFILE.bin --no-sce-sys

# Custom output path
garlic d SAVEFILE -k SAVEFILE.bin -o decrypted.zip
```

### Encrypt

```bash
# Encrypt a decrypted save folder (must contain sce_sys/param.sfo)
garlic e ./my_save/ -a 0000000000000000

# PS5 save
garlic e ./my_save/ -a 0000000000000000 -p ps5
```

### Resign

```bash
# Re-sign to a different account
garlic r SAVEFILE -k SAVEFILE.bin -a 1234567890abcdef
```

### Re-region

```bash
# Re-region using a sample save's keystone
garlic rr TARGET -k TARGET.bin -s SAMPLE -a 0000000000000000 --sample-key SAMPLE.bin
```

### Other Commands

```bash
# Check job status
garlic s JOB_ID

# Download a completed job's result
garlic dl JOB_ID -o result.zip

# List recent jobs
garlic ls

# Show config
garlic config --show
```

## Batch Decrypt

```bash
# Decrypt all saves from a PS4 USB backup
for dir in /media/usb/PS4/SAVEDATA/*/; do
  title=$(basename "$dir")
  for bin in "$dir"*.bin; do
    [ -f "$bin" ] || continue
    save="${bin%.bin}"
    [ -f "$save" ] || continue
    garlic d "$save" -k "$bin" -o "decrypted/${title}_$(basename $save).zip"
  done
done
```

## USB helpers

The four things garlic did not do: read the account ID and title ID off a USB export,
find a community save for that title, and put the resigned result back in the right folder.

```bash
# What is on the stick? Prints the account ID in both forms and every title on it.
garlic usb                      # auto-detects /media, /run/media, /Volumes, drive letters
garlic usb --usb /media/me/PS4  # or point at the USB root

# Which title IDs exist for a game, per region?
garlic titles "Red Dead Redemption 2"

# Known community saves for a title ID (links only, nothing is rehosted)
garlic catalog CUSA08519

# Resign a downloaded save (zip, folder, or file) to the account on the USB
# and write it to PS4/SAVEDATA/<account>/<title>/ in one go
garlic apply ~/Downloads/rdr2-ch2.zip --usb /media/me/PS4

# Or just copy an already-resigned result into place
garlic install 1234_resigned.zip --usb /media/me/PS4 -t CUSA08519
```

Then on the console: Settings > Saved Data and Game/App Settings > Saved Data (PS4) > USB Drive > Copy to Console Storage.
PS5 uses the same path for PS4 games.

### Account ID forms

The folder name under `PS4/SAVEDATA/` is the numeric account ID as 16 hex digits,
zero-padded. That is also the "display form" the garlicsaves **website** asks for, so
paste the folder name straight into the web form.

The raw worker API is different. `garlic-worker` runs `hex_to_bytes(account_id)` and
`pwrite()`s those 8 bytes into `param.sfo`, which stores `ACCOUNT_ID` as a little-endian
uint64, so the raw API takes the byte sequence: the folder name reversed.

```
USB folder name / garlicsaves web form:  0123456789abcdef
raw worker API (-a, apply):              efcdab8967452301
```

`garlic usb` prints both and labels which is which. `garlic apply` does the swap for
you; `-a` on `resign`, `encrypt` and `reregion` is passed through untouched. If a
resigned save does not show up on the console, try `apply --no-swap` once.

Region matters: a `CUSA03041` (US) save will not import into a `CUSA08519` (EU) install
even after resigning. `garlic usb` shows the title ID your console actually uses.

`catalog.json` sits next to the script. Add entries there; keep them as links.

Self-check: `python3 test_garlic.py` (offline).

## Config

Config is stored at `~/.config/garlic/config.json`. API key can also be set via the `GARLIC_API_KEY` environment variable or the `-K` flag.

## License

GPL-3.0 — see [LICENSE](LICENSE).
