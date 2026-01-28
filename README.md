# Multiarch GNU Toolchain Conan Package

A Conan tool package for the GNU GCC Toolchain, providing both native compilation
(`gcc`, `g++`) and ARM cross-compilation (`arm-none-eabi-gcc`). By adding this
tool package to your Conan build profile, your project can leverage GCC for
development across multiple platforms and architectures.

## ✨ Key Features

- **Unified toolchain**: Single package provides both native GCC and ARM
  cross-compiler
- **Automatic selection**: Correct toolchain variant chosen based on target
  OS/architecture
- **Embedded ARM support**: Built-in support for ARM Cortex-M microcontrollers
- **Native compilation**: Full GCC support for Linux and Windows
- **Optimized binaries**: Native GCC from xpack-dev-tools, ARM cross-compiler
  from official ARM releases

## 📋 Supported Versions & Platforms

All binaries are downloaded from official sources:

- Native GCC from [xpack-dev-tools](https://github.com/xpack-dev-tools/gcc-xpack/releases)
- ARM cross-compiler from [ARM GNU Toolchain](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads)

### GCC 14

#### Native Compilation (Host Platforms)

| Platform | x86_64 | ARM64 |
|----------|--------|-------|
| Linux    | ✅     | ✅    |
| Windows  | ✅     | ❌    |

> [!NOTE]
> Native compilation (building executables for your host OS) is only supported
> on Linux and Windows. macOS is not supported for native compilation.

#### ARM Cross-Compilation (Build Platforms)

The following platforms can cross-compile for ARM Cortex-M targets:

| Platform | x86_64 | ARM64 |
|----------|--------|-------|
| Linux    | ✅     | ✅    |
| macOS    | ✅     | ✅    |
| Windows  | ✅     | ❌    |

## 🚀 Quick Start

To use the Multiarch GNU Toolchain for your application, install the pre-made
compiler profiles to your local `conan2` cache:

```bash
conan config install -sf conan/profiles/v1 -tf profiles https://github.com/libhal/multiarch-gnu-toolchain.git
```

This provides profiles accessible via `-pr gcc-14`. These profiles only include
compiler information. You'll need a "target" profile to actually build something.

### Native Development

For native development on your host platform, the `gcc-14` profile automatically
detects your OS and architecture:

```bash
# Build for your current platform (auto-detected)
conan build demos/cpp -pr:a gcc-14
```

### ARM Cortex-M Cross-Compilation

For embedded ARM Cortex-M development:

```bash
# Cortex-M4 with hardware floating point
conan build demos/cpp -pr:a gcc-14 -pr cortex-m4f

# Cortex-M7 with double-precision FPU
conan build demos/cpp -pr:a gcc-14 -pr cortex-m7d

# Cortex-M33 with hardware floating point
conan build demos/cpp -pr:a gcc-14 -pr cortex-m33f
```

## 🔗 Adding as a Dependency

For this tool package to work correctly, the toolchain **MUST** be added as a
dependency using `tool_requires` in at least one profile.

```jinja2
[settings]
compiler=gcc
compiler.cppstd=23
compiler.libcxx=libstdc++11
compiler.version=14

[tool_requires]
multiarch-gnu-toolchain/14
```

By adding `multiarch-gnu-toolchain/14` to your profile, every dependency will
use this toolchain for compilation. The tool package should NOT be directly
added to an application's `conanfile.py`.

### ARM Cortex-M Examples

For ARM Cortex-M4 with hardware floating point:

```plaintext
[settings]
arch=cortex-m4f
build_type=Release
os=baremetal
```

For ARM Cortex-M7 with double-precision FPU:

```plaintext
[settings]
arch=cortex-m7d
build_type=Release
os=baremetal
```

## 🧾 Using Pre-made Profiles

Install profiles into your local Conan cache:

```bash
conan config install -sf conan/profiles/v1 -tf profiles https://github.com/libhal/multiarch-gnu-toolchain.git
```

Or from a locally cloned repo:

```bash
conan config install -sf conan/profiles/v1 -tf profiles .
```

All profiles use `libstdc++11` as this is the latest GCC C++ ABI.

## 📦 Building & Installing the Tool Package

When you create the package, it downloads the appropriate compiler variant from
official releases based on your build and target settings, then stores it in
your local Conan package cache:

```bash
# For host platform development (native build)
conan create all --version=14 --build-require

# For ARM Cortex-M cross-compilation
conan create all --version=14 --build-require -pr:h gcc-14 -pr cortex-m4f
```

## 🎛️ Options

Example profile options:

```plaintext
[options]
multiarch-gnu-toolchain/*:default_arch=True
multiarch-gnu-toolchain/*:lto=True
multiarch-gnu-toolchain/*:fat_lto=True
multiarch-gnu-toolchain/*:function_sections=True
multiarch-gnu-toolchain/*:data_sections=True
multiarch-gnu-toolchain/*:gc_sections=True
multiarch-gnu-toolchain/*:default_libc=True
```

### `local_path` (Default: `""`)

Path to a local GCC toolchain directory. If not empty, the recipe will use this
path instead of downloading the official toolchain. Useful for custom-built
toolchains or alternative binary sources.

```bash
conan create all --version 14 -o "*:local_path=/path/to/gcc-toolchain/"
```

### `default_arch` (Default: `True`)

Automatically inject appropriate `-mcpu` and `-mfloat-abi` flags for the `arch`
defined in your build target profile.

Examples for ARM Cortex-M:

- For `cortex-m4`:
  - `-mcpu=cortex-m4`
  - `-mfloat-abi=soft`
- For `cortex-m4f`:
  - `-mcpu=cortex-m4`
  - `-mfloat-abi=hard`
  - `-mfpu=fpv4-sp-d16`

### `lto` (Default: `False` for GCC 14)

Enable Link-Time Optimization with `-flto`.

> [!WARNING]
> LTO is disabled by default for GCC 14 for ARM embedded targets. ZSTD LTO
> compression support is enabled for the Linux ARM toolchain but not for macOS.
> This causes errors when object files built on Linux are linked on macOS:
>
> ```plaintext
> lto1: fatal error: compiler does not support ZSTD LTO compression
> compilation terminated.
> ```

### `fat_lto` (Default: `True`)

Enable `-ffat-lto-objects` for compatibility with linkers that don't support LTO.
This option is ignored if `lto` is not enabled.

### `function_sections` (Default: `True`)

Enable `-ffunction-sections` to place each function in its own section for
better garbage collection at link time.

### `data_sections` (Default: `True`)

Enable `-fdata-sections` to place each data item in its own section for better
garbage collection at link time.

### `gc_sections` (Default: `True`)

Enable garbage collection of unused sections. Uses `-Wl,--gc-sections` linker
flag.

### `default_libc` (Default: `True`)

Inject `--specs=nosys.specs` to linker arguments. This provides weak stubs for
newlib libc APIs like `exit()`, `kill()`, `sbrk()`, allowing binaries to link
without defining all libc APIs upfront.

### `lto_compression_level` (Default: `0`)

Compression level for LTO objects. Accepts 0-19 for zstd or 0-9 for zlib.

## 🎯 Supported ARM Cortex-M Targets

The following embedded ARM Cortex-M architectures are fully supported:

- cortex-m0
- cortex-m0plus
- cortex-m1
- cortex-m3
- cortex-m4
- cortex-m4f
- cortex-m7
- cortex-m7f
- cortex-m7d
- cortex-m23
- cortex-m33
- cortex-m33f
- cortex-m35p
- cortex-m35pf
- cortex-m55
- cortex-m85

> [!NOTE]
> The architecture names may have trailing characters indicating floating point
> support:
>
> - `f` indicates single precision (32-bit) hard float
> - `d` indicates double precision (64-bit) hard float

## ✨ Adding New Versions of GCC

If you'd like to add support for a new GCC version, follow these instructions
(replace `XY.Z` with the correct version):

### 1. Update `config.yml`

Add the version to `/config.yml`:

```yaml
versions:
  "14":
    folder: "all"
  "XY.Z":
    folder: "all"
```

### 2. Add Workflow File

Add `.github/workflows/XY.Z.yml`:

```yaml
name: 🚀 XY.Z Deploy

on:
  workflow_dispatch:
  pull_request:
  push:
    branches:
      - main

jobs:
  deploy:
    uses: ./.github/workflows/deploy.yml
    with:
      version: "XY.Z"
    secrets: inherit
```

### 3. Add Profile

Add profile `gcc-XY.Z` to `/conan/profiles/v1/`:

```jinja2
{% set detected_os = detect_api.detect_os() %}
{% set detected_arch = detect_api.detect_arch() %}

[settings]
os={{ detected_os }}
arch={{ detected_arch }}
build_type=Release
compiler=gcc
compiler.cppstd=23
compiler.libcxx=libstdc++11
compiler.version=XY

[tool_requires]
multiarch-gnu-toolchain/XY.Z
```

### 4. Update `conandata.yml`

Add download URLs and SHA256 checksums for native and ARM cross-compiler
binaries in `all/conandata.yml`:

```yaml
sources:
  "XY.Z":
    "native":
      "Linux":
        "x86_64":
          url: ""
          sha256: ""
        "armv8":
          url: ""
          sha256: ""
      "Windows":
        "x86_64":
          url: ""
          sha256: ""
    "arm-none-eabi":
      "Linux":
        "x86_64":
          url: ""
          sha256: ""
        "armv8":
          url: ""
          sha256: ""
      "Macos":
        "x86_64":
          url: ""
          sha256: ""
        "armv8":
          url: ""
          sha256: ""
      "Windows":
        "x86_64":
          url: ""
          sha256: ""
```

### 5. Test the Package

```bash
# Test native build
conan create all --version=XY.Z --build-require

# Test ARM cross-compilation
conan create all --version=XY.Z --build-require -pr:h gcc-XY.Z -pr cortex-m4f
```

### 6. Submit a Pull Request

Submit a PR with title `:sparkles: Add support for GCC XY.Z`.

## 🔖 Interpreting Versions

The package version represents the major GCC version. For example, version "14"
uses GCC 14.2.0 binaries.

## 🤝 Contributing

Contributions are welcome! Please ensure:

1. All tests pass on supported platforms
2. Documentation is updated for new features
3. Profiles are added for new versions

## 📄 License

This project is licensed under the Apache 2.0 License - see the LICENSE file
for details.
