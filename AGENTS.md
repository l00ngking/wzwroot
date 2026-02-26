# AGENTS.md

## Cursor Cloud specific instructions

### Overview

WZWRoot is a kernel-based Android root solution. The codebase has four main buildable components:

| Component | Language | Location | Build Tool |
|---|---|---|---|
| **ksud** | Rust | `userspace/ksud/` | `cross` (Docker-based cross-compilation) |
| **ksuinit** | Rust | `userspace/ksuinit/` | `cargo` (musl target) |
| **Manager App** | Kotlin/Compose | `manager/` | Gradle (`./gradlew`) |
| **Kernel Module** | C | `kernel/` | Linux kernel build system |

### Environment variables

The following must be set (already configured in `~/.bashrc`):

```
export ANDROID_HOME=/home/ubuntu/android-sdk
export ANDROID_NDK_HOME=/home/ubuntu/android-sdk/ndk/29.0.14206865
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

### Starting Docker (required for `cross`)

Docker must be running before using `cross` to build ksud:

```bash
sudo dockerd &>/tmp/dockerd.log &
sleep 3
```

### Building ksud

```bash
CROSS_NO_WARNINGS=0 cross build --target aarch64-linux-android --release --manifest-path ./userspace/ksud/Cargo.toml
```

Other targets: `x86_64-linux-android`, `armv7-linux-androideabi`.

### Building Manager App

The Manager app requires ksud binaries as `libksud.so` in `manager/app/src/main/jniLibs/<abi>/`. Copy them before building:

```bash
mkdir -p manager/app/src/main/jniLibs/{arm64-v8a,x86_64,armeabi-v7a}
cp userspace/ksud/target/aarch64-linux-android/release/ksud manager/app/src/main/jniLibs/arm64-v8a/libksud.so
cp userspace/ksud/target/x86_64-linux-android/release/ksud manager/app/src/main/jniLibs/x86_64/libksud.so
cp userspace/ksud/target/armv7-linux-androideabi/release/ksud manager/app/src/main/jniLibs/armeabi-v7a/libksud.so
cd manager && ./gradlew assembleDebug
```

### Lint commands

- **Rust format**: `cargo fmt --manifest-path ./userspace/ksud/Cargo.toml -- --check`
- **Clippy**: `cross clippy --manifest-path userspace/ksud/Cargo.toml --target aarch64-linux-android --release`
- **Kernel C format**: `cd kernel && make check-format`
- **Shell scripts**: `shellcheck kernel/setup.sh`
- **Android lint**: `cd manager && ./gradlew lintDebug` (has pre-existing errors unrelated to code changes)

### Known issues

- The `./gradlew lintDebug` task fails with pre-existing `LocalContextGetResourceValueCall` errors in the existing Compose code. The build (`assembleDebug`) itself succeeds.
- The `make check-format` for kernel has pre-existing formatting violations in `kpm/super_access.h`.
- The kernel module cannot be built without a Linux kernel source tree; only formatting checks are available in this environment.
- This is an Android-only project; end-to-end testing requires an Android device or emulator with a custom kernel. The cloud VM can only build, lint, and run static checks.
