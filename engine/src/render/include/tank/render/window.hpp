#pragma once

#include <string>

struct SDL_Window;
struct SDL_Renderer;

namespace tank::render {

// RAII wrapper around SDL's window + renderer pair. Owns SDL_Init(SDL_INIT_VIDEO)/SDL_Quit for
// the lifetime of the process (only one Window is expected to exist at a time).
class Window {
public:
    Window(const std::string& title, int width, int height);
    ~Window();

    Window(const Window&) = delete;
    Window& operator=(const Window&) = delete;

    void Clear(float r, float g, float b, float a = 1.0f) const;
    void Present() const;

    [[nodiscard]] SDL_Renderer* Renderer() const { return renderer_; }
    [[nodiscard]] SDL_Window* Handle() const { return window_; }
    [[nodiscard]] int Width() const { return width_; }
    [[nodiscard]] int Height() const { return height_; }

private:
    SDL_Window* window_ = nullptr;
    SDL_Renderer* renderer_ = nullptr;
    int width_ = 0;
    int height_ = 0;
};

}  // namespace tank::render
