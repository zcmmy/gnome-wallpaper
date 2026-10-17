#include "GLFWMouseInput.h"
#include <glm/common.hpp>
#include "WallpaperEngine/Input/PointerCoordinates.h"

#include "WallpaperEngine/Render/Drivers/GLFWOpenGLDriver.h"

using namespace WallpaperEngine::Input::Drivers;

GLFWMouseInput::GLFWMouseInput (const Render::Drivers::GLFWOpenGLDriver& driver) : m_driver (driver) { }

bool GLFWMouseInput::setExternalPointer(double x, double y, bool left, bool right, bool active) {
    m_external = true;
    m_externalPosition = {x, y};
    m_externalLeft = left;
    m_externalRight = right;
    m_externalActive = active;
    m_externalAt = std::chrono::steady_clock::now();
    return true;
}

void GLFWMouseInput::update () {
    const glm::ivec2 fb = m_driver.getFramebufferSize();
    m_leftClick = m_rightClick = MouseClickStatus::Released;
    m_hasPointer = false;
    m_reportedPosition = framebufferPointer({0.5, 0.5}, fb);
    if (!m_driver.getApp().getContext().settings.mouse.enabled || fb.x <= 0 || fb.y <= 0)
        return;

    if (m_external) {
        // A disconnected/suspended compositor cannot leave a button held down.
        if (!m_externalActive || std::chrono::steady_clock::now() - m_externalAt > std::chrono::milliseconds(500))
            return;
        m_hasPointer = true;
        m_reportedPosition = framebufferPointer(m_externalPosition, fb);
        m_leftClick = m_externalLeft ? MouseClickStatus::Clicked : MouseClickStatus::Released;
        m_rightClick = m_externalRight ? MouseClickStatus::Clicked : MouseClickStatus::Released;
        return;
    }

    int width = 0, height = 0;
    glfwGetWindowSize(m_driver.getWindow(), &width, &height);
    glfwGetCursorPos(m_driver.getWindow(), &m_mousePosition.x, &m_mousePosition.y);
    const auto norm = logicalPointer(m_mousePosition.x, m_mousePosition.y, width, height);
    if (!norm || !glfwGetWindowAttrib(m_driver.getWindow(), GLFW_HOVERED))
        return;
    // GLFW cursor positions are logical; the renderer consumes framebuffer pixels.
    m_reportedPosition = framebufferPointer(*norm, fb);
    m_hasPointer = true;
    m_leftClick = glfwGetMouseButton(m_driver.getWindow(), GLFW_MOUSE_BUTTON_LEFT) == GLFW_PRESS
        ? MouseClickStatus::Clicked : MouseClickStatus::Released;
    m_rightClick = glfwGetMouseButton(m_driver.getWindow(), GLFW_MOUSE_BUTTON_RIGHT) == GLFW_PRESS
        ? MouseClickStatus::Clicked : MouseClickStatus::Released;
}

glm::dvec2 GLFWMouseInput::position () const { return this->m_reportedPosition; }

glm::dvec2 GLFWMouseInput::normalized () const { return this->resolveNormalized ().value_or (glm::dvec2 { 0.5, 0.5 }); }

bool GLFWMouseInput::hasPointer () const { return this->resolveNormalized ().has_value (); }

std::optional<glm::dvec2> GLFWMouseInput::resolveNormalized () const {
    // [0,1]^2 within the window, y-down; nullopt when disabled/degenerate.
    // m_reportedPosition is GL y-up (update() flips), so undo it here.
    if (!m_hasPointer || !this->m_driver.getApp ().getContext ().settings.mouse.enabled) {
	return std::nullopt;
    }
    const glm::ivec2 fb = this->m_driver.getFramebufferSize ();
    if (fb.x <= 0 || fb.y <= 0) {
	return std::nullopt;
    }
    return glm::dvec2 { glm::clamp (this->m_reportedPosition.x / fb.x, 0.0, 1.0),
			glm::clamp (1.0 - this->m_reportedPosition.y / fb.y, 0.0, 1.0) };
}

WallpaperEngine::Input::MouseClickStatus GLFWMouseInput::leftClick () const { return m_leftClick; }

WallpaperEngine::Input::MouseClickStatus GLFWMouseInput::rightClick () const { return m_rightClick; }