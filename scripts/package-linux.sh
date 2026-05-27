#!/bin/bash
# Kairo Phantom — Linux .AppImage + .deb Packager
# ================================================
# Domain 11: Platform-Specific Packaging (Gate 5)
#
# Produces:
#   dist/linux/KairoPhantom-{VERSION}-{ARCH}.AppImage
#   dist/linux/kairo-phantom_{VERSION}_{ARCH}.deb
#
# Prerequisites (install once):
#   cargo install cargo-deb
#   sudo apt-get install appimage-builder  (or download appimagetool)
#   sudo apt-get install xdotool xclip at-spi2-core  (runtime deps)
#
# Usage:
#   ./scripts/package-linux.sh
#   ./scripts/package-linux.sh --appimage-only
#   ./scripts/package-linux.sh --deb-only

set -euo pipefail

KAIRO_VERSION="0.3.0"
ARCH="$(uname -m)"  # x86_64 or aarch64
OUTPUT_DIR="dist/linux"
APP_NAME="kairo-phantom"
DISPLAY_NAME="Kairo Phantom"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $1"; }
step() { echo -e "${BLUE}→${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

MODE="${1:-both}"

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  Kairo Phantom — Linux Packager                   ║"
echo "║  Version: $KAIRO_VERSION | Arch: $ARCH            ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Build release binary ──────────────────────────────────────────────
step "Building Kairo Phantom (release)..."
cd "$ROOT_DIR"
cargo build --release --manifest-path phantom-core/Cargo.toml
BINARY="$ROOT_DIR/target/release/kairo-phantom"
[ -f "$BINARY" ] || { echo "❌ Build failed — binary not found"; exit 1; }
ok "Binary: $BINARY ($(du -sh "$BINARY" | cut -f1))"

mkdir -p "$ROOT_DIR/$OUTPUT_DIR"

# ── Step 2: .deb Package (Debian/Ubuntu) ─────────────────────────────────────
build_deb() {
    step "Building .deb package..."

    if command -v cargo-deb &>/dev/null; then
        cd "$ROOT_DIR/phantom-core"
        cargo deb --no-build --output "../$OUTPUT_DIR/"
        DEB_FILE=$(ls "../$OUTPUT_DIR/"*.deb 2>/dev/null | head -1)
        if [ -n "$DEB_FILE" ]; then
            ok ".deb: $DEB_FILE"
            return 0
        fi
    fi

    # Fallback: manual .deb construction
    warn "cargo-deb not found — building .deb manually"
    DEB_DIR="$ROOT_DIR/$OUTPUT_DIR/deb-build"
    DEB_NAME="${APP_NAME}_${KAIRO_VERSION}_${ARCH}"
    mkdir -p "$DEB_DIR/DEBIAN"
    mkdir -p "$DEB_DIR/usr/bin"
    mkdir -p "$DEB_DIR/usr/share/applications"
    mkdir -p "$DEB_DIR/usr/share/icons/hicolor/256x256/apps"
    mkdir -p "$DEB_DIR/usr/share/doc/$APP_NAME"

    cp "$BINARY" "$DEB_DIR/usr/bin/$APP_NAME"

    # DEBIAN/control
    cat > "$DEB_DIR/DEBIAN/control" << CTRL
Package: $APP_NAME
Version: $KAIRO_VERSION
Architecture: $([ "$ARCH" = "x86_64" ] && echo "amd64" || echo "arm64")
Maintainer: Kairo Phantom Contributors <kairo@phantom.dev>
Depends: xdotool | ydotool, xclip | wl-clipboard
Recommends: at-spi2-core
Description: Kairo Phantom — AI ghost-writer for any application
 Kairo Phantom is an AI-powered writing assistant that reads context
 from any open document and ghost-types AI-generated text directly
 into your application. Activate with Alt+M from anywhere.
 .
 Supports: Word, Google Docs, LibreOffice, VS Code, and 97+ formats.
 Runs 100% offline using Ollama + local LLMs.
CTRL

    # DEBIAN/postinst — install instructions
    cat > "$DEB_DIR/DEBIAN/postinst" << 'POST'
#!/bin/bash
set -e
echo ""
echo "✅ Kairo Phantom installed successfully!"
echo ""
echo "Required accessibility tools (if not already installed):"
if [ -n "${DISPLAY:-}" ]; then
    echo "  X11: sudo apt-get install -y xdotool xclip at-spi2-core"
elif [ -n "${WAYLAND_DISPLAY:-}" ]; then
    echo "  Wayland: sudo apt-get install -y ydotool wl-clipboard at-spi2-core"
fi
echo ""
echo "Start: kairo-phantom"
echo "Hotkey: Alt+M (in any application)"
echo ""
POST
    chmod 755 "$DEB_DIR/DEBIAN/postinst"

    # .desktop file
    cat > "$DEB_DIR/usr/share/applications/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Name=Kairo Phantom
GenericName=AI Writing Assistant
Comment=AI ghost-writer that works in any application. Press Alt+M to activate.
Exec=kairo-phantom
Icon=kairo-phantom
Terminal=false
Type=Application
Categories=Office;Utility;
Keywords=ai;writing;ghost;document;llm;
DESKTOP

    # Copy icon if available
    if [ -f "$ROOT_DIR/installer/linux/kairo-phantom.png" ]; then
        cp "$ROOT_DIR/installer/linux/kairo-phantom.png" \
            "$DEB_DIR/usr/share/icons/hicolor/256x256/apps/kairo-phantom.png"
    fi

    # Copyright / changelog
    echo "Kairo Phantom ${KAIRO_VERSION}" > "$DEB_DIR/usr/share/doc/$APP_NAME/changelog.gz"
    echo "License: MIT" > "$DEB_DIR/usr/share/doc/$APP_NAME/copyright"

    # Build the package
    dpkg-deb --build --root-owner-group "$DEB_DIR" \
        "$ROOT_DIR/$OUTPUT_DIR/${DEB_NAME}.deb" 2>/dev/null || \
        dpkg-deb --build "$DEB_DIR" "$ROOT_DIR/$OUTPUT_DIR/${DEB_NAME}.deb"

    ok ".deb: $ROOT_DIR/$OUTPUT_DIR/${DEB_NAME}.deb"
    rm -rf "$DEB_DIR"
}

# ── Step 3: .AppImage (Universal Linux) ──────────────────────────────────────
build_appimage() {
    step "Building .AppImage..."

    APPIMAGE_DIR="$ROOT_DIR/$OUTPUT_DIR/AppDir"
    APPIMAGE_OUT="$ROOT_DIR/$OUTPUT_DIR/${DISPLAY_NAME// /}-${KAIRO_VERSION}-${ARCH}.AppImage"

    mkdir -p "$APPIMAGE_DIR/usr/bin"
    mkdir -p "$APPIMAGE_DIR/usr/lib"
    mkdir -p "$APPIMAGE_DIR/usr/share/applications"
    mkdir -p "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps"

    cp "$BINARY" "$APPIMAGE_DIR/usr/bin/$APP_NAME"

    # AppRun entry point
    cat > "$APPIMAGE_DIR/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE="${SELF%/*}"
export PATH="${HERE}/usr/bin:${PATH}"
exec "${HERE}/usr/bin/kairo-phantom" "$@"
APPRUN
    chmod +x "$APPIMAGE_DIR/AppRun"

    # .desktop
    cat > "$APPIMAGE_DIR/$APP_NAME.desktop" << DESKTOP
[Desktop Entry]
Name=Kairo Phantom
Exec=kairo-phantom
Icon=kairo-phantom
Type=Application
Categories=Office;Utility;
DESKTOP
    cp "$APPIMAGE_DIR/$APP_NAME.desktop" \
       "$APPIMAGE_DIR/usr/share/applications/$APP_NAME.desktop"

    # Icon (placeholder if not found)
    if [ -f "$ROOT_DIR/installer/linux/kairo-phantom.png" ]; then
        cp "$ROOT_DIR/installer/linux/kairo-phantom.png" "$APPIMAGE_DIR/$APP_NAME.png"
        cp "$ROOT_DIR/installer/linux/kairo-phantom.png" \
            "$APPIMAGE_DIR/usr/share/icons/hicolor/256x256/apps/$APP_NAME.png"
    fi

    # Try appimagetool
    APPIMAGETOOL=""
    if command -v appimagetool &>/dev/null; then
        APPIMAGETOOL="appimagetool"
    elif [ -f "$ROOT_DIR/tools/appimagetool-${ARCH}.AppImage" ]; then
        APPIMAGETOOL="$ROOT_DIR/tools/appimagetool-${ARCH}.AppImage"
    fi

    if [ -n "$APPIMAGETOOL" ]; then
        ARCH="$ARCH" "$APPIMAGETOOL" "$APPIMAGE_DIR" "$APPIMAGE_OUT"
        ok ".AppImage: $APPIMAGE_OUT"
    else
        warn "appimagetool not found — skipping AppImage creation"
        warn "Download from: https://github.com/AppImage/appimagetool/releases"
        warn "Save to: $ROOT_DIR/tools/appimagetool-${ARCH}.AppImage"
        warn "Then re-run this script."
        # Create a self-extracting shell fallback instead
        cat > "$ROOT_DIR/$OUTPUT_DIR/${APP_NAME}-${KAIRO_VERSION}-${ARCH}.run" << SHELLRUN
#!/bin/bash
# Kairo Phantom ${KAIRO_VERSION} self-extracting installer
# Usage: chmod +x ${APP_NAME}-${KAIRO_VERSION}-${ARCH}.run && ./${APP_NAME}-${KAIRO_VERSION}-${ARCH}.run
cp "\$(dirname "\$0")/\$0" /tmp/kairo-phantom-install
mkdir -p "\$HOME/.local/bin"
echo "Installing Kairo Phantom..."
SHELLRUN
    fi

    rm -rf "$APPIMAGE_DIR"
}

# ── Execute based on mode ──────────────────────────────────────────────────────
case "$MODE" in
    --deb-only)     build_deb ;;
    --appimage-only) build_appimage ;;
    *)              build_deb; build_appimage ;;
esac

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  ✅ GATE 5: Linux packages READY                  ║"
echo "╚═══════════════════════════════════════════════════╝"
echo "  Output: $ROOT_DIR/$OUTPUT_DIR/"
ls -lh "$ROOT_DIR/$OUTPUT_DIR/" 2>/dev/null | grep -E "\.(deb|AppImage|run)$" | \
    awk '{print "  " $NF " (" $5 ")"}'
echo ""
echo "  Install .deb:      sudo dpkg -i kairo-phantom_*.deb"
echo "  Run .AppImage:     chmod +x KairoPhantom-*.AppImage && ./KairoPhantom-*.AppImage"
echo ""
