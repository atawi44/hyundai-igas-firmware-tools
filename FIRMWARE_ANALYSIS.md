# Ultimate Firmware Analysis Report: `STDGEN5\kor\hyundaiD`

This report provides a comprehensive, low-level technical examination of the Hyundai Gen5 Standard Navigation firmware files located inside `STDGEN5\kor\hyundaiD\`.

---

## 📁 Directory Structure Overview

The `hyundaiD` directory represents the firmware payload for a specific Standard Gen5 vehicle head unit variant (running Android on a Telechips SoC). Below is the analyzed file layout:

```text
STDGEN5\kor\hyundaiD\update\
├── info.ini                     # Encrypted metadata/signature information
├── update.ini                   # Plaintext update instruction sheet
├── checksum                     # SHA-512 cryptographic hashes for all files
│
├── system\                      # System OS update partition
│   ├── update_package.zip       # Main update container (266.1 MB)
│   ├── qb_data.sparse.img       # Quick Boot sparse image (5.3 MB)
│   ├── vr.inf                   # Voice Recognition (VR) configuration
│   ├── vr.md5                   # MD5 hash of the voice recognition bundle
│   └── vr.sha                   # SHA hash of the voice recognition bundle
│
├── gps\                         # Global Positioning System update
│   ├── gps.inf                  # GPS metadata definition
│   └── gps_module.bin           # GPS firmware binary (561.7 KB)
│
├── micom\                       # Microcontroller updates (IG & IG Hybrid)
│   ├── ig\
│   │   ├── micom.inf
│   │   └── micom_sw.bin
│   └── ighev\
│       ├── micom.inf
│       └── micom_sw.bin         # MICOM software binary (1.0 MB)
│
└── modem\                       # Qualcomm MSM9615 Baseband updater files
    ├── partition.mbn            # Flash partition table
    ├── sbl1.mbn                 # Secondary Bootloader 1
    ├── sbl2.mbn                 # Secondary Bootloader 2
    ├── rpm.mbn                  # Resource Power Manager firmware
    ├── appsboot.mbn             # Android Apps bootloader (lk)
    ├── boot-oe-msm9615.img      # Modem kernel image
    ├── 9615-cdp-image-*.yaffs2  # Base modem rootfs (YAFFS2 filesystem)
    ├── 9615-cdp-usr-*.yaffs2    # Base modem usrfs (YAFFS2 filesystem)
    ├── dsp1_D_KT.mbn            # DSP modem images for KT Network (Korea)
    ├── dsp2_D_KT.mbn
    ├── dsp3_D_KT.mbn
    ├── NPRG9x15.hex             # Qualcomm programmer hex tool
    ├── modem.inf                # Modem partition list definitions
    └── modem_version.txt        # Plaintext modem version strings
