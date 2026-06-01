# Hyundai iGAS Firmware Tools

Tools for analyzing and decrypting Hyundai iGAS (Gen5) head unit firmware update packages.

## Background

Hyundai iGAS head units use ZipCrypto encryption for firmware update packages (`update_package.zip`). This tool implements a known-plaintext attack to recover the encryption keys, based on the research documented at [xakcop.com/post/hyundai-hack/](https://xakcop.com/post/hyundai-hack/).

## Requirements

- Python 3.8+
- [bkcrack](https://github.com/kimci86/bkcrack) — place `bkcrack.exe` in the same folder as the script
- [7-Zip](https://www.7-zip.org/) — installed at default path (`C:\Program Files\7-Zip\7z.exe`)

## Usage

### Basic — auto-detect date and crack:
```cmd
python hyundai_crack.py update_package.zip
```

### Already have keys from a previous run:
```cmd
python hyundai_crack.py update_package.zip
# When prompted, enter: aabbccdd 11223344 55667788
```

### Generate .bat file only (no cracking):
```cmd
python hyundai_crack.py update_package.zip --bat-only
```



## How It Works

1. Reads internal file dates from `update_package.zip`
2. Converts date to MS-DOS hex format (used as known plaintext)
3. Generates `plain*.bin` files (ZIP local file header variants)
4. Runs bkcrack known-plaintext attack
5. Extracts `update.zip` and `otacerts.zip` using recovered keys
6. Unpacks `update.zip` → `update_extracted/`
7. Unpacks `otacerts.zip` → `otacerts_extracted/` (contains RSA public key)

## Plain File Variants

```
plain1.bin: 504b0304 1400 0000 0000  (store,   version 14)
plain2.bin: 504b0304 1400 0000 0800  (deflate, version 14)
plain3.bin: 504b0304 0a00 0000 0000  (store,   version 0a)
plain4.bin: 504b0304 0a00 0000 0800  (deflate, version 0a)
```

## ZIP Password Formula

The firmware ZIP password is derived from Android system properties:

```python
tmp1 = "ro.product.model=X" + "ro.product.brand=X" + ...
password = SHA512(SHA512(tmp1))[10:38]
```

## Known Keys & Passwords

| Firmware | Date | Keys | Password |
|---|---|---|---|
| V119 KOR | 31 Jul 2020 | `9932e869 a3deb24d c6838559` | — |
| V141 MES | 16 Jun 2025 | `7c629412 1b648727 7125c267` | `9659752E23D1D9982B8B9A642CC9` |
| V141 KOR | 14 Jan 2026 | `43043bc0 37d3884a ef0cc88c` | `DE4453F2728293C3A5B3026051FB` |

## Supported Vehicles

- Hyundai Grandeur (iGAS, Gen5)
- Hyundai Azera (iGAS, Gen5)

## References

- [How I Hacked my Car — Programming With Style](https://programmingwithstyle.com/posts/howihackedmycarpart5/)
- [bkcrack — ZipCrypto known-plaintext attack](https://github.com/kimci86/bkcrack)

## Disclaimer

For educational and personal vehicle use only. Use responsibly.
