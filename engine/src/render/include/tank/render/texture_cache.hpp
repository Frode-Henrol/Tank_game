#pragma once

#include <string>
#include <unordered_map>

struct SDL_Texture;
struct SDL_Renderer;

namespace tank::render {

// Loads PNGs (via SDL3_image) keyed by filesystem path, caching so repeated Sprite references
// to the same file (many tanks sharing one body texture, etc.) don't reload/re-upload it.
class TextureCache {
public:
    explicit TextureCache(SDL_Renderer* renderer) : renderer_(renderer) {}
    ~TextureCache();

    TextureCache(const TextureCache&) = delete;
    TextureCache& operator=(const TextureCache&) = delete;

    // Returns the cached texture for `path`, loading it on first request. Returns nullptr (and
    // logs via SDL_Log) if the file can't be loaded.
    SDL_Texture* Get(const std::string& path);

private:
    SDL_Renderer* renderer_;
    std::unordered_map<std::string, SDL_Texture*> textures_;
};

}  // namespace tank::render
