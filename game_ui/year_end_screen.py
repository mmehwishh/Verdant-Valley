"""
Year End Screen - Shows after completing 4 seasons (1 year)
Options: CONTINUE (next year), RESTART (fresh game), MAIN MENU

UI: Deep forest aesthetic — layered panels, animated particles,
    chromosome gene bars, score rings, gradient text effects.
"""

import pygame
import math
import random
from utils.constants import SCREEN_W, SCREEN_H


# ─────────────────────────────────────────────────────────────────────────────
#  Tiny helpers
# ─────────────────────────────────────────────────────────────────────────────

def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _draw_rounded_rect_gradient(surf, rect, color_top, color_bot, radius=12):
    """Vertical gradient inside a rounded rect (blitted via a temp surface)."""
    tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    for y in range(rect.h):
        t = y / max(rect.h - 1, 1)
        c = _lerp_color(color_top, color_bot, t)
        pygame.draw.line(tmp, c, (0, y), (rect.w, y))
    # mask rounded corners
    mask = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, rect.w, rect.h), border_radius=radius)
    tmp.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(tmp, (rect.x, rect.y))


def _draw_glowing_text(surf, text, font, x, y, color, glow_color, center=True):
    """Render text with a soft glow halo."""
    for offset in [3, 2, 1]:
        alpha = 60 // offset
        glow_surf = font.render(text, True, glow_color)
        glow_surf.set_alpha(alpha)
        gx = x - glow_surf.get_width() // 2 if center else x
        gy = y - glow_surf.get_height() // 2 if center else y
        for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
            surf.blit(glow_surf, (gx + dx, gy + dy))
    base = font.render(text, True, color)
    bx = x - base.get_width() // 2 if center else x
    by = y - base.get_height() // 2 if center else y
    surf.blit(base, (bx, by))


def _draw_arc_ring(surf, cx, cy, radius, width, value, max_val, color_fill, color_bg, start_angle=-120, span=240):
    """Draw a partial arc ring showing value/max_val progress."""
    steps = 80
    bg_end   = math.radians(start_angle + span)
    bg_start = math.radians(start_angle)
    # background arc
    for i in range(steps):
        t = i / steps
        a = bg_start + t * (bg_end - bg_start)
        for w in range(width):
            r = radius - w
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            pygame.draw.circle(surf, color_bg, (px, py), 1)
    # value arc
    ratio = min(max(value / max_val, 0), 1)
    val_end = bg_start + ratio * (bg_end - bg_start)
    for i in range(steps):
        t = i / steps
        a = bg_start + t * (val_end - bg_start)
        if a > val_end:
            break
        for w in range(width):
            r = radius - w
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            pygame.draw.circle(surf, color_fill, (px, py), 1)


def _draw_gene_bar(surf, x, y, w, h, value, label, color, font_tiny):
    """Horizontal bar for a single chromosome gene (0-1 range)."""
    bg_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (30, 40, 35), bg_rect, border_radius=4)
    fill_w = int(w * min(max(value, 0), 1))
    if fill_w > 0:
        fill_rect = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(surf, color, fill_rect, border_radius=4)
    pygame.draw.rect(surf, (80, 110, 90), bg_rect, 1, border_radius=4)
    lbl = font_tiny.render(f"{label}: {value:.2f}", True, (200, 215, 205))
    surf.blit(lbl, (x, y - 13))


# ─────────────────────────────────────────────────────────────────────────────
#  Particle system  (firefly / leaf particles for atmosphere)
# ─────────────────────────────────────────────────────────────────────────────

class _Particle:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, SCREEN_W)
        self.y = random.uniform(0, SCREEN_H)
        self.size = random.uniform(1.2, 3.2)
        self.speed = random.uniform(0.2, 0.7)
        self.drift = random.uniform(-0.3, 0.3)
        self.alpha = random.randint(30, 140)
        self.alpha_dir = random.choice([-1, 1])
        self.color = random.choice([
            (120, 220, 120), (200, 255, 160), (255, 220, 100), (160, 240, 200)
        ])

    def update(self):
        self.y -= self.speed
        self.x += self.drift
        self.alpha += self.alpha_dir * 1.5
        if self.alpha > 160:
            self.alpha_dir = -1
        if self.alpha < 20:
            self.alpha_dir = 1
        if self.y < -10 or self.x < -10 or self.x > SCREEN_W + 10:
            self.reset()
            self.y = SCREEN_H + 5

    def draw(self, surf):
        s = pygame.Surface((int(self.size * 2 + 2), int(self.size * 2 + 2)), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, int(self.alpha)), (int(self.size + 1), int(self.size + 1)), int(self.size))
        surf.blit(s, (int(self.x - self.size), int(self.y - self.size)))


