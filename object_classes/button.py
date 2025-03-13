import pygame as pg

class Button:
    def __init__(self, x, y, width, height, text, target_state=None, action=None, is_toggle_on=False, color_normal=None, color_clicked=None, hover_enabled=True, disabled=False, semi_disabled=False, click_color_enabled=False, obj_id = None):
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.target_state = target_state
        self.action = action
        self.font = pg.font.Font(None, 36)
        
        # id for each object
        self.obj_id = obj_id
        
        # Default colors
        self.default_color_normal = (100, 100, 200)
        self.default_color_clicked = (50, 50, 150)
        self.disabled_color = (150, 150, 150)  # Gray color when disabled
        self.semi_disabled_color = (120, 120, 180)  # Slightly faded color for semi-disabled
        
        self.color_normal = color_normal if color_normal else self.default_color_normal
        self.color_clicked = color_clicked if color_clicked else self.default_color_clicked
        
        self.hover_enabled = hover_enabled
        self.is_toggle_on = is_toggle_on
        self.toggle = is_toggle_on
        self.disabled = disabled  # Fully disabled state
        self.semi_disabled = semi_disabled  # Semi-disabled state
        self.click_color_enabled = click_color_enabled  # Enables or disables click color change
        
        self.color = self.get_current_color()
        self.update_hover_color()

    def get_current_color(self):
        if self.disabled:
            return self.disabled_color
        elif self.semi_disabled:
            return self.semi_disabled_color
        return self.color_clicked if self.toggle else self.color_normal

    def update_hover_color(self):
        if not self.disabled:
            r, g, b = self.color
            self.color_hover = (min(r + 50, 255), min(g + 50, 255), min(b + 50, 255))
        else:
            self.color_hover = self.disabled_color  # No hover effect when disabled

    def set_disabled(self, disabled):
        """Enable or disable the button."""
        self.disabled = disabled
        self.color = self.get_current_color()
        self.update_hover_color()
    
    def set_semi_disabled(self, semi_disabled):
        """Enable or semi-disable the button. If clicked while semi-disabled, it becomes fully enabled."""
        self.semi_disabled = semi_disabled
        self.color = self.get_current_color()
        self.update_hover_color()

    def draw(self, surface):
        pg.draw.rect(surface, self.color, self.rect)
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(text_surface, (self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                                    self.rect.y + (self.rect.height - text_surface.get_height()) // 2))
    def change_button_text(self, new_text):
        self.text = new_text
    
    def handle_event(self, event):
        if self.disabled:
            return None  # Ignore events when fully disabled
        
        if event.type == pg.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            print(f"CLICKED on {self.text} at {event.pos}")
            
            if self.semi_disabled:
                self.set_semi_disabled(False)  # Clicking when semi-disabled enables the button
            
            if self.is_toggle_on:
                self.toggle = not self.toggle
                self.color = self.color_clicked if self.toggle else self.color_normal
            elif self.click_color_enabled:
                self.color = self.color_clicked
            
            self.update_hover_color()
            
            if self.action and not self.disabled:  # Click action still works when semi-disabled
                self.action()
            
            return self.target_state
        
        elif event.type == pg.MOUSEMOTION:
            if self.hover_enabled and self.rect.collidepoint(event.pos) and not self.semi_disabled:
                self.color = self.color_hover
            else:
                self.color = self.get_current_color()
        
        return None

    def get_id(self):
        return self.obj_id