#!/bin/bash
# Kairo Phantom — macOS .dmg Packager
# =====================================
# Domain 11: Platform-Specific Packaging (Gate 5)
#
# Produces: KairoPhantom-{VERSION}-macOS-{ARCH}.dmg
#
# Prerequisites (install once):
#   brew install create-dmg
#   cargo install cargo-bundle
#
# Usage:
#   ./scripts/package-macos.sh
#   ./scripts/package-macos.sh --sign  # Code-sign with Apple Developer ID

set -euo pipefail

KAIRO_VERSION="0.3.0"
ARCH="$(uname -m)"  # arm64 or x86_64
OUTPUT_DIR="dist/macos"
APP_NAME="KairoPhantom"
BUNDLE_ID="com.kairo-phantom.app"

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}✓${RESET} $1"; }
step() { echo -e "${BLUE}→${RESET} $1"; }
warn() { echo -e "${YELLOW}⚠${RESET}  $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  Kairo Phantom — macOS .dmg Builder               ║"
echo "║  Version: $KAIRO_VERSION | Arch: $ARCH            ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Build the release binary ──────────────────────────────────────────
step "Building Kairo Phantom (release)..."
cd "$ROOT_DIR"
cargo build --release --manifest-path phantom-core/Cargo.toml
BINARY="$ROOT_DIR/target/release/kairo-phantom"
[ -f "$BINARY" ] || { echo "❌ Build failed — binary not found at $BINARY"; exit 1; }
ok "Binary: $BINARY"

# ── Step 2: Create .app bundle structure ──────────────────────────────────────
step "Creating .app bundle..."
APP_DIR="$ROOT_DIR/$OUTPUT_DIR/$APP_NAME.app"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copy binary
cp "$BINARY" "$APP_DIR/Contents/MacOS/$APP_NAME"
chmod +x "$APP_DIR/Contents/MacOS/$APP_NAME"

# Write Info.plist (required for NSAccessibilityUsageDescription)
cat > "$APP_DIR/Contents/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>KairoPhantom</string>
    <key>CFBundleDisplayName</key>
    <string>Kairo Phantom</string>
    <key>CFBundleIdentifier</key>
    <string>${BUNDLE_ID}</string>
    <key>CFBundleVersion</key>
    <string>${KAIRO_VERSION}</string>
    <key>CFBundleShortVersionString</key>
    <string>${KAIRO_VERSION}</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>12.0</string>
    <key>NSAccessibilityUsageDescription</key>
    <string>Kairo Phantom needs Accessibility access to read document text and type AI-generated content into your applications. Press Alt+M in any app to activate.</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
PLIST
ok "Info.plist written (NSAccessibilityUsageDescription included)"

# Copy icon if available
if [ -f "$ROOT_DIR/installer/macos/AppIcon.icns" ]; then
    cp "$ROOT_DIR/installer/macos/AppIcon.icns" "$APP_DIR/Contents/Resources/AppIcon.icns"
    ok "App icon copied"
else
    warn "No AppIcon.icns found at installer/macos/AppIcon.icns — bundle will use default icon"
fi

# ── Step 3: Code-sign (optional) ──────────────────────────────────────────────
if [[ "${1:-}" == "--sign" ]]; then
    SIGN_ID="${APPLE_DEVELOPER_ID:-}"
    if [ -z "$SIGN_ID" ]; then
        warn "APPLE_DEVELOPER_ID not set — skipping code signing"
    else
        step "Code-signing with: $SIGN_ID"
        codesign --deep --force --verify --verbose \
            --sign "$SIGN_ID" \
            --options runtime \
            --entitlements "$ROOT_DIR/installer/macos/entitlements.plist" \
            "$APP_DIR"
        ok "App signed"
    fi
fi

# ── Step 4: Create .dmg ────────────────────────────────────────────────────────
step "Creating .dmg..."
mkdir -p "$ROOT_DIR/$OUTPUT_DIR"
DMG_PATH="$ROOT_DIR/$OUTPUT_DIR/${APP_NAME}-${KAIRO_VERSION}-macOS-${ARCH}.dmg"

if command -v create-dmg &>/dev/null; then
    create-dmg \
        --volname "Kairo Phantom ${KAIRO_VERSION}" \
        --volicon "$ROOT_DIR/installer/macos/AppIcon.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "${APP_NAME}.app" 175 190 \
        --hide-extension "${APP_NAME}.app" \
        --app-drop-link 425 190 \
        --no-internet-enable \
        "$DMG_PATH" \
        "$APP_DIR" 2>/dev/null || {
        # Fallback: create a simple DMG without create-dmg
        hdiutil create -volname "Kairo Phantom" -srcfolder "$APP_DIR" \
            -ov -format UDZO "$DMG_PATH"
    }
else
    warn "create-dmg not found — using hdiutil directly (install create-dmg for prettier DMG)"
    hdiutil create -volname "Kairo Phantom" -srcfolder "$APP_DIR" \
        -ov -format UDZO "$DMG_PATH"
fi

ok "DMG created: $DMG_PATH"
DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
ok "DMG size: $DMG_SIZE"

echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  ✅ GATE 5: macOS .dmg READY                      ║"
echo "╚═══════════════════════════════════════════════════╝"
echo "  Path: $DMG_PATH"
echo "  Arch: $ARCH"
echo "  Install: Double-click → drag to Applications"
echo ""
