#pragma once
#include "WallpaperEngine/Scripting/ScriptableObject.h"

namespace WallpaperEngine::Render::Objects {
// Non-drawing groups still own scriptable transforms and visibility.
class CGroup final : public Scripting::ScriptableObject {
  public:
    CGroup (Wallpapers::CScene &scene, const Object &object)
	: CObject (scene, object), ScriptableObject (scene, object) {
	registerProperty ("origin", *object.origin->value);
	registerProperty ("scale", *object.groupScale->value);
	registerProperty ("angles", *object.groupAngles->value);
	registerProperty ("visible", *object.groupVisible->value);
    }
};
} // namespace WallpaperEngine::Render::Objects
