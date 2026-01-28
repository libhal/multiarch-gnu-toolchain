#!/usr/bin/python
#
# Copyright 2024 - 2025 Khalil Estell and the libhal contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import shutil
from pathlib import Path
from conan import ConanFile
from conan.tools.files import get
from conan.errors import ConanInvalidConfiguration


required_conan_version = ">=2.0.0"


class MultiarchGNUToolchainPackage(ConanFile):
    name = "multiarch-gnu-toolchain"
    license = ("GPL-3.0-only", "GPL-2.0-only", "BSD-3-Clause",
               "BSD-2-Clause-FreeBSD", "AGPL-3.0-only", "BSD-2-Clause")
    url = "https://github.com/libhal/multiarch-gnu-toolchain"
    homepage = "https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads"
    description = "GCC Multiarch Toolchain for native and cross-compilation"
    topics = ("gcc", "compiler", "embedded", "arm", "cortex", "native",
              "linux", "macos", "windows", "cross-compilation")
    settings = "os", "arch", "compiler", "build_type"
    package_type = "application"
    build_policy = "missing"
    upload_policy = "skip"

    options = {
        "local_path": ["ANY"],
        "default_arch": [True, False],
        "lto": [True, False],
        "fat_lto": [True, False],
        "function_sections": [True, False],
        "data_sections": [True, False],
        "gc_sections": [True, False],
        "default_libc": [True, False],
        "lto_compression_level": ["ANY"],
    }

    default_options = {
        "local_path": "",
        "default_arch": True,
        # "lto" default set in config_options()
        "fat_lto": True,
        "function_sections": True,
        "data_sections": True,
        "gc_sections": True,
        "default_libc": True,
        "lto_compression_level": "0",
    }

    options_description = {
        "local_path": "Provide a path to your local GCC Toolchain. If not set, the official toolchain is downloaded.",
        "default_arch": "Automatically inject architecture appropriate -mcpu and -mfloat-abi arguments into compilation flags for ARM targets.",
        "lto": "Enable LTO support in binaries and intermediate files (.o and .a files)",
        "fat_lto": "Enable linkers without LTO support to still build with LTO enabled binaries. This adds both LTO information and compiled code into the object and archive files. This option is ignored if the `lto` option is False",
        "function_sections": "Enable -ffunction-sections which splits each function into their own subsection allowing link time garbage collection.",
        "data_sections": "Enable -fdata-sections which splits each statically defined block memory into their own subsection allowing link time garbage collection.",
        "gc_sections": "Enable garbage collection at link stage. Only useful if at least function_sections and data_sections is enabled.",
        "default_libc": "For ARM targets: Link against `nosys` libc specification via `--specs=nosys.specs`. Provides weak stubs for newlib libc APIs.",
        "lto_compression_level": "LTO compression level (0-19 for zstd, 0-9 for zlib). Only meaningful with LTO enabled.",
    }

    LOCAL_PATH_TXT = "local_path.txt"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def config_options(self):
        """Set LTO default based on compiler version"""
        # Disable LTO for GCC 14 due to ZSTD compression incompatibilities
        # between different build environments (Linux/macOS/Windows)
        if self.settings_target:
            COMPILER_VERSION = str(
                self.settings_target.get_safe("compiler.version", ""))
            if COMPILER_VERSION.startswith("14"):
                self.output.debug(
                    "Disabling LTO for GCC 14 (ZSTD incompatibility)")
                self.options.lto = False
            else:
                self.output.debug("Enabling LTO for GCC")
                self.options.lto = True

    def validate(self):
        supported_build_operating_systems = ["Linux", "Macos", "Windows"]
        if not self._settings_build.os in supported_build_operating_systems:
            raise ConanInvalidConfiguration(
                f"The build os '{self._settings_build.os}' is not supported. "
                "Pre-compiled binaries are only available for "
                f"{supported_build_operating_systems}."
            )

        supported_build_architectures = {
            "Linux": ["armv8", "x86_64"],
            "Macos": ["armv8", "x86_64"],
            "Windows": ["armv8", "x86_64"],
        }

        if (
            not self._settings_build.arch
            in supported_build_architectures[str(self._settings_build.os)]
        ):
            build_os = str(self._settings_build.os)
            raise ConanInvalidConfiguration(
                f"The build architecture '{self._settings_build.arch}' "
                f"is not supported for {self._settings_build.os}. "
                "Pre-compiled binaries are only available for "
                f"{supported_build_architectures[build_os]}."
            )

        # Validate LTO compression level
        try:
            LVL = int(self.options.lto_compression_level)
            if LVL < 0 or LVL > 19:
                raise ConanInvalidConfiguration(
                    f"lto_compression_level must be between 0-19, got {LVL}"
                )
        except ValueError:
            LVL = self.options.lto_compression_level
            raise ConanInvalidConfiguration(
                f"lto_compression_level must be an integer, got '{LVL}'"
            )

        # Validate version-variant compatibility
        if self.settings_target:
            variant = self._determine_gcc_variant()
            try:
                available_variants = list(
                    self.conan_data['sources'][self.version].keys())
                if variant not in available_variants:
                    target_arch = self.settings_target.get_safe('arch')
                    target_os = self.settings_target.get_safe('os')
                    raise ConanInvalidConfiguration(
                        f"Version {self.version} does not support the '{variant}' variant "
                        f"required for target {target_os}/{target_arch}. "
                        f"Available variants for {self.version}: {available_variants}."
                    )
            except KeyError:
                raise ConanInvalidConfiguration(
                    f"Version {self.version} is not defined in conandata.yml"
                )

    def source(self):
        pass

    def build(self):
        pass

    def _determine_gcc_variant(self):
        """Determine which GCC variant to download based on target architecture"""
        if not self.settings_target:
            # Native build - no cross-compilation target specified
            self.output.debug("Using native GCC binary")
            return "native"

        TARGET_OS = self.settings_target.get_safe("os")
        TARGET_ARCH = self.settings_target.get_safe("arch")

        self.output.debug(
            f"target: os: '{TARGET_OS}', architecture: '{TARGET_ARCH}'")

        # ARM Cortex-M baremetal targets use ARM cross-compiler
        if TARGET_OS == "baremetal" and TARGET_ARCH in [
            "cortex-m0", "cortex-m0plus", "cortex-m1",
            "cortex-m3", "cortex-m4", "cortex-m4f",
            "cortex-m7", "cortex-m7f", "cortex-m7d",
            "cortex-m23", "cortex-m33", "cortex-m33f",
            "cortex-m35p", "cortex-m35pf",
            "cortex-m55", "cortex-m85",
        ]:
            self.output.debug("Using ARM GCC cross-compiler (arm-none-eabi)")
            return "arm-none-eabi"

        # Native OS targets (Linux, macOS, Windows) use native GCC
        if TARGET_OS in ["Linux", "Macos", "Windows"]:
            self.output.debug("Using native GCC binary")
            return "native"

        # Fallback to native
        self.output.debug("Defaulting to native GCC binary")
        return "native"

    def package(self):
        # Use local path if specified
        if self.options.local_path:
            self._package_local_path()
            return

        VARIANT = self._determine_gcc_variant()
        BUILD_OS = str(self._settings_build.os)
        BUILD_ARCH = str(self._settings_build.arch)

        self.output.info(f'VARIANT: {VARIANT}')
        self.output.info(f'BUILD_OS: {BUILD_OS}, BUILD_ARCH: {BUILD_ARCH}')

        URL = self.conan_data["sources"][self.version][VARIANT][BUILD_OS][BUILD_ARCH]["url"]
        SHA256 = self.conan_data["sources"][self.version][VARIANT][BUILD_OS][BUILD_ARCH]["sha256"]

        get(self, URL, sha256=SHA256, strip_root=True,
            destination=self.package_folder)

        if (not (Path(self.package_folder) / "bin").exists() and
                BUILD_OS == "Macos"):
            # Handle Macos case: move contents of versioned folder (e.g., 14.3.0) to root
            package_folder = Path(self.package_folder)

            # Find any folder that starts with "14"
            versioned_folders = [
                f for f in package_folder.iterdir()
                if f.is_dir() and f.name.startswith(self.version)]

            if versioned_folders:
                # Move contents of the first matching folder to root
                versioned_folder = versioned_folders[0]
                self.output.info(
                    f"Moving contents from {versioned_folder} to root")

                for item in versioned_folder.iterdir():
                    if item.is_dir():
                        shutil.move(str(item), str(package_folder / item.name))
                    else:
                        shutil.move(str(item), str(package_folder / item.name))

                # Remove the now-empty versioned folder
                shutil.rmtree(versioned_folder)

            # Create symlinks in bin directory for files ending with version
            # suffix
            bin_folder = package_folder / "bin"
            if bin_folder.exists():
                # Get the major version (e.g., "14" from "14.3.0")
                major_version = self.version.split(
                    '.')[0] if '.' in self.version else self.version

                # Create symlinks for files ending with the major version
                for item in bin_folder.iterdir():
                    if item.is_file() and item.name.endswith(f"-{major_version}"):
                        # Remove the version suffix from the filename (e.g., "gcc-14" -> "gcc")
                        symlink_name = item.name[:-len(f"-{major_version}")]

                        # Create symlink
                        symlink_path = bin_folder / symlink_name
                        if not symlink_path.exists():
                            try:
                                symlink_path.symlink_to(item.name)
                                self.output.info(
                                    f"Created symlink: {symlink_name} -> {item.name}")
                            except OSError as e:
                                self.output.warn(
                                    f"Failed to create symlink {symlink_name}: {e}")

    def _package_local_path(self):
        """Package using a local toolchain installation"""
        LOCAL_PATH = str(self.options.local_path)
        self.output.info(f"Using local toolchain: {LOCAL_PATH}")
        (Path(self.package_folder) / self.LOCAL_PATH_TXT).write_text(LOCAL_PATH)

    def _get_bin_path(self) -> Path:
        """Get the bin directory path, handling local_path option"""
        LOCAL_PATH_FILE = Path(self.package_folder) / self.LOCAL_PATH_TXT
        if LOCAL_PATH_FILE.exists():
            self.output.info("Using binaries from local_path")
            return Path(LOCAL_PATH_FILE.read_text()) / "bin"
        else:
            self.output.info("Using downloaded binaries")
            return Path(self.package_folder) / "bin"

    def _setup_bin_dirs(self):
        """Configure binary directories"""
        BIN_PATH = self._get_bin_path()
        self.cpp_info.bindirs = [str(BIN_PATH)]
        self.output.info(f"bindirs: {self.cpp_info.bindirs}")

    def package_info(self):
        VARIANT = self._determine_gcc_variant()

        if VARIANT == "native":
            self._configure_native_gcc()
        elif VARIANT == "arm-none-eabi":
            self._configure_arm_gcc()

    def _configure_native_gcc(self):
        """Configure native GCC toolchain for Linux/macOS/Windows targets"""
        self.cpp_info.includedirs = []

        self.conf_info.define("tools.build:compiler_executables", {
            "c": "gcc",
            "cpp": "g++",
            "asm": "gcc",
        })

        # Determine target OS
        if self.settings_target:
            target_os = self.settings_target.get_safe('os')
        else:
            target_os = str(self.settings.os)

        # Set CMake system name based on target OS
        if target_os == "Linux":
            self.conf_info.define(
                "tools.cmake.cmaketoolchain:system_name", "Linux")
        elif target_os == "Macos":
            self.conf_info.define(
                "tools.cmake.cmaketoolchain:system_name", "Darwin")
        elif target_os == "Windows":
            self.conf_info.define(
                "tools.cmake.cmaketoolchain:system_name", "Windows")

        # Tell CMake that native binaries can run on this machine
        self.conf_info.define("tools.build.cross_building:can_run", True)

        # CMake extra variables for native GCC
        self.conf_info.define("tools.cmake.cmaketoolchain:extra_variables", {
            "CMAKE_C_COMPILER": "gcc",
            "CMAKE_CXX_COMPILER": "g++",
            "CMAKE_ASM_COMPILER": "gcc",
            "CMAKE_AR": "ar",
            "CMAKE_RANLIB": "ranlib",
            "CMAKE_STRIP": "strip",
            "CMAKE_OBJCOPY": "objcopy",
            "CMAKE_OBJDUMP": "objdump",
            "CMAKE_NM": "nm",
        })

        # Build environment variables
        self.buildenv_info.define("GCC_INSTALL_DIR", self.package_folder)
        self.buildenv_info.define("CC", "gcc")
        self.buildenv_info.define("CXX", "g++")
        self.buildenv_info.define("AS", "gcc")
        self.buildenv_info.define("AR", "ar")
        self.buildenv_info.define("LD", "ld")
        self.buildenv_info.define("NM", "nm")
        self.buildenv_info.define("OBJCOPY", "objcopy")
        self.buildenv_info.define("OBJDUMP", "objdump")
        self.buildenv_info.define("RANLIB", "ranlib")
        self.buildenv_info.define("SIZE", "size")
        self.buildenv_info.define("STRIP", "strip")
        self.buildenv_info.define("GDB", "gdb")

        self._setup_bin_dirs()
        self._inject_native_flags()

    def _configure_arm_gcc(self):
        """Configure ARM GCC cross-compiler for Cortex-M targets"""
        self.cpp_info.includedirs = []

        # CMake cross-compilation settings
        self.conf_info.define(
            "tools.cmake.cmaketoolchain:system_name", "Generic")
        self.conf_info.define(
            "tools.cmake.cmaketoolchain:system_processor", "ARM")
        self.conf_info.define("tools.build.cross_building:can_run", False)

        self.conf_info.define("tools.build:compiler_executables", {
            "c": "arm-none-eabi-gcc",
            "cpp": "arm-none-eabi-g++",
            "asm": "arm-none-eabi-gcc",
        })

        # CMake extra variables with cross-compilation workarounds
        self.conf_info.define("tools.cmake.cmaketoolchain:extra_variables", {
            # Blank out CMake's default optimization flags
            "CMAKE_CXX_FLAGS_DEBUG": "",
            "CMAKE_CXX_FLAGS_RELEASE": "",
            "CMAKE_CXX_FLAGS_MINSIZEREL": "",
            "CMAKE_CXX_FLAGS_RELWITHDEBINFO": "",
            "CMAKE_C_FLAGS_DEBUG": "",
            "CMAKE_C_FLAGS_RELEASE": "",
            "CMAKE_C_FLAGS_MINSIZEREL": "",
            "CMAKE_C_FLAGS_RELWITHDEBINFO": "",

            # Cross-compilation workarounds
            "CMAKE_CXX_COMPILER_WORKS": "TRUE",
            "CMAKE_C_COMPILER_WORKS": "TRUE",
            "CMAKE_TRY_COMPILE_TARGET_TYPE": "STATIC_LIBRARY",

            # Binutils
            "CMAKE_AR": "arm-none-eabi-ar",
            "CMAKE_RANLIB": "arm-none-eabi-ranlib",
            "CMAKE_STRIP": "arm-none-eabi-strip",
            "CMAKE_OBJCOPY": "arm-none-eabi-objcopy",
            "CMAKE_OBJDUMP": "arm-none-eabi-objdump",
            "CMAKE_NM": "arm-none-eabi-nm",
            "CMAKE_SIZE_UTIL": "arm-none-eabi-size",
        })

        # Build environment variables
        self.buildenv_info.define("GCC_INSTALL_DIR", self.package_folder)
        self.buildenv_info.define("CC", "arm-none-eabi-gcc")
        self.buildenv_info.define("CXX", "arm-none-eabi-g++")
        self.buildenv_info.define("AS", "arm-none-eabi-gcc")
        self.buildenv_info.define("AR", "arm-none-eabi-ar")
        self.buildenv_info.define("LD", "arm-none-eabi-ld")
        self.buildenv_info.define("NM", "arm-none-eabi-nm")
        self.buildenv_info.define("OBJCOPY", "arm-none-eabi-objcopy")
        self.buildenv_info.define("OBJDUMP", "arm-none-eabi-objdump")
        self.buildenv_info.define("RANLIB", "arm-none-eabi-ranlib")
        self.buildenv_info.define("SIZE", "arm-none-eabi-size")
        self.buildenv_info.define("STRIP", "arm-none-eabi-strip")
        self.buildenv_info.define("GDB", "arm-none-eabi-gdb")

        self._setup_bin_dirs()
        self._inject_arm_flags()

    def _inject_native_flags(self):
        """Inject GCC-specific flags for native compilation"""
        c_flags = []
        cxx_flags = []
        exelinkflags = []

        if self.options.lto:
            c_flags.append("-flto")
            cxx_flags.append("-flto")
            exelinkflags.append("-flto")

            LVL = int(self.options.lto_compression_level)
            c_flags.append(f"-flto-compression-level={LVL}")
            cxx_flags.append(f"-flto-compression-level={LVL}")

            if self.options.fat_lto:
                c_flags.append("-ffat-lto-objects")
                cxx_flags.append("-ffat-lto-objects")

        if self.options.function_sections:
            c_flags.append("-ffunction-sections")
            cxx_flags.append("-ffunction-sections")

        if self.options.data_sections:
            c_flags.append("-fdata-sections")
            cxx_flags.append("-fdata-sections")

        if self.options.gc_sections:
            # Determine target OS for GC flags
            if self.settings_target:
                target_os = self.settings_target.get_safe('os')
            else:
                target_os = str(self.settings.os)

            if target_os == "Macos":
                exelinkflags.append("-Wl,-dead_strip")
            elif target_os != "Windows":
                exelinkflags.append("-Wl,--gc-sections")
            # Windows: GCC applies gc-sections automatically

        self.output.info(f'native c_flags: {c_flags}')
        self.output.info(f'native cxx_flags: {cxx_flags}')
        self.output.info(f'native exelinkflags: {exelinkflags}')

        self.conf_info.append("tools.build:cflags", c_flags)
        self.conf_info.append("tools.build:cxxflags", cxx_flags)
        self.conf_info.append("tools.build:exelinkflags", exelinkflags)

    def _inject_arm_flags(self):
        """Inject GCC-specific flags for ARM Cortex-M targets"""
        c_flags = []
        cxx_flags = []
        exelinkflags = []

        # Set optimization level based on build type
        if self.settings_target:
            BUILD_TYPE = str(self.settings_target.build_type)
            if BUILD_TYPE == "Debug":
                # Use -Og for debuggable but LTO-compatible code
                c_flags.append("-Og")
                cxx_flags.append("-Og")
            elif BUILD_TYPE == "MinSizeRel":
                c_flags.append("-Os")
                cxx_flags.append("-Os")
            elif BUILD_TYPE in ["Release", "RelWithDebInfo"]:
                c_flags.append("-O3")
                cxx_flags.append("-O3")

        if self.options.lto:
            c_flags.append("-flto")
            cxx_flags.append("-flto")
            exelinkflags.append("-flto")

            LVL = int(self.options.lto_compression_level)
            c_flags.append(f"-flto-compression-level={LVL}")
            cxx_flags.append(f"-flto-compression-level={LVL}")

            if self.options.fat_lto:
                c_flags.append("-ffat-lto-objects")
                cxx_flags.append("-ffat-lto-objects")

        if self.options.function_sections:
            c_flags.append("-ffunction-sections")
            cxx_flags.append("-ffunction-sections")

        if self.options.data_sections:
            c_flags.append("-fdata-sections")
            cxx_flags.append("-fdata-sections")

        if self.options.gc_sections:
            exelinkflags.append("-Wl,--gc-sections")

        if self.options.default_libc:
            exelinkflags.append("--specs=nosys.specs")

        # Architecture-specific flags for ARM Cortex-M (GCC style)
        ARCH_MAP = {
            "cortex-m0": ["-mcpu=cortex-m0", "-mfloat-abi=soft"],
            "cortex-m0plus": ["-mcpu=cortex-m0plus", "-mfloat-abi=soft"],
            "cortex-m1": ["-mcpu=cortex-m1", "-mfloat-abi=soft"],
            "cortex-m3": ["-mcpu=cortex-m3", "-mfloat-abi=soft"],
            "cortex-m4": ["-mcpu=cortex-m4", "-mfloat-abi=soft"],
            "cortex-m4f": ["-mcpu=cortex-m4", "-mfloat-abi=hard"],
            "cortex-m7": ["-mcpu=cortex-m7", "-mfloat-abi=soft"],
            "cortex-m7f": [
                "-mcpu=cortex-m7", "-mfloat-abi=hard", "-mfpu=fpv5-sp-d16"],
            "cortex-m7d": [
                "-mcpu=cortex-m7", "-mfloat-abi=hard", "-mfpu=fpv5-d16"],
            "cortex-m23": ["-mcpu=cortex-m23", "-mfloat-abi=soft"],
            "cortex-m33": ["-mcpu=cortex-m33", "-mfloat-abi=soft"],
            "cortex-m33f": ["-mcpu=cortex-m33", "-mfloat-abi=hard"],
            "cortex-m35p": ["-mcpu=cortex-m35p", "-mfloat-abi=soft"],
            "cortex-m35pf": ["-mcpu=cortex-m35p", "-mfloat-abi=hard"],
            "cortex-m55": ["-mcpu=cortex-m55", "-mfloat-abi=soft"],
            "cortex-m85": ["-mcpu=cortex-m85", "-mfloat-abi=soft"],
        }

        if (self.options.default_arch and self.settings_target and
                self.settings_target.get_safe('arch') in ARCH_MAP):
            ARCH_FLAGS = ARCH_MAP[self.settings_target.get_safe('arch')]
            c_flags.extend(ARCH_FLAGS)
            cxx_flags.extend(ARCH_FLAGS)
            exelinkflags.extend(ARCH_FLAGS)

        self.output.info(f'arm c_flags: {c_flags}')
        self.output.info(f'arm cxx_flags: {cxx_flags}')
        self.output.info(f'arm exelinkflags: {exelinkflags}')

        self.conf_info.append("tools.build:cflags", c_flags)
        self.conf_info.append("tools.build:cxxflags", cxx_flags)
        self.conf_info.append("tools.build:exelinkflags", exelinkflags)

    def package_id(self):
        # Clear options - they only affect flags, not the package binary
        self.info.options.clear()

        # Clear settings - the downloaded binary is determined by build machine
        self.info.settings.clear()

        # Keep the variant in package_id since native and arm-none-eabi
        # are completely different toolchains
        variant = self._determine_gcc_variant()
        self.info.conf.define("user.multiarch-gnu-toolchain:variant", variant)
