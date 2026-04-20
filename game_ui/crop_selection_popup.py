"""
game_ui/crop_selection_popup.py
Shown when all crops are harvested/eaten.
Offers:
  - AUTO PLANT  → CSP re-generates the farm layout immediately
  - MANUAL SELECT → user picks a crop type + quantity; farmer physically
                    walks to each tile and plants before harvesting begins
"""

import pygame
from utils.constants import (
    SCREEN_W, SCREEN_H,
    CROP_WHEAT, CROP_SUNFLOWER, CROP_CORN, CROP_TOMATO, CROP_CARROT, CROP_POTATO,
    CROP_NAMES,
)

# ── Crop catalogue shown in manual mode ──────────────────────────────────────
CROP_OPTIONS = [
    (CROP_WHEAT,     "Wheat",     "🌾", (220, 200, 100)),
    (CROP_SUNFLOWER, "Sunflower", "🌻", (255, 210,  50)),
    (CROP_CORN,      "Corn",      "🌽", (255, 230,  80)),
    (CROP_TOMATO,    "Tomato",    "🍅", (230,  70,  70)),
    (CROP_CARROT,    "Carrot",    "🥕", (255, 140,  40)),
    (CROP_POTATO,    "Potato",    "🥔", (180, 140,  90)),
]

MIN_CROPS = 1
MAX_CROPS = 12