# ─────────────────────────────────────────────────────────────────────────────
#  Main Screen Class
# ─────────────────────────────────────────────────────────────────────────────

class YearEndScreen:
    """End of year summary screen — rich forest-themed UI."""

    def __init__(
        self,
        screen,
        farmer_score,
        guard_score,
        animal_score,
        year,
        fox_fitness_before,
        rabbit_fitness_before,
        fox_chromo_before,
        rabbit_chromo_before,
        fox_fitness_after,
        rabbit_fitness_after,
        fox_chromo_after,
        rabbit_chromo_after,
    ):
        self.screen = screen
        self.farmer_score = farmer_score
        self.guard_score  = guard_score
        self.animal_score = animal_score
        self.year = year

        self.fox_before        = fox_fitness_before
        self.rabbit_before     = rabbit_fitness_before
        self.fox_after         = fox_fitness_after
        self.rabbit_after      = rabbit_fitness_after
        self.fox_chromo_before = fox_chromo_before
        self.fox_chromo_after  = fox_chromo_after
        self.rabbit_chromo_before = rabbit_chromo_before
        self.rabbit_chromo_after  = rabbit_chromo_after

        # ── Fonts ──────────────────────────────────────────────────────────────
        self.font_title  = pygame.font.Font(None, 52)
        self.font_large  = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 26)
        self.font_small  = pygame.font.Font(None, 20)
        self.font_tiny   = pygame.font.Font(None, 16)

        # ── Palette ────────────────────────────────────────────────────────────
        self.C = {
            "bg_dark":    (10, 18, 12),
            "bg_mid":     (16, 28, 20),
            "panel_top":  (22, 38, 28),
            "panel_bot":  (14, 24, 18),
            "border":     (60, 110, 75),
            "border_hi":  (100, 180, 120),
            "gold":       (255, 210, 60),
            "gold_dim":   (180, 140, 30),
            "green_hi":   (90, 230, 110),
            "green_dim":  (40, 120, 55),
            "red_hi":     (255, 90, 90),
            "red_dim":    (140, 40, 40),
            "orange":     (255, 150, 60),
            "fox":        (255, 130, 50),
            "rabbit":     (180, 140, 255),
            "farmer":     (80, 200, 100),
            "guard":      (255, 100, 100),
            "animal":     (255, 190, 80),
            "text":       (215, 228, 218),
            "text_dim":   (140, 160, 145),
            "white":      (240, 245, 240),
        }

        # ── Particles ──────────────────────────────────────────────────────────
        self._particles = [_Particle() for _ in range(45)]

        # ── Animation tick ────────────────────────────────────────────────────
        self._tick = 0

        # ── Buttons ────────────────────────────────────────────────────────────
        btn_w, btn_h = 168, 48
        gap          = 20
        total_w      = btn_w * 3 + gap * 2
        bx           = (SCREEN_W - total_w) // 2
        by           = SCREEN_H - 72

        self.continue_btn = pygame.Rect(bx,                   by, btn_w, btn_h)
        self.restart_btn  = pygame.Rect(bx + btn_w + gap,     by, btn_w, btn_h)
        self.menu_btn     = pygame.Rect(bx + (btn_w + gap)*2, by, btn_w, btn_h)

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC DRAW ENTRY POINT
    # ══════════════════════════════════════════════════════════════════════════

    def draw(self):
        self._tick += 1

        # ── Background ────────────────────────────────────────────────────────
        self._draw_background()

        # ── Particles ─────────────────────────────────────────────────────────
        for p in self._particles:
            p.update()
            p.draw(self.screen)

        # ── Header ────────────────────────────────────────────────────────────
        self._draw_header()

        # ── Two-column body ───────────────────────────────────────────────────
        self._draw_scores_panel()
        self._draw_evolution_panel()

        # ── Footer / Buttons ──────────────────────────────────────────────────
        self._draw_buttons()
        self._draw_footer()

    # ══════════════════════════════════════════════════════════════════════════
    #  BACKGROUND
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_background(self):
        """Radial vignette background + faint hex grid."""
        self.screen.fill(self.C["bg_dark"])

        # Soft radial glow at centre
        glow = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for r in range(300, 0, -6):
            alpha = max(0, int(18 - r * 0.05))
            pygame.draw.circle(glow, (30, 80, 40, alpha), (SCREEN_W // 2, SCREEN_H // 2), r)
        self.screen.blit(glow, (0, 0))

        # Faint horizontal scanlines for texture
        for y in range(0, SCREEN_H, 4):
            pygame.draw.line(self.screen, (0, 0, 0), (0, y), (SCREEN_W, y))

        # Corner leaf silhouette hints (just small triangles, decorative)
        leaf_color = (20, 40, 25)
        for cx, cy, flip in [(0, 0, 1), (SCREEN_W, 0, -1), (0, SCREEN_H, 1), (SCREEN_W, SCREEN_H, -1)]:
            pts = [(cx, cy), (cx + flip*90, cy), (cx, cy + (90 if cy == 0 else -90))]
            pygame.draw.polygon(self.screen, leaf_color, pts)

    # ══════════════════════════════════════════════════════════════════════════
    #  HEADER
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_header(self):
        # Pulsing crown / medal emoji row (drawn as coloured dots arc)
        pulse = 0.5 + 0.5 * math.sin(self._tick * 0.04)
        star_color = _lerp_color(self.C["gold_dim"], self.C["gold"], pulse)

        cx = SCREEN_W // 2
        for i, angle_deg in enumerate(range(-60, 61, 20)):
            angle = math.radians(angle_deg)
            sx = cx + int(math.sin(angle) * 55)
            sy = 28 + int(-math.cos(angle) * 18)
            size = 4 if abs(angle_deg) < 15 else 3
            pygame.draw.circle(self.screen, star_color, (sx, sy), size)

        # Main title with glow
        _draw_glowing_text(
            self.screen,
            f"✦  YEAR  {self.year}  COMPLETE  ✦",
            self.font_title,
            cx, 62,
            self.C["gold"],
            self.C["gold_dim"],
        )

        # Subtitle
        sub = self.font_small.render(
            "Four seasons survived — Evolution reshapes the land", True, self.C["text_dim"]
        )
        self.screen.blit(sub, (cx - sub.get_width() // 2, 94))

        # Gold separator line
        line_y = 114
        for i in range(SCREEN_W):
            t = i / SCREEN_W
            alpha = int(80 + 120 * math.sin(t * math.pi))
            c = _lerp_color(self.C["bg_dark"], self.C["border_hi"], alpha / 200)
            pygame.draw.line(self.screen, c, (i, line_y), (i, line_y + 1))

    # ══════════════════════════════════════════════════════════════════════════
    #  SCORES PANEL  (left column)
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_scores_panel(self):
        panel = pygame.Rect(30, 124, 310, 310)
        _draw_rounded_rect_gradient(self.screen, panel, self.C["panel_top"], self.C["panel_bot"], 14)
        pygame.draw.rect(self.screen, self.C["border"], panel, 2, border_radius=14)

        # Panel title
        t = self.font_medium.render("◈  SEASON SCORES", True, self.C["gold"])
        self.screen.blit(t, (panel.x + 16, panel.y + 12))
        pygame.draw.line(
            self.screen, self.C["border"],
            (panel.x + 12, panel.y + 34), (panel.right - 12, panel.y + 34)
        )

        # Three score rings
        ring_data = [
            ("FARMER", self.farmer_score, 500, self.C["farmer"], "🌾", panel.x + 65, panel.y + 100),
            ("GUARD",  self.guard_score,  500, self.C["guard"],  "🛡", panel.x + 155, panel.y + 100),
            ("ANIMAL", self.animal_score, 500, self.C["animal"], "🐾", panel.x + 245, panel.y + 100),
        ]

        for label, score, max_s, color, icon, rx, ry in ring_data:
            _draw_arc_ring(
                self.screen, rx, ry, 36, 7,
                score, max_s,
                color, (35, 50, 40),
            )
            score_txt = self.font_medium.render(str(score), True, color)
            self.screen.blit(score_txt, (rx - score_txt.get_width() // 2, ry - 11))
            lbl = self.font_tiny.render(label, True, self.C["text_dim"])
            self.screen.blit(lbl, (rx - lbl.get_width() // 2, ry + 44))

        # Combined total
        total = self.farmer_score + self.guard_score + self.animal_score
        pygame.draw.line(
            self.screen, self.C["border"],
            (panel.x + 12, panel.y + 158), (panel.right - 12, panel.y + 158)
        )

        tot_lbl = self.font_small.render("COMBINED TOTAL", True, self.C["text_dim"])
        self.screen.blit(tot_lbl, (panel.x + panel.w // 2 - tot_lbl.get_width() // 2, panel.y + 166))

        tot_val = self.font_large.render(str(total), True, self.C["gold"])
        self.screen.blit(tot_val, (panel.x + panel.w // 2 - tot_val.get_width() // 2, panel.y + 185))

        # Score breakdown bars
        bar_x  = panel.x + 20
        bar_w  = panel.w - 40
        bar_h  = 12
        bar_y0 = panel.y + 222

        for i, (lbl, score, color) in enumerate([
            ("Farmer", self.farmer_score, self.C["farmer"]),
            ("Guard",  self.guard_score,  self.C["guard"]),
            ("Animal", self.animal_score, self.C["animal"]),
        ]):
            by = bar_y0 + i * 26
            bg_r = pygame.Rect(bar_x, by, bar_w, bar_h)
            pygame.draw.rect(self.screen, (25, 40, 30), bg_r, border_radius=6)
            fill = int(bar_w * min(score / 500, 1))
            if fill > 0:
                pygame.draw.rect(self.screen, color,
                                 pygame.Rect(bar_x, by, fill, bar_h), border_radius=6)
            pygame.draw.rect(self.screen, self.C["border"], bg_r, 1, border_radius=6)
            l = self.font_tiny.render(f"{lbl}  {score}", True, self.C["text"])
            self.screen.blit(l, (bar_x + 4, by - 13))

        # Year progression indicator
        pygame.draw.line(
            self.screen, self.C["border"],
            (panel.x + 12, panel.y + 300), (panel.right - 12, panel.y + 300)
        )
        yr_txt = self.font_small.render(
            f"Year {self.year}  ──►  Year {self.year + 1}", True, self.C["text_dim"]
        )
        self.screen.blit(yr_txt, (panel.x + panel.w // 2 - yr_txt.get_width() // 2, panel.y + 306))

    # ══════════════════════════════════════════════════════════════════════════
    #  EVOLUTION PANEL  (right column)
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_evolution_panel(self):
        panel = pygame.Rect(354, 124, SCREEN_W - 384, 310)
        _draw_rounded_rect_gradient(self.screen, panel, self.C["panel_top"], self.C["panel_bot"], 14)
        pygame.draw.rect(self.screen, self.C["border"], panel, 2, border_radius=14)

        t = self.font_medium.render("◈  EVOLUTION SUMMARY", True, self.C["gold"])
        self.screen.blit(t, (panel.x + 16, panel.y + 12))
        pygame.draw.line(
            self.screen, self.C["border"],
            (panel.x + 12, panel.y + 34), (panel.right - 12, panel.y + 34)
        )

        half_w = (panel.w - 36) // 2

        # ── Fox section ───────────────────────────────────────────────────────
        fox_panel = pygame.Rect(panel.x + 12, panel.y + 42, half_w, 260)
        pygame.draw.rect(self.screen, (18, 30, 22), fox_panel, border_radius=10)
        pygame.draw.rect(self.screen, self.C["fox"], fox_panel, 1, border_radius=10)

        fx_lbl = self.font_medium.render("🦊  FOX", True, self.C["fox"])
        self.screen.blit(fx_lbl, (fox_panel.x + 10, fox_panel.y + 8))

        self._draw_fitness_change(
            fox_panel.x + 10, fox_panel.y + 34,
            self.fox_before, self.fox_after, self.C["fox"]
        )
        self._draw_chromosome_section(
            fox_panel.x + 10, fox_panel.y + 110,
            fox_panel.w - 20,
            self.fox_chromo_after,
            self.C["fox"],
            self.C["fox"],
        )

        # ── Rabbit section ────────────────────────────────────────────────────
        rab_panel = pygame.Rect(panel.x + 24 + half_w, panel.y + 42, half_w, 260)
        pygame.draw.rect(self.screen, (18, 30, 22), rab_panel, border_radius=10)
        pygame.draw.rect(self.screen, self.C["rabbit"], rab_panel, 1, border_radius=10)

        rb_lbl = self.font_medium.render("🐇  RABBIT", True, self.C["rabbit"])
        self.screen.blit(rb_lbl, (rab_panel.x + 10, rab_panel.y + 8))

        self._draw_fitness_change(
            rab_panel.x + 10, rab_panel.y + 34,
            self.rabbit_before, self.rabbit_after, self.C["rabbit"]
        )
        self._draw_chromosome_section(
            rab_panel.x + 10, rab_panel.y + 110,
            rab_panel.w - 20,
            self.rabbit_chromo_after,
            self.C["rabbit"],
            self.C["rabbit"],
        )

    def _draw_fitness_change(self, x, y, before, after, color):
        """Compact before→after fitness with delta badge."""
        change = after - before
        sign   = "+" if change >= 0 else ""
        delta_color = self.C["green_hi"] if change >= 0 else self.C["red_hi"]
        bg_color    = (20, 60, 30) if change >= 0 else (60, 20, 20)

        # Labels
        b_lbl = self.font_tiny.render("BEFORE", True, self.C["text_dim"])
        a_lbl = self.font_tiny.render("AFTER", True, self.C["text_dim"])
        self.screen.blit(b_lbl, (x, y))
        self.screen.blit(a_lbl, (x + 76, y))

        b_val = self.font_large.render(f"{before:.0f}", True, self.C["text"])
        a_val = self.font_large.render(f"{after:.0f}", True, color)
        arr   = self.font_medium.render("→", True, self.C["gold"])
        self.screen.blit(b_val, (x, y + 14))
        self.screen.blit(arr, (x + 50, y + 18))
        self.screen.blit(a_val, (x + 76, y + 14))

        # Delta badge
        badge = pygame.Rect(x, y + 50, 130, 22)
        pygame.draw.rect(self.screen, bg_color, badge, border_radius=6)
        pygame.draw.rect(self.screen, delta_color, badge, 1, border_radius=6)
        delta_txt = self.font_tiny.render(
            f"{sign}{change:.0f}  fitness points", True, delta_color
        )
        self.screen.blit(delta_txt, (badge.x + 6, badge.y + 4))

        # Mini spark line (just decorative dots showing trend direction)
        for i in range(8):
            t = i / 7
            sx = x + int(t * 120)
            trend = before + (after - before) * t
            norm = (trend - min(before, after)) / max(abs(change), 1)
            sy = y + 88 - int(norm * 12)
            dot_c = _lerp_color(self.C["text_dim"], color, t)
            pygame.draw.circle(self.screen, dot_c, (sx, sy), 2)

    def _draw_chromosome_section(self, x, y, w, chromo, bar_color, accent):
        """Draw gene bars from a chromosome dict."""
        if not chromo:
            no_data = self.font_tiny.render("No chromosome data", True, self.C["text_dim"])
            self.screen.blit(no_data, (x, y))
            return

        lbl = self.font_tiny.render("-", True, accent)
        self.screen.blit(lbl, (x, y))

        gene_map = {
            "crop_attraction": "Crop Attr",
            "guard_avoidance": "Guard Avoid",
            "speed":           "Speed",
            "boldness":        "Boldness",
            "stealth":         "Stealth",
            "endurance":       "Endurance",
        }

        bar_w = w - 10
        bar_h = 8
        spacing = 28
        # Pick a gradient per bar
        colors = [
            (100, 220, 130), (220, 130, 80), (100, 180, 255),
            (220, 80, 80), (180, 220, 100), (100, 200, 200)
        ]

        drawn = 0
        for i, (key, friendly) in enumerate(gene_map.items()):
            val = chromo.get(key)
            if val is None:
                continue
            by = y + 16 + drawn * spacing
            # bg track
            bg_r = pygame.Rect(x, by, bar_w, bar_h)
            pygame.draw.rect(self.screen, (28, 42, 33), bg_r, border_radius=4)
            # fill
            fill_w = int(bar_w * min(max(val, 0), 1))
            if fill_w:
                pygame.draw.rect(
                    self.screen, colors[i % len(colors)],
                    pygame.Rect(x, by, fill_w, bar_h), border_radius=4
                )
            pygame.draw.rect(self.screen, (60, 90, 70), bg_r, 1, border_radius=4)
            lbl_t = self.font_tiny.render(f"{friendly}: {val:.2f}", True, self.C["text"])
            self.screen.blit(lbl_t, (x, by - 12))
            drawn += 1

    # ══════════════════════════════════════════════════════════════════════════
    #  BUTTONS
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_buttons(self):
        mouse_pos = pygame.mouse.get_pos()
        pulse = 0.5 + 0.5 * math.sin(self._tick * 0.05)

        btn_specs = [
            (self.continue_btn, "▶  CONTINUE",  (30, 100, 55), (55, 160, 85),  self.C["green_hi"], True),
            (self.restart_btn,  "↺  RESTART",   (100, 50, 30), (160, 80, 50),  self.C["orange"],   False),
            (self.menu_btn,     "⌂  MAIN MENU", (40, 50, 80),  (65, 80, 120),  self.C["rabbit"],   False),
        ]

        for rect, label, col_base, col_hover, text_color, primary in btn_specs:
            hovered = rect.collidepoint(mouse_pos)
            base_c  = _lerp_color(col_base, col_hover, 0.4 * pulse if (primary and not hovered) else 0)
            color   = col_hover if hovered else base_c

            # Shadow
            shadow = pygame.Rect(rect.x + 3, rect.y + 3, rect.w, rect.h)
            shadow_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 80), (0, 0, rect.w, rect.h), border_radius=12)
            self.screen.blit(shadow_surf, (shadow.x, shadow.y))

            # Body
            pygame.draw.rect(self.screen, color, rect, border_radius=12)

            # Border — brighter on hover
            border_c = text_color if hovered else self.C["border"]
            pygame.draw.rect(self.screen, border_c, rect, 2, border_radius=12)

            # Shimmer line on top edge
            shine = pygame.Rect(rect.x + 8, rect.y + 2, rect.w - 16, 2)
            pygame.draw.rect(self.screen, (*[min(255, c + 60) for c in color],), shine, border_radius=2)

            # Label
            lbl = self.font_medium.render(label, True, text_color if hovered else self.C["text"])
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ══════════════════════════════════════════════════════════════════════════
    #  FOOTER
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_footer(self):
        # Thin separator
        sep_y = SCREEN_H - 80
        for i in range(SCREEN_W):
            t = i / SCREEN_W
            a = int(60 + 80 * math.sin(t * math.pi))
            c = _lerp_color(self.C["bg_dark"], self.C["border"], a / 140)
            pygame.draw.line(self.screen, c, (i, sep_y), (i, sep_y + 1))

        # Tip text
        tip = self.font_tiny.render(
            "Evolution runs between years — stronger traits persist, weaker ones fade",
            True, self.C["text_dim"]
        )
        self.screen.blit(tip, (SCREEN_W // 2 - tip.get_width() // 2, SCREEN_H - 18))

    # ══════════════════════════════════════════════════════════════════════════
    #  EVENT HANDLING  (unchanged external interface)
    # ══════════════════════════════════════════════════════════════════════════

    def handle_event(self, event):
        """Process mouse clicks — returns 'continue', 'restart', 'menu', or None."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.continue_btn.collidepoint(event.pos):
                return "continue"
            if self.restart_btn.collidepoint(event.pos):
                return "restart"
            if self.menu_btn.collidepoint(event.pos):
                return "menu"
        return None