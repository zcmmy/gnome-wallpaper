#pragma once

#include "ObjectAdapter.h"
#include <map>

namespace WallpaperEngine::Scripting::Adapters {
class ScriptableObjectAdapter : public ObjectAdapter {
public:
    explicit ScriptableObjectAdapter (ScriptEngine& engine, std::string name);

    ~ScriptableObjectAdapter () override;
    void forget (const ScriptableObject *object);
    JSValue instantiate (ScriptableObject& object) override;
    JSValue instantiate (Data::Model::DynamicValue& value) override;

private:
  std::map<const ScriptableObject *, JSValue> m_instances;
  JSClassExoticMethods m_exoticMethods;
  std::string m_name;
};
}