class CropSelectionPopup:
    """
    Modal popup that appears when the field is empty.

    Public interface
    ----------------
    popup.update()          → call every frame; returns None while active
    popup.draw()            → render to screen
    popup.handle_event(ev)  → feed pygame events
    popup.result            → None | "auto" | ("manual", crop_id, count)
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.result = None          # set when user confirms a choice
        self._phase = "choose"      # "choose" | "manual"

        # Manual-selection state
        self._selected_crop_idx = 0
        self._crop_count = 4

        # Fonts
        self._f_title  = pygame.font.Font(None, 46)
        self._f_head   = pygame.font.Font(None, 30)
        self._f_body   = pygame.font.Font(None, 24)
        self._f_small  = pygame.font.Font(None, 20)

        # Animation
        self._alpha = 0             # fade-in
        self._overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        # Panel dimensions
        self._pw = 560
        self._ph_choose = 260
        self._ph_manual = 420
        self._px = (SCREEN_W - self._pw) // 2

        # Button rects (rebuilt each draw — safe for all resolutions)
        self._btn_auto   = pygame.Rect(0, 0, 0, 0)
        self._btn_manual = pygame.Rect(0, 0, 0, 0)
        self._btn_confirm= pygame.Rect(0, 0, 0, 0)
        self._btn_back   = pygame.Rect(0, 0, 0, 0)
        self._crop_rects : list[pygame.Rect] = []
        self._btn_minus  = pygame.Rect(0, 0, 0, 0)
        self._btn_plus   = pygame.Rect(0, 0, 0, 0)

    # ── Public ────────────────────────────────────────────────────────────────

    def update(self) -> bool:
        """Returns True when the popup is finished (result is set)."""
        self._alpha = min(255, self._alpha + 18)
        return self.result is not None

    def handle_event(self, event: pygame.event.Event):
        if self.result is not None:
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            if self._phase == "choose":
                if self._btn_auto.collidepoint(pos):
                    self.result = "auto"
                elif self._btn_manual.collidepoint(pos):
                    self._phase = "manual"

            elif self._phase == "manual":
                # Crop selector cards
                for i, rect in enumerate(self._crop_rects):
                    if rect.collidepoint(pos):
                        self._selected_crop_idx = i

                # Count buttons
                if self._btn_minus.collidepoint(pos):
                    self._crop_count = max(MIN_CROPS, self._crop_count - 1)
                if self._btn_plus.collidepoint(pos):
                    self._crop_count = min(MAX_CROPS, self._crop_count + 1)

                if self._btn_confirm.collidepoint(pos):
                    crop_id = CROP_OPTIONS[self._selected_crop_idx][0]
                    self.result = ("manual", crop_id, self._crop_count)

                if self._btn_back.collidepoint(pos):
                    self._phase = "choose"

        if event.type == pygame.KEYDOWN:
            if self._phase == "manual":
                if event.key == pygame.K_LEFT:
                    self._crop_count = max(MIN_CROPS, self._crop_count - 1)
                if event.key == pygame.K_RIGHT:
                    self._crop_count = min(MAX_CROPS, self._crop_count + 1)
                if event.key == pygame.K_RETURN:
                    crop_id = CROP_OPTIONS[self._selected_crop_idx][0]
                    self.result = ("manual", crop_id, self._crop_count)

    def draw(self):
        # Dim background
        self._overlay.fill((0, 0, 0, min(160, self._alpha)))
        self.screen.blit(self._overlay, (0, 0))

        if self._phase == "choose":
            self._draw_choose_phase()
        else:
            self._draw_manual_phase()

    # ── Drawing helpers ────────────────────────────────────────────────────────

    def _panel_y(self, ph):
        return (SCREEN_H - ph) // 2

    def _draw_panel(self, ph):
        py = self._panel_y(ph)
        # Drop shadow
        shadow = pygame.Rect(self._px + 6, py + 6, self._pw, ph)
        pygame.draw.rect(self.screen, (0, 0, 0, 120), shadow, border_radius=18)
        # Panel body
        panel_rect = pygame.Rect(self._px, py, self._pw, ph)
        pygame.draw.rect(self.screen, (22, 30, 22), panel_rect, border_radius=18)
        pygame.draw.rect(self.screen, (90, 140, 90), panel_rect, 2, border_radius=18)
        return py

    def _draw_title(self, py, text, sub=None):
        t = self._f_title.render(text, True, (255, 215, 0))
        tr = t.get_rect(centerx=SCREEN_W // 2, top=py + 22)
        self.screen.blit(t, tr)
        if sub:
            s = self._f_small.render(sub, True, (160, 200, 160))
            sr = s.get_rect(centerx=SCREEN_W // 2, top=tr.bottom + 4)
            self.screen.blit(s, sr)
            return sr.bottom
        return tr.bottom

    def _wood_button(self, rect, label, hovered=False, disabled=False):
        base  = (80, 80, 80)   if disabled else (140, 105, 65) if hovered else (100, 70, 40)
        border= (110,110,110)  if disabled else (80, 150, 80)
        lbl_c = (150,150,150)  if disabled else (255, 215, 0)
        pygame.draw.rect(self.screen, base, rect, border_radius=10)
        pygame.draw.rect(self.screen, border, rect, 2, border_radius=10)
        lbl = self._f_body.render(label, True, lbl_c)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_choose_phase(self):
        ph = self._ph_choose
        py = self._draw_panel(ph)
        bottom = self._draw_title(py, "Field is Empty!",
                                   "All crops have been harvested. What next?")

        mouse = pygame.mouse.get_pos()
        bw, bh = 200, 56
        gap = 24
        total = bw * 2 + gap
        lx = SCREEN_W // 2 - total // 2
        by = bottom + 28

        self._btn_auto   = pygame.Rect(lx,        by, bw, bh)
        self._btn_manual = pygame.Rect(lx + bw + gap, by, bw, bh)

        self._wood_button(self._btn_auto,   "⚡ Auto Plant",
                          self._btn_auto.collidepoint(mouse))
        self._wood_button(self._btn_manual, "✋ Manual Select",
                          self._btn_manual.collidepoint(mouse))

        # Tiny captions
        ac = self._f_small.render("CSP generates the layout", True, (130, 170, 130))
        mc = self._f_small.render("You choose crop & count",  True, (130, 170, 130))
        self.screen.blit(ac, ac.get_rect(centerx=self._btn_auto.centerx,
                                          top=self._btn_auto.bottom + 6))
        self.screen.blit(mc, mc.get_rect(centerx=self._btn_manual.centerx,
                                          top=self._btn_manual.bottom + 6))

    def _draw_manual_phase(self):
        ph = self._ph_manual
        py = self._draw_panel(ph)
        bottom = self._draw_title(py, "Choose Your Crop")

        mouse = pygame.mouse.get_pos()

        # ── Crop cards ─────────────────────────────────────────────────────
        card_w, card_h = 78, 78
        cols = len(CROP_OPTIONS)
        spacing = 14
        row_w = cols * card_w + (cols - 1) * spacing
        cx_start = SCREEN_W // 2 - row_w // 2
        cy = bottom + 18

        self._crop_rects = []
        for i, (_, name, emoji, color) in enumerate(CROP_OPTIONS):
            rx = cx_start + i * (card_w + spacing)
            rect = pygame.Rect(rx, cy, card_w, card_h)
            self._crop_rects.append(rect)

            selected  = (i == self._selected_crop_idx)
            hov       = rect.collidepoint(mouse)
            bg        = (40, 55, 40) if not selected else (30, 60, 30)
            border_c  = color        if selected     else ((80, 120, 80) if hov else (50, 70, 50))
            border_w  = 3            if selected     else 1

            pygame.draw.rect(self.screen, bg, rect, border_radius=10)
            pygame.draw.rect(self.screen, border_c, rect, border_w, border_radius=10)

            em = self._f_head.render(emoji, True, color)
            self.screen.blit(em, em.get_rect(centerx=rect.centerx, top=rect.top + 10))

            nm = self._f_small.render(name, True, color if selected else (170, 190, 170))
            self.screen.blit(nm, nm.get_rect(centerx=rect.centerx, bottom=rect.bottom - 8))

        # ── Count selector ─────────────────────────────────────────────────
        count_y = cy + card_h + 24
        label = self._f_head.render("How many crops?", True, (200, 210, 200))
        self.screen.blit(label, label.get_rect(centerx=SCREEN_W // 2, top=count_y))

        bsz = 36
        count_center_y = count_y + 40
        self._btn_minus = pygame.Rect(SCREEN_W // 2 - 80 - bsz, count_center_y, bsz, bsz)
        self._btn_plus  = pygame.Rect(SCREEN_W // 2 + 80,        count_center_y, bsz, bsz)

        for btn, lbl in ((self._btn_minus, "−"), (self._btn_plus, "+")):
            hov = btn.collidepoint(mouse)
            pygame.draw.rect(self.screen, (60, 90, 60) if hov else (40, 60, 40), btn, border_radius=8)
            pygame.draw.rect(self.screen, (100, 160, 100), btn, 2, border_radius=8)
            t = self._f_head.render(lbl, True, (255, 215, 0))
            self.screen.blit(t, t.get_rect(center=btn.center))

        count_txt = self._f_title.render(str(self._crop_count), True, (255, 215, 0))
        self.screen.blit(count_txt, count_txt.get_rect(centerx=SCREEN_W // 2,
                                                         centery=count_center_y + bsz // 2))

        hint = self._f_small.render("← → or buttons to adjust", True, (120, 150, 120))
        self.screen.blit(hint, hint.get_rect(centerx=SCREEN_W // 2,
                                               top=count_center_y + bsz + 6))

        # ── Confirm / Back ─────────────────────────────────────────────────
        action_y = count_center_y + bsz + 36
        bw, bh = 170, 50
        gap = 20
        lx = SCREEN_W // 2 - bw - gap // 2

        self._btn_back    = pygame.Rect(lx,        action_y, bw, bh)
        self._btn_confirm = pygame.Rect(lx + bw + gap, action_y, bw, bh)

        self._wood_button(self._btn_back,    "← Back",
                          self._btn_back.collidepoint(mouse))
        self._wood_button(self._btn_confirm, "✅ Start Planting",
                          self._btn_confirm.collidepoint(mouse))