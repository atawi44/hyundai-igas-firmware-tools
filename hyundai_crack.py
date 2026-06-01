#!/usr/bin/env python3
"""
Hyundai iGAS Firmware Cracker
==============================
Cracks the ZipCrypto encryption of Hyundai iGAS firmware update packages.

Usage:
    python hyundai_crack.py <update_package.zip> [--brute] [--bat-only] [--password]

Steps:
    1. Reads the internal date from update_package.zip
    2. Converts to MS-DOS hex format
    3. Generates plain*.bin files
    4. Generates a ready-to-run .bat file
    5. Optionally runs bkcrack directly
    6. Extracts update.zip and otacerts.zip
    7. Computes ZIP password from build.prop

Reference: https://xakcop.com/post/hyundai-hack/
"""

import struct
import zipfile
import calendar
import subprocess
import os
import sys
import argparse
import hashlib

# ─── Plain file variants (ZIP local file header - exactly 10 bytes) ──────────
VARIANTS = {
    'plain1.bin': bytes.fromhex('504b0304140000000000'),  # store   v14 (10 bytes)
    'plain2.bin': bytes.fromhex('504b0304140000000800'),  # deflate v14 (10 bytes)
    'plain3.bin': bytes.fromhex('504b03040a0000000000'),  # store   v0a (10 bytes)
    'plain4.bin': bytes.fromhex('504b03040a0000000800'),  # deflate v0a (10 bytes)
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Utilities ────────────────────────────────────────────────────────────────

def msdos_date(year: int, month: int, day: int) -> bytes:
    val = ((year - 1980) << 9) | (month << 5) | day
    return struct.pack('<H', val)


def get_zip_internal_dates(zip_path: str) -> dict:
    dates = {}
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                y, mo, d, h, mi, s = info.date_time
                hex_date = msdos_date(y, mo, d).hex().upper()
                dates[info.filename] = {
                    'date': (y, mo, d),
                    'time': (h, mi, s),
                    'hex':  hex_date,
                }
    except Exception as e:
        print(f"[!] Could not read zip dates: {e}")
    return dates


def write_plain_files() -> None:
    for fname, data in VARIANTS.items():
        path = os.path.join(SCRIPT_DIR, fname)
        with open(path, 'wb') as f:
            f.write(data)
    print(f"[+] Written plain1.bin – plain4.bin ({len(list(VARIANTS.values())[0])} bytes each)")


def compute_password(props: dict) -> str:
    order = [
        'ro.product.model', 'ro.product.brand', 'ro.product.name',
        'ro.product.device', 'ro.product.board', 'ro.product.cpu.abi',
        'ro.product.cpu.abi2', 'ro.product.manufacturer',
        'ro.product.locale.language', 'ro.product.locale.region',
    ]
    tmp1 = ''.join(f"{k}={props[k]}" for k in order if k in props)

    def sha512_upper(s: str) -> str:
        return hashlib.sha512(s.encode()).hexdigest().upper()

    return sha512_upper(sha512_upper(tmp1))[10:38]


# ─── Core functions ───────────────────────────────────────────────────────────

def extract_with_keys(zip_path: str, key1: str, key2: str, key3: str) -> str:
    """Extract update.zip and otacerts.zip using known keys. Returns output dir."""
    zip_abs  = os.path.abspath(zip_path)
    zip_dir  = os.path.dirname(zip_abs)
    bkcrack  = os.path.join(SCRIPT_DIR, 'bkcrack.exe')

    extracted = {}
    for fname in ['update.zip', 'otacerts.zip']:
        out_path = os.path.join(zip_dir, fname)
        cmd = [bkcrack, '-C', zip_abs, '-c', fname,
               '-k', key1, key2, key3, '-d', out_path]
        print(f"  [~] Extracting {fname} ... ", end='', flush=True)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=120, cwd=zip_dir)
            if os.path.exists(out_path):
                size = os.path.getsize(out_path)
                print(f"OK ({size:,} bytes) → {out_path}")
                extracted[fname] = out_path
            else:
                print(f"FAILED\n{result.stdout + result.stderr}")
        except FileNotFoundError:
            print(f"\n[!] bkcrack.exe not found at: {bkcrack}")
            return zip_dir
        except subprocess.TimeoutExpired:
            print("timeout")

    # ── Unpack update.zip and otacerts.zip ───────────────────
    seven_zip = r'C:\Program Files\7-Zip\7z.exe'

    def unpack(fname, label):
        src = extracted.get(fname)
        if src and os.path.exists(src):
            out_dir = os.path.join(zip_dir, fname.replace('.zip', '_extracted'))
            if os.path.exists(seven_zip):
                print(f"\n[+] Unpacking {fname} → {out_dir}")
                os.makedirs(out_dir, exist_ok=True)
                result = subprocess.run(
                    [seven_zip, 'x', src, f'-o{out_dir}', '-y'],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    print(f"[+] {label} unpacked → {out_dir}")
                    return out_dir
                else:
                    print(f"[!] 7-Zip failed: {result.stderr}")
            else:
                print(f"\n[!] 7-Zip not found — skipping {fname}")
                print(f"    Manual: 7z x \"{src}\" -o\"{out_dir}\"")
        return None

    update_out = unpack('update.zip', 'update.zip')
    otacerts_out = unpack('otacerts.zip', 'otacerts.zip')
    _print_summary(key1, key2, key3, extracted.get('update.zip'), update_out, otacerts_out)

    return zip_dir


def _print_summary(key1, key2, key3, update_zip, update_out, otacerts_out):
    print("\n" + "=" * 55)
    print("  SUMMARY")
    print("=" * 55)
    print(f"  Keys           : {key1} {key2} {key3}")
    if update_zip:
        print(f"  update.zip     → {update_zip}")
    if update_out:
        print(f"  update_extracted → {update_out}")
    if otacerts_out:
        print(f"  otacerts_extracted → {otacerts_out}")
    print("=" * 55)


def generate_bat(zip_path: str, hex_date: str, date_str: str) -> str:
    zip_abs  = os.path.abspath(zip_path)
    bat_path = os.path.join(SCRIPT_DIR, f"crack_{hex_date}.bat")
    bkcrack  = os.path.join(SCRIPT_DIR, 'bkcrack.exe')

    lines = [
        '@echo off',
        f'cd /d "{SCRIPT_DIR}"',
        'echo ================================',
        f'echo Starting bkcrack attack',
        f'echo Date: {date_str} = {hex_date}',
        'echo ================================',
        'echo.',
    ]
    for i, pname in enumerate(VARIANTS.keys(), 1):
        plain_abs = os.path.join(SCRIPT_DIR, pname)
        lines += [
            f'echo [{i}/4] Trying {pname}...',
            f'"{bkcrack}" -C "{zip_abs}" -c otacerts.zip -p "{plain_abs}" -x 12 {hex_date}',
            'if %errorlevel% == 0 goto found',
        ]
    lines += [
        'echo.',
        'echo ================================',
        f'echo Could not find keys with date {hex_date}',
        'echo Try: python hyundai_crack.py <zip> --brute',
        'echo ================================',
        'pause', 'exit',
        ':found',
        'echo.',
        'echo ================================',
        'echo KEYS FOUND! Check output above',
        'echo ================================',
        'pause',
    ]
    with open(bat_path, 'w') as f:
        f.write('\r\n'.join(lines) + '\r\n')
    print(f"[+] Batch file written: {bat_path}")
    return bat_path


def run_bkcrack(zip_path: str, hex_date: str) -> tuple:
    """Returns (found: bool, keys: list)"""
    zip_abs  = os.path.abspath(zip_path)
    bkcrack  = os.path.join(SCRIPT_DIR, 'bkcrack.exe')

    for pname in VARIANTS.keys():
        plain_abs = os.path.join(SCRIPT_DIR, pname)
        cmd = [bkcrack, '-C', zip_abs, '-c', 'otacerts.zip',
               '-p', plain_abs, '-x', '12', hex_date,
               '-j', str(os.cpu_count())]
        print(f"  [~] {pname} + date {hex_date} ... ", end='', flush=True)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=900, cwd=os.path.dirname(zip_abs))
            output = result.stdout + result.stderr
            if 'Keys' in output and 'Could not' not in output:
                print("FOUND!")
                keys_path = os.path.join(SCRIPT_DIR, 'KEYS_FOUND.txt')
                with open(keys_path, 'w') as kf:
                    kf.write(output)
                print(f"[+] Keys saved to {keys_path}")
                # Parse keys
                for line in output.splitlines():
                    parts = line.strip().split()
                    if len(parts) == 3 and all(len(p) == 8 for p in parts):
                        return True, parts
                return True, []
            else:
                print("no match")
        except subprocess.TimeoutExpired:
            print("timeout")
        except FileNotFoundError:
            print(f"\n[!] bkcrack.exe not found at: {bkcrack}")
            return False, []
    return False, []


