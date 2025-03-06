import pygame as pg

class Button:
    def __init__(self, x, y, width, height, text, target_state, action=None):
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.target_state = target_state  # Store the target state for the button click
        self.action = action  # Optional action to call when clicked
        self.font = pg.font.Font(None, 36)  # Font for text rendering
        
        # Button colors
        self.color_normal = (100, 100, 200)  # Normal color
        self.color_hover = (150, 150, 255)   # Hover color
        self.color_clicked = (50, 50, 150)  # Clicked color
        self.color = self.color_normal  # Initial color is normal

    def draw(self, surface):
        """Draw the button on the screen with current color."""
        pg.draw.rect(surface, self.color, self.rect)  # Draw the button with current color
        text_surface = self.font.render(self.text, True, (255, 255, 255))  # White text
        surface.blit(text_surface, (self.rect.x + (self.rect.width - text_surface.get_width()) // 2,
                                    self.rect.y + (self.rect.height - text_surface.get_height()) // 2))


    def handle_event(self, event):
        """Handle mouse events (clicks and hover) on the button."""
        if event.type == pg.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):  # If the button was clicked
                print(f"CLICKED on {self.text} at {event.pos}")
                if self.action:
                    self.action()  # Call the action (if any)
                self.color = self.color_clicked  # Change the color to clicked
                return self.target_state  # Return the target state (used in the main game loop)
        
        elif event.type == pg.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):  # If the mouse is hovering over the button
                self.color = self.color_hover  # Change to hover color
            else:
                self.color = self.color_normal  # Change back to normal color
        
        return None  # No state change if no click is detected

