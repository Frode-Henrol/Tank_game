#pragma once

#include <string>
#include <unordered_map>

struct SDL_Renderer;
struct SDL_Texture;
using TTF_Font = struct TTF_Font;

namespace tank::ui {

// Thin wrapper around one SDL3_ttf font: renders (and caches, by exact string) white text as a
// texture. Tint via SDL_SetTextureColorMod on the returned texture if a color other than white
// is needed - buttons in this game are only ever drawn with white text, so that's not exposed
// here.
class Font {
public:
    Font(const std::string& path, float point_size);
    ~Font();

    Font(const Font&) = delete;
    Font& operator=(const Font&) = delete;

    // Returns nullptr (logging via SDL_Log) if the font failed to load or the text failed to
    // render - callers should treat that as "draw nothing," not a fatal error.
    [[nodiscard]] SDL_Texture* GetTextTexture(SDL_Renderer* renderer, const std::string& text);

private:
    TTF_Font* font_ = nullptr;
    std::unordered_map<std::string, SDL_Texture*> cache_;
};

}  // namespace tank::ui
