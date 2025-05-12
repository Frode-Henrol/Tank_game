import pygame as pg

class Button:
    def __init__(self, 
                 x, y, width, height, text, 
                 target_state=None, 
                 action=None, 
                 is_toggle_on=False,
                 color_normal=None, 
                 color_clicked=None, 
                 hover_enabled=True, 
                 disabled=False, 
                 semi_disabled=False, 
                 click_color_enabled=False, 
                 obj_id=None):
        
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.target_state = target_state
        self.action = action
        self.font = pg.font.Font(None, 36)
        self.obj_id = obj_id
        
        # Colors
        self.default_color_normal = (100, 100, 200)
        self.default_color_clicked = (50, 50, 150)
        self.disabled_color = (150, 150, 150)
        self.semi_disabled_color = (120, 120, 180)
        
        self.color_normal = color_normal or self.default_color_normal
        self.color_clicked = color_clicked or self.default_color_clicked

        # Flags
        self.hover_enabled = hover_enabled
        self.is_toggle_on = is_toggle_on
        self.toggle = is_toggle_on
        self.disabled = disabled
        self.semi_disabled = semi_disabled
        self.click_color_enabled = click_color_enabled

        # Button state: "normal", "hover", "clicked"
        self.state = "normal"
        self.color = self.get_color_from_state()

    def get_color_from_state(self):
        if self.disabled:
            return self.disabled_color
        elif self.semi_disabled:
            return self.semi_disabled_color
        elif self.state == "hover":
            base = self.color_clicked if self.toggle else self.color_normal
            r, g, b = base
            return (min(r + 50, 255), min(g + 50, 255), min(b + 50, 255))
        elif self.state == "clicked":
            return self.color_clicked
        elif self.toggle:
            return self.color_clicked
        else:
            return self.color_normal

    def set_disabled(self, disabled):
        self.disabled = disabled
        self.color = self.get_color_from_state()

    def set_semi_disabled(self, semi_disabled):
        self.semi_disabled = semi_disabled
        self.color = self.get_color_from_state()

    def change_button_text(self, new_text):
        self.text = new_text

    def handle_event(self, event):
        if self.disabled:
            return None

        if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            print(f"CLICKED on {self.text} at {event.pos}")

            if self.semi_disabled:
                self.set_semi_disabled(False)

            if self.is_toggle_on:
                self.toggle = not self.toggle

            if self.click_color_enabled:
                self.state = "clicked"
            elif self.hover_enabled and self.rect.collidepoint(event.pos):
                self.state = "hover"
            else:
                self.state = "normal"

            self.color = self.get_color_from_state()

            if self.action:
                self.action()

            return self.target_state

        elif event.type == pg.MOUSEMOTION:
            if self.hover_enabled and self.rect.collidepoint(event.pos) and not self.semi_disabled:
                self.state = "hover"
            else:
                self.state = "normal"

            self.color = self.get_color_from_state()

        return None

    def draw(self, surface):
        pg.draw.rect(surface, self.color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(
            text_surface,
            (
                self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                self.rect.y + (self.rect.height - text_surface.get_height()) // 2
            )
        )

    def get_id(self):
        return self.obj_id
