# Renderer test fixtures

`engine-debug.txt` is the expected output for `DebugSwitches::helpText()`.
It was moved unchanged from the [upstream help fixture](https://github.com/portghost-dev/linux-wallpaperengine/blob/50530e5167c0822e63f052f50ef8d8613663915a/lwe-ui/tests/fixtures/help/engine-debug.txt)
when the unused UI was removed. Its contents are byte-for-byte the help string
in `Application/DebugSwitches.cpp`, retained under the renderer's GPLv3 license.
No UI Python/QML code is included here. Keep this fixture independent of the UI.
