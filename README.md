# WZWRoot

A kernel-based root solution for Android devices, forked from [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra).

## Features

1. Kernel-based `su` and root access management
2. Module system based on Magic Mount
3. App Profile: Lock up the root power in a cage
4. Support non-GKI and GKI 1.0
5. KPM Support
6. Built-in susfs management tool

## Compatibility

- Android GKI 2.0 devices (kernel 5.10+) officially supported
- Older kernels (4.4+) compatible with manual build
- Support for 3.x kernel (3.4-3.18) with backports
- Architectures: arm64-v8a, armeabi-v7a, X86_64 (partial)

## Building

### Prerequisites

- Android Studio or command-line build tools
- Android NDK
- Rust toolchain (for userspace tools)
- Linux kernel source (for kernel module)

### Build Manager App

```bash
cd manager
./gradlew assembleRelease
```

### Build Kernel Module

Integrate into your kernel source and build with your kernel.

## Credits

- [KernelSU](https://github.com/tiann/KernelSU): Original upstream
- [SukiSU-Ultra](https://github.com/SukiSU-Ultra/SukiSU-Ultra): Direct upstream
- [MKSU](https://github.com/5ec1cff/KernelSU): Magic Mount
- [susfs](https://gitlab.com/simonpunk/susfs4ksu): Root hiding patches

## License

- kernel directory: GPL-2.0-only
- Other parts: GPL-3.0 or later