def brute_force(zip_path: str, years: list) -> tuple:
    for year in years:
        print(f"\n[*] Brute-forcing year {year} ...")
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                hex_date = msdos_date(year, month, day).hex().upper()
                found, keys = run_bkcrack(zip_path, hex_date)
                if found:
                    return True, keys
    return False, []


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Hyundai iGAS Firmware ZipCrypto Cracker')
    parser.add_argument('zip', nargs='?', help='Path to update_package.zip')
    parser.add_argument('--year', type=int, nargs='+', help='Year(s) to brute-force')
    parser.add_argument('--brute', action='store_true', help='Run brute-force after auto attempt')
    parser.add_argument('--bat-only', action='store_true', help='Only generate .bat file')
    parser.add_argument('--password', action='store_true', help='Compute ZIP password from build.prop values')
    args = parser.parse_args()

    print("=" * 55)
    print("  Hyundai iGAS Firmware Cracker")
    print("  Reference: xakcop.com/post/hyundai-hack/")
    print("=" * 55)

    # ── Interactive: check if user already has keys ───────────
    if not args.password:
        print("\nDo you already have keys from a previous attack?")
        has_keys = input("  Enter keys (e.g. 'aabbccdd 11223344 55667788') or press Enter to skip: ").strip()
        if has_keys:
            parts = has_keys.split()
            if len(parts) == 3 and args.zip:
                print(f"\n[+] Using provided keys: {' '.join(parts)}")
                extract_with_keys(args.zip, parts[0], parts[1], parts[2])
                return
            else:
                print("[!] Invalid keys format. Starting crack...")

    # ── Password calculator mode ──────────────────────────────
    if args.password:
        print("\n[Password Calculator]")
        print("Enter build.prop values:\n")
        keys_list = [
            'ro.product.model', 'ro.product.brand', 'ro.product.name',
            'ro.product.device', 'ro.product.board', 'ro.product.cpu.abi',
            'ro.product.cpu.abi2', 'ro.product.manufacturer',
            'ro.product.locale.language', 'ro.product.locale.region',
        ]
        props = {}
        for k in keys_list:
            val = input(f"  {k} = ").strip()
            if val:
                props[k] = val
        print(f"\n[+] ZIP Password: {compute_password(props)}")
        return

    if not args.zip:
        parser.print_help()
        return

    zip_path = args.zip
    if not os.path.exists(zip_path):
        print(f"[!] File not found: {zip_path}")
        sys.exit(1)

    print(f"\n[1] Reading internal dates from: {zip_path}")
    dates_info = get_zip_internal_dates(zip_path)
    for fname, info in dates_info.items():
        y, mo, d = info['date']
        h, mi, s = info['time']
        print(f"    {fname}: {y}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{s:02d}  hex={info['hex']}")

    target   = dates_info.get('otacerts.zip') or list(dates_info.values())[0]
    y, mo, d = target['date']
    hex_date = target['hex']
    months   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    date_str = f"{d:02d} {months[mo-1]} {y}"
    print(f"\n[+] Using date: {date_str} → {hex_date}")

    print("\n[2] Writing plain*.bin files ...")
    write_plain_files()

    print(f"\n[3] Generating batch file ...")
    generate_bat(zip_path, hex_date, date_str)

    if args.bat_only:
        print("\n[*] --bat-only: done.")
        return

    print(f"\n[4] Running bkcrack with date {hex_date} ...")
    found, keys = run_bkcrack(zip_path, hex_date)

    if not found and args.brute:
        years = args.year if args.year else [y - 1, y, y + 1]
        print(f"\n[5] Brute-force years: {years}")
        found, keys = brute_force(zip_path, years)

    if found and keys:
        print(f"\n[+] Keys: {' '.join(keys)}")
        print("\n[6] Extracting files ...")
        extract_with_keys(zip_path, keys[0], keys[1], keys[2])
    elif not found:
        print("\n[!] Keys not found.")
        print("    Try: python hyundai_crack.py <zip> --brute --year 2020 2025 2026")


if __name__ == '__main__':
    main()
