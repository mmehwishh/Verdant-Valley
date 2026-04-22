import pygame


class Animation:
    def __init__(
        self, sprite_sheet_path, frame_width, frame_height, rows, cols, scale=1
    ):
        self.sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.rows = rows
        self.cols = cols
        self.scale = scale

        sheet_width = self.sheet.get_width()
        sheet_height = self.sheet.get_height()

        print(f"Sheet: {sheet_width}x{sheet_height}")
        print(f"Frames: {rows}x{cols}, each {frame_width}x{frame_height}")

        self.frames = []
        for row in range(rows):
            row_frames = []
            for col in range(cols):
                x = col * frame_width
                y = row * frame_height

                if x + frame_width <= sheet_width and y + frame_height <= sheet_height:
                    frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
                    frame.blit(self.sheet, (0, 0), (x, y, frame_width, frame_height))

                    if scale != 1:
                        new_size = (int(frame_width * scale), int(frame_height * scale))
                        frame = pygame.transform.scale(frame, new_size)

                    row_frames.append(frame)

            if row_frames:
                self.frames.append(row_frames)

        self.current_row = 0
        self.current_frame = 0
        self.animation_speed = 0.12
        self.animation_timer = 0

        print(
            f"✓ Loaded {len(self.frames)} rows, {len(self.frames[0]) if self.frames else 0} frames per row"
        )

    def set_direction(self, row):
        if 0 <= row < len(self.frames):
            self.current_row = row
            if self.current_frame >= len(self.frames[self.current_row]):
                self.current_frame = 0

    def update(self):
        if not self.frames:
            return
        self.animation_timer += self.animation_speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            self.current_frame = (self.current_frame + 1) % len(
                self.frames[self.current_row]
            )

    def get_frame(self):
        if self.frames and self.current_row < len(self.frames):
            if self.current_frame < len(self.frames[self.current_row]):
                return self.frames[self.current_row][self.current_frame]
        fallback = pygame.Surface((48, 48), pygame.SRCALPHA)
        fallback.fill((150, 150, 150))
        return fallback

    def reset(self):
        self.current_frame = 0
        self.animation_timer = 0
