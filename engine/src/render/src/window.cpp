#include "tank/render/window.hpp"

#include <SDL3/SDL.h>
#include <stdexcept>

namespace tank::render {

Window::Window(const std::string& title, int width, int height) : width_(width), height_(height) {
    if (!SDL_Init(SDL_INIT_VIDEO)) {
        throw std::runtime_error(std::string("SDL_Init failed: ") + SDL_GetError());
    }

    window_ = SDL_CreateWindow(title.c_str(), width, height, 0);
    if (window_ == nullptr) {
        SDL_Quit();
        throw std::runtime_error(std::string("SDL_CreateWindow failed: ") + SDL_GetError());
    }

    renderer_ = SDL_CreateRenderer(window_, nullptr);
    if (renderer_ == nullptr) {
        SDL_DestroyWindow(window_);
        SDL_Quit();
        throw std::runtime_error(std::string("SDL_CreateRenderer failed: ") + SDL_GetError());
    }
}

Window::~Window() {
    if (renderer_ != nullptr) {
        SDL_DestroyRenderer(renderer_);
    }
    if (window_ != nullptr) {
        SDL_DestroyWindow(window_);
    }
    SDL_Quit();
}

void Window::Clear(float r, float g, float b, float a) const {
    SDL_SetRenderDrawColorFloat(renderer_, r, g, b, a);
    SDL_RenderClear(renderer_);
}

void Window::Present() const { SDL_RenderPresent(renderer_); }

}  // namespace tank::render
