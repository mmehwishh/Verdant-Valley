"""
Metrics Panel - Display simulation statistics
"""

import pygame
from utils.constants import *
from utils.helpers import draw_rounded_rect, draw_text
from game_ui.fonts import FontCache


class MetricsPanel:
    def __init__(self, screen):
        self.screen = screen
        self.panel_height = 120
        self.panel_y = SCREEN_H - self.panel_height

    def draw(self, grid, agents):
        """Draw comprehensive farming simulation metrics panel"""
        panel_rect = pygame.Rect(0, self.panel_y, SCREEN_W, self.panel_height)
        panel_surface = pygame.Surface((SCREEN_W, self.panel_height), pygame.SRCALPHA)
        panel_surface.fill((25, 32, 28, 220))
        draw_rounded_rect(
            panel_surface,
            (25, 32, 28, 240),
            pygame.Rect(8, 8, SCREEN_W - 16, self.panel_height - 16),
            radius=18,
            border=2,
            border_color=(100, 140, 90),
        )
        self.screen.blit(panel_surface, (0, self.panel_y))

        f_title = FontCache.get(FONT_MEDIUM, bold=True)
        f_normal = FontCache.get(FONT_SMALL)
        f_tiny = FontCache.get(FONT_TINY)

        metrics = self._calculate_metrics(grid, agents)

        x = 24
        sections = [
            ("🌾 Crops", self._draw_crop_metrics, metrics['crops']),
            ("👥 Agents", self._draw_agent_metrics, metrics['agents']),
            ("📈 Performance", self._draw_performance_metrics, metrics['performance']),
            ("🌤️ Status", self._draw_status_metrics, metrics['status'])
        ]

        for title, draw_func, data in sections:
            section_width = 280
            if x + section_width > SCREEN_W - 20:
                break

            header_rect = pygame.Rect(x - 8, self.panel_y + 10, section_width, 28)
            draw_rounded_rect(
                self.screen,
                (20, 28, 24, 200),
                header_rect,
                radius=10,
            )
            title_text = f_title.render(title, True, C_TEXT_GOLD)
            self.screen.blit(title_text, (x, self.panel_y + 14))

            draw_func(x, self.panel_y + 42, section_width - 24, data, f_normal, f_tiny)
            x += section_width + 20

    def _calculate_metrics(self, grid, agents):
        """Calculate all metrics from current game state"""
        crops = {
            'planted': 0,
            'ready': 0,
            'harvested_value': 0,
            'by_type': {CROP_WHEAT: 0, CROP_SUNFLOWER: 0, CROP_CORN: 0}
        }

        agents_data = {
            'farmers': {'count': 0, 'total_score': 0, 'active': 0},
            'guards': {'count': 0, 'total_score': 0, 'active': 0},
            'animals': {'count': 0, 'total_score': 0, 'alive': 0, 'crops_eaten': 0}
        }

        # Analyze crops
        for c, r in grid.crop_tiles():
            tile = grid.get(c, r)
            crops['planted'] += 1
            crops['by_type'][tile.crop] += 1
            if tile.crop_stage >= 2:  # Ready to harvest
                crops['ready'] += 1
                crops['harvested_value'] += CROP_VALUE[tile.crop] * tile.crop_stage

        # Analyze agents
        for agent in agents:
            if hasattr(agent, 'alive') and not agent.alive:
                continue

            if 'Farmer' in agent.name:
                agents_data['farmers']['count'] += 1
                agents_data['farmers']['total_score'] += agent.score
                if agent.moving or agent.state != 'idle':
                    agents_data['farmers']['active'] += 1
            elif 'Guard' in agent.name:
                agents_data['guards']['count'] += 1
                agents_data['guards']['total_score'] += agent.score
                if agent.moving or agent.state != 'idle':
                    agents_data['guards']['active'] += 1
            elif 'Animal' in agent.name:
                agents_data['animals']['count'] += 1
                agents_data['animals']['total_score'] += agent.score
                if agent.alive:
                    agents_data['animals']['alive'] += 1
                if hasattr(agent, 'crops_eaten'):
                    agents_data['animals']['crops_eaten'] += agent.crops_eaten

        performance = {
            'efficiency': crops['harvested_value'] / max(1, crops['planted']) if crops['planted'] > 0 else 0,
            'protection': (agents_data['animals']['crops_eaten'] / max(1, crops['planted'])) * 100 if crops['planted'] > 0 else 0,
            'productivity': agents_data['farmers']['total_score'] + agents_data['guards']['total_score']
        }

        status = {
            'wet_tiles': sum(1 for c in range(grid.cols) for r in range(grid.rows) if grid.tiles[c][r].wet),
            'field_utilization': len(grid.field_tiles()) / (grid.cols * grid.rows) * 100
        }

        return {
            'crops': crops,
            'agents': agents_data,
            'performance': performance,
            'status': status
        }

    def _draw_crop_metrics(self, x, y, width, data, f_normal, f_tiny):
        """Draw crop-related metrics"""
        lines = [
            f"Planted: {data['planted']}",
            f"Ready: {data['ready']}",
            f"Value: ${data['harvested_value']}"
        ]

        crop_icons = {CROP_WHEAT: "🌾", CROP_SUNFLOWER: "🌻", CROP_CORN: "🌽"}
        for crop_id, count in data['by_type'].items():
            if count > 0:
                icon = crop_icons.get(crop_id, "❓")
                lines.append(f"{icon} {CROP_NAMES[crop_id]}: {count}")

        for i, line in enumerate(lines):
            color = C_TEXT_SUCCESS if "Ready" in line else C_TEXT_MAIN
            text = f_tiny.render(line, True, color)
            self.screen.blit(text, (x, y + i * 18))

    def _draw_agent_metrics(self, x, y, width, data, f_normal, f_tiny):
        """Draw agent-related metrics"""
        lines = []
        for agent_type, info in data.items():
            if agent_type == 'farmers':
                icon = "🌾"
                color = C_FARMER
            elif agent_type == 'guards':
                icon = "🛡️"
                color = C_GUARD
            else:  # animals
                icon = "🐮"
                color = C_ANIMAL

            count = info['count']
            score = info['total_score']
            lines.append(f"{icon} {agent_type.title()}: {count} (Score: {score})")

            if agent_type == 'animals':
                eaten = info['crops_eaten']
                lines.append(f"   Crops eaten: {eaten}")
            else:
                active = info.get('active', 0)
                lines.append(f"   Active: {active}/{count}")

        for i, line in enumerate(lines):
            text = f_tiny.render(line, True, C_TEXT_MAIN)
            self.screen.blit(text, (x, y + i * 18))

    def _draw_performance_metrics(self, x, y, width, data, f_normal, f_tiny):
        """Draw performance metrics"""
        lines = [
            f"Efficiency: {data['efficiency']:.1f}%",
            f"Protection: {data['protection']:.1f}%",
            f"Productivity: {data['productivity']}"
        ]

        for i, line in enumerate(lines):
            color = C_TEXT_SUCCESS if "Efficiency" in line and data['efficiency'] > 50 else C_TEXT_WARN if "Protection" in line and data['protection'] > 20 else C_TEXT_MAIN
            text = f_tiny.render(line, True, color)
            self.screen.blit(text, (x, y + i * 18))

    def _draw_status_metrics(self, x, y, width, data, f_normal, f_tiny):
        """Draw status metrics"""
        lines = [
            f"Wet tiles: {data['wet_tiles']}",
            f"Field utilization: {data['field_utilization']:.1f}%"
        ]

        for i, line in enumerate(lines):
            text = f_tiny.render(line, True, C_TEXT_DIM)
            self.screen.blit(text, (x, y + i * 18))
