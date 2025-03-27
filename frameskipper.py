class FrameSkipper:
    def __init__(self, skip_frames: int):
        self.skip_frames = skip_frames
        self.frame_count = 0

    def should_update(self) -> bool:
        """Returns True if this frame should update objects, False otherwise."""
        self.frame_count += 1
        if self.frame_count >= self.skip_frames:
            self.frame_count = 0
            return True
        return False