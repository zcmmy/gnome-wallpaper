# Scene Effects Rendering Investigation

Investigation of rendering differences between linux-wallpaperengine and the native
Windows Wallpaper Engine for scenes using combined image, text, and audio-reactive effects.

## Relevant scene techniques

This investigation applies to scenes combining solid/image layers, audio pulse effects,
text rendering, passthrough images, water-wave effects, and post-processing bloom.

## Issues Found

### 1. Script-based UserSettings

**Files:** `src/WallpaperEngine/Data/Parsers/DynamicValueParser.cpp::scriptSource`

Some wallpapers define user settings with embedded JavaScript that dynamically
control object position (Y and Z axes) via slider properties. The parser stores the
script body on the value (DynamicValue.cpp::setScriptSource) and the script engine
compiles and registers it per property (ScriptEngine.cpp::queueScript), so the
sliders drive object position as authored.

Illustrative property-update pattern:
```javascript
export function update(value) {
    value.y = scriptProperties.posY;  // slider 0-100
    return value;
}
```

### 2. Text objects

**Files:** `src/WallpaperEngine/Render/Wallpapers/CScene.cpp::CText`

Text objects are rendered by `CText`, which rasterizes
glyphs through FreeType. The font bundled with the wallpaper is loaded first from
the asset container, with a system font as fallback
(CText.cpp::loadEmbeddedFont).

### 3. Orthogonal camera auto-size

**Files:** `CScene.cpp::isAuto`

When the scene camera uses `isAuto=true`, the projection is derived from content
extent: the constructor walks the scene's image objects and takes the maximum
origin-plus-size extent (CScene.cpp::isAuto).

### 4. Passthrough images without effects are skipped (LOW-MEDIUM)

**Files:** `CImage.cpp::passthrough`

Some image layers use passthrough mode with no effects attached, and the render
path returns early for that combination (CImage.cpp::passthrough). A passthrough
layer that does carry effects renders: it keeps its destination quad full-screen in
local FBO space and passes scene-space positions through
(CImage.cpp::getPassSpacePosition).

**Impact:** If this object is meant to composite content from behind, it will not
appear.

### 5. Audio spectrum processing may differ (MEDIUM)

**Files:** `src/WallpaperEngine/Audio/Drivers/Recorders/PulseAudioPlaybackRecorder.cpp::update`

An audio pulse effect can use:
- `AUDIOPROCESSING=3`
- `audioamount=1.0`, `audiobounds=0.5-1.0`, `audioexponent=0.35`

The DSP algorithm for audio spectrum analysis may produce different results than
the Windows implementation.

**Impact:** Image pulse animations may respond differently to audio.

### 6. Fullscreen/autosize behavior incomplete (LOW)

**Files:** `src/WallpaperEngine/Render/Objects/CImage.cpp::AUTOSIZE`

There is a TODO asking what `autosize` should do. Fullscreen layers force size to
scene dimensions, but autosize behavior is undefined.

**Impact:** Minor sizing differences for affected layers.

## parallaxDepth UserSetting support

`parallaxDepth` is declared as a `UserSetting` rather than a plain `glm::vec2`,
because scenes may encode it as a UserSetting object:
```json
{"user": "parallaxstrength", "value": "0.19000 0.19000"}
```

- `src/WallpaperEngine/Data/Model/Object.h`: `parallaxDepth` is a
  `UserSettingUniquePtr` in both `ImageData` and `ParticleData`
- `src/WallpaperEngine/Data/Parsers/ObjectParser.cpp`: 3 parse sites use
  `it.user()` so both plain values and UserSetting objects are accepted
- `src/WallpaperEngine/Render/Objects/CImage.cpp`: access dereferences through the
  UserSetting wrapper (`->value->getVec2()`)

This follows the same pattern already used by `origin`, `scale`, `angles`,
`visible`, `alpha`, and `color`.

## Reproduction

```bash
linux-wallpaperengine \
  --assets-dir ~/.local/share/Steam/steamapps/common/wallpaper_engine/assets \
  --screen-root DP-2 --screen-root HDMI-A-1 \
  --fps 60 --silent \
  "/path/to/your/scene"
```