```

---

## ⚙️ Plaintext Configuration Sheet (`update.ini`)

The file `update.ini` governs the update logic processed by the head unit's updater engine. 

### Key Properties
| Property | Value | Description |
| :--- | :--- | :--- |
| `CONFIG_PRODUCT_MODEL_TYPE` | `1` | Denotes standard system type. |
| `CONFIG_PRODUCT_SW_VERSION` | `HYUNDAID.KOR.0000.V141.260114` | The target Software version (released around Jan 14, 2026). |
| `CONFIG_SYSTEM_UPDATE_TYPE` | `1` | Enables complete System update sequence. |
| `CONFIG_MODEM_UPDATE_TYPE` | `1` | Triggers Qualcomm modem flash. |
| `CONFIG_GPS_UPDATE_TYPE` | `1` | Triggers GPS module update. |
| `CONFIG_MICOM_UPDATE_TYPE` | `1` | Triggers Microcontroller (MICOM) update. |
| `VENDOR_CODE` | `1` | Vendor mapping (`0` = Kia, `1` = Hyundai). |

### Partition Update Flag Array
The installation checklist specifies which partitions/components are targeted for this product type (`$hyundaiD_KOR`):
```ini
// 1.SYSTEM  2.DAB  3.MODEM  4.GPS  5.DMB  6.EXT.KEYBOARD  7.HDRADIO  8.SXM  9.EXT.CDP  10.MICOM 
$hyundaiD_KOR : {1, 0, 1, 1, 0, 0, 0, 0, 0, 1}
```

### Data Backup List
During the update, the system backs up configuration and application states for the following packages to preserve user preferences:
* **Core Bluelink / Telematics:** `com.hkmc.telematics`, `com.hkmc.telematics.app.ev`, `com.hkmc.telematics.app.phev`
* **Navigation App:** `com.mnsoft.navi`
* **Connectivity & Media:** `com.android.bluetooth`, `com.SoundHound`, `com.daudio.av.app.cmmb`
* **System Utilities & Settings:** `com.android.settings`, `com.android.providers.contacts`, `com.hkmc.system.app.homesetting`
* **AI & Keyboard:** `com.Kakaoi` (Kakao i voice assistant), `com.android.inputmethod.korean`, `com.android.inputmethod.latin`

---

## 🔒 Deep-Dive Analysis of the System Update Component

### System Update Package (`system\update_package.zip`)
Analyzing the inner file structure of `update_package.zip` (266,142,893 bytes):
* **`otacerts.zip`** (1,203 bytes): Holds standard Android X.509 OTA certificates used to authenticate the package signatures during the recovery phase.
* **`update.zip`** (266,141,312 bytes): The actual core OS file system bundle.

### Encryption Metadata Analysis
By inspecting the zip directory headers for the nested `update.zip`, we discovered the following details:
```text
File name: update.zip
Uncompressed size: 266141312 bytes
Compressed size:   266141324 bytes
Compression type:  0 (Stored / Uncompressed)
Flag bits:         9 (Bit 0 = Encrypted; Bit 3 = Data Descriptor present)
```
> [!IMPORTANT]
> The size difference between `Compressed size` and `Uncompressed size` is **exactly 12 bytes**. 
> This is the exact signature of **Traditional PKWARE ZipCrypto** encryption. It indicates that the files rely on standard legacy zip encryption.
>
> Using your ZipCrypto internal keys (**`43043bc0 37d3884a ef0cc88c`**), we successfully bypassed the password barrier and completely decrypted `update.zip` and `otacerts.zip`!

---

## 🛠️ Extracted System OS Partition (`system.ext4`)

We successfully extracted the core Linux filesystem partition (`system.ext4`, 453 MB) to detail its internal Android architecture.

### Extracted Directory tree
```text
system_extracted\
├── app2\                      # User-space Android system applications
│   ├── HKMC_Climate.apk       # Vehicle HVAC / climate management service
│   └── Settings.apk           # Head unit settings app
├── framework\                 # Core Java libraries and resources
│   ├── framework-res.apk      # System base resources
│   ├── hkmc-res.apk           # Hyundai/Kia brand resource package
│   ├── automotive.jar         # Proprietary vehicle communication interfaces
│   ├── automotive-service.jar # High-level vehicle system services (5.4 MB)
│   └── com.infobank.jar       # Telematics / Infobank integration library
├── onebin\                    # Multi-variant configurations overrides
│   ├── ig_kr\                 # Grandeur Gasoline/Diesel specific definitions
│   └── ighev_kr\              # Grandeur Hybrid specific definitions
├── lost+found\
└── build.prop                 # Global system environment parameters
```

### Variant Customizations (`onebin/`)
Depending on the specific Grandeur chassis type detected at installation, the system applies overriding properties defined in `onebin/`:
* **`ighev_kr/mobis.prop` (Grandeur Hybrid):**
  ```properties
  ro.product.name=ighev_kr
  ro.product.device=daudioplus_ighev_kr
  ro.product.vehicleinfo1=IGAH (IG Grandeur Hybrid)
  ro.product.opt.hybrid_vr=true
  ro.daudio.telematics.features=1111001111011111111011
  ```
* **`ig_kr/mobis.prop` (Grandeur Gasoline/Diesel):**
  ```properties
  ro.product.name=ig_kr
  ro.product.device=daudioplus_ig_kr
  ro.product.vehicleinfo1=IGAS (IG Grandeur Standard)
  ro.daudio.telematics.features=1110001111111111111011
  ```

### Calculated Head Unit ZIP Password
Using the values discovered in the primary `build.prop` file:
* **Product Model:** `daudioplus`
* **Product Brand:** `hyundai`
* **Product Name:** `hyundaiD_kr`
* **Product Device:** `daudioplus_hyundaiD_kr`
* **Board:** `daudio`
* **CPU ABIs:** `armeabi-v7a` & `armeabi`
* **Manufacturer:** `mobis`
* **Locale:** `ko_KR`

The Mobis double-SHA512 zip password hashing generates the exact archive password:
👉 **`DE4453F2728293C3A5B3026051FB`**

---

## 🔏 Cryptographic OTA Signature (`otacerts.zip`)

The package contains `daudio.x509.pem`, which holds the public key used by the Android bootloader/recovery to verify updates:

* **Issuer/Subject Details:**
  * `C = KR` (South Korea)
  * `ST = Gyeonggi-Do`
  * `L = Yongin-Si`
  * `O = Hyundai Mobis Co., Ltd.`
  * `OU = Multi SW Platform Engr`
  * `CN = Daudio`
  * `Email = bslim@mobis.co.kr`
* **Validity Period:** April 7, 2015 – August 23, 2042
* **Algorithm:** RSA 2048-bit with SHA-1 signature

---

## 📦 OEM Variant Resources (`BIN\G40\*.npkg`)

In the vehicle variant binary configuration folder `BIN\G40\`, we discovered custom resource archives utilizing the **`.npkg`** extension (such as `oem_std5_ecn_kmc.npkg`, 34.6 MB).

Our header inspection reveals a proprietary format:
* **Magic Bytes:** `50524e4d` (ASCII: **`PRNM`**)
* **Header Metadata:** Includes a clear plaintext timestamp: `2025/07/02 17:05:55`.
* **Nature:** These are encrypted map-render libraries and base resource bundles loaded dynamically by the navigation software on runtime.
