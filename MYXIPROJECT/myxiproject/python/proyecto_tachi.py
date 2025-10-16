"""Proyecto Tachi - Simulación interactiva de la Universidad de la UP.

Este módulo contiene un pequeño juego/simulación hecho con Pygame
que muestra a diferentes personajes moviéndose dentro del campus.

Controles:
    - Flechas del teclado o WASD: mover al alumno protagonista.
    - Click izquierdo sobre la pantalla: fuerza a todos a continuar
      con su siguiente actividad (útil para reiniciar ciclos).
    - Coloca el cursor sobre un personaje para mostrar su panel de control.

Requisitos:
    pip install pygame

Ejecución:
    python python/proyecto_tachi.py
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame

# ---------------------------------------------------------------------------
# Configuración general
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 1180, 720
BACKGROUND_COLOR = (228, 233, 244)
FPS = 60
FONT_NAME = "freesansbold.ttf"

# ---------------------------------------------------------------------------
# Definición de lugares del campus
# ---------------------------------------------------------------------------
@dataclass
class CampusArea:
    name: str
    rect: pygame.Rect
    color: Tuple[int, int, int]
    anchor: Tuple[int, int]


def build_campus_map() -> Dict[str, CampusArea]:
    """Construye el mapa de la universidad con zonas rectangulares."""
    margin = 40
    area_w, area_h = 200, 120
    gap_x, gap_y = 20, 20

    areas: Dict[str, CampusArea] = {}
    grid_positions = [
        ("Entrada", 0, 0),
        ("Fundadores", 1, 0),
        ("Biblioteca", 2, 0),
        ("Smart Center", 0, 1),
        ("Ingenierías", 1, 1),
        ("Civil", 2, 1),
        ("TI", 3, 1),
        ("Starbucks", 0, 2),
        ("Caffenio", 1, 2),
        ("Cafetería", 2, 2),
        ("Oxxo", 3, 2),
        ("Capilla", 0, 3),
        ("Posgrados", 1, 3),
        ("Gym", 2, 3),
        ("Canchas", 3, 3),
        ("Música", 0, 4),
        ("Biblio", 1, 4),
        ("Starbucks 2", 2, 4),
        ("Oxxo 2", 3, 4),
    ]

    palette = [
        (204, 229, 255), (204, 255, 229), (255, 229, 204),
        (255, 204, 229), (229, 204, 255), (204, 255, 255),
    ]

    for index, (name, gx, gy) in enumerate(grid_positions):
        x = margin + gx * (area_w + gap_x)
        y = margin + gy * (area_h + gap_y)
        rect = pygame.Rect(x, y, area_w, area_h)
        anchor = (rect.centerx, rect.centery)
        color = palette[index % len(palette)]
        areas[name] = CampusArea(name=name, rect=rect, color=color, anchor=anchor)

    return areas


# ---------------------------------------------------------------------------
# Personajes y actividades
# ---------------------------------------------------------------------------
@dataclass
class Activity:
    label: str
    location: str
    duration: int  # en segundos simulados
    status_key: str


@dataclass
class Character:
    name: str
    role: str
    color: Tuple[int, int, int]
    speed: float
    cycle: List[Activity]
    position: Tuple[float, float]
    radius: int = 18
    status: Dict[str, bool] = field(default_factory=dict)
    current_index: int = 0
    wait_timer: float = 0.0
    target: Optional[Tuple[float, float]] = None

    def reset_status(self) -> None:
        for key in {activity.status_key for activity in self.cycle}:
            self.status[key] = False
        self.current_index = 0
        self.wait_timer = 0
        self.target = None

    def current_activity(self) -> Optional[Activity]:
        if not self.cycle:
            return None
        return self.cycle[self.current_index % len(self.cycle)]

    def advance_activity(self, campus: Dict[str, CampusArea]) -> None:
        activity = self.current_activity()
        if not activity:
            return
        area = campus[activity.location]
        self.target = area.anchor
        if activity.status_key not in self.status:
            self.status[activity.status_key] = False

    def update(self, dt: float, campus: Dict[str, CampusArea]) -> None:
        if not self.cycle:
            return

        activity = self.current_activity()
        if activity is None:
            return

        # Si no hay objetivo asignado, apuntar al lugar correspondiente
        if self.target is None:
            self.advance_activity(campus)

        if self.target is not None:
            self._move_towards_target(dt)

        # ¿Llegó al destino?
        if self.target is not None and self._distance_to_target() <= self.speed * dt:
            self.position = self.target
            self.target = None
            self.wait_timer += dt
            if self.wait_timer >= activity.duration:
                self.status[activity.status_key] = True
                self.current_index = (self.current_index + 1) % len(self.cycle)
                self.wait_timer = 0

    # ------------------------------------------------------------------
    def _move_towards_target(self, dt: float) -> None:
        if self.target is None:
            return
        x, y = self.position
        tx, ty = self.target
        dx = tx - x
        dy = ty - y
        distance = math.hypot(dx, dy)
        if distance == 0:
            return
        step = min(self.speed * dt, distance)
        self.position = (x + dx / distance * step, y + dy / distance * step)

    def _distance_to_target(self) -> float:
        if self.target is None:
            return float("inf")
        x, y = self.position
        tx, ty = self.target
        return math.hypot(tx - x, ty - y)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.circle(surface, self.color, tuple(map(int, self.position)), self.radius)
        label = font.render(self.name, True, (30, 30, 30))
        surface.blit(label, (self.position[0] - label.get_width() / 2, self.position[1] - self.radius - 20))

    def is_hovered(self, mouse_pos: Tuple[int, int]) -> bool:
        return math.hypot(self.position[0] - mouse_pos[0], self.position[1] - mouse_pos[1]) <= self.radius


# ---------------------------------------------------------------------------
# Juego principal
# ---------------------------------------------------------------------------
class ProyectoTachiGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Proyecto Tachi - Vida en la UP")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.Font(FONT_NAME, 14)
        self.font_medium = pygame.font.Font(FONT_NAME, 18)
        self.font_large = pygame.font.Font(FONT_NAME, 24)

        self.campus = build_campus_map()
        self.characters = self._create_characters()
        self.player = self.characters["Alumno"]

    # ------------------------------------------------------------------
    def _create_characters(self) -> Dict[str, Character]:
        campus = build_campus_map()

        def activity(label: str, location: str, duration: int, status: str) -> Activity:
            return Activity(label=label, location=location, duration=duration, status_key=status)

        personajes: Dict[str, Character] = {}
        personajes["Rector"] = Character(
            name="Antonio",
            role="Rector",
            color=(200, 70, 70),
            speed=90,
            cycle=[
                activity("Recorrido", "Entrada", 6, "Recorrido completado"),
                activity("Revisión", "Ingenierías", 8, "Ingenierías revisadas"),
                activity("Reunión", "Posgrados", 6, "Atendió reuniones"),
                activity("Café", "Starbucks", 4, "Tomó café"),
            ],
            position=campus["Entrada"].anchor,
        )

        maestros = {
            "Dávalos": [
                activity("Clase", "Ingenierías", 8, "Ya dio clase"),
                activity("Asesoría", "Smart Center", 5, "Dio asesorías"),
                activity("Comida", "Cafetería", 4, "Comió"),
            ],
            "Tachiquín": [
                activity("Clase", "TI", 8, "Ya dio clase"),
                activity("Descanso", "Starbucks", 5, "Descansó"),
                activity("Tarea", "Biblioteca", 6, "Preparó clases"),
            ],
            "Martha": [
                activity("Clase", "Civil", 7, "Ya dio clase"),
                activity("Comida", "Caffenio", 4, "Comió"),
                activity("Asesoría", "Smart Center", 5, "Dio asesorías"),
            ],
            "Isaac": [
                activity("Clase", "Smart Center", 7, "Ya dio clase"),
                activity("Ejercicio", "Gym", 5, "Hizo ejercicio"),
                activity("Descanso", "Cafetería", 4, "Descansó"),
            ],
            "Fabiola": [
                activity("Clase", "Fundadores", 6, "Ya dio clase"),
                activity("Comida", "Cafetería", 4, "Comió"),
                activity("Exámenes", "Biblioteca", 5, "Calificó exámenes"),
            ],
        }

        base_colors = [(72, 126, 176), (94, 109, 217), (39, 174, 96), (236, 112, 99), (155, 89, 182)]
        for index, (nombre, ciclo) in enumerate(maestros.items()):
            personajes[nombre] = Character(
                name=nombre,
                role="Maestro",
                color=base_colors[index % len(base_colors)],
                speed=80,
                cycle=ciclo,
                position=campus["Fundadores"].anchor,
            )

        personajes["Alumno"] = Character(
            name="Alumno",
            role="Alumno",
            color=(246, 229, 141),
            speed=130,
            cycle=[
                activity("Clase", "Ingenierías", 6, "Fue a clases"),
                activity("Comida", "Cafetería", 4, "Comió"),
                activity("Estudio", "Biblioteca", 5, "Estudió"),
                activity("Deporte", "Canchas", 6, "Hizo deporte"),
                activity("Música", "Música", 4, "Practicó música"),
            ],
            position=campus["Cafetería"].anchor,
        )

        personajes["Contador"] = Character(
            name="Contador",
            role="Empleado",
            color=(232, 126, 4),
            speed=75,
            cycle=[
                activity("Cuentas", "Smart Center", 6, "Atendió cuentas"),
                activity("Comida", "Cafetería", 4, "Comió"),
                activity("Proveedores", "Oxxo", 5, "Revisó proveedores"),
            ],
            position=campus["Smart Center"].anchor,
        )

        personajes["Oxxo"] = Character(
            name="Oxxo",
            role="Empleado Oxxo",
            color=(255, 190, 118),
            speed=70,
            cycle=[
                activity("Venta", "Oxxo", 8, "Vendió"),
                activity("Descanso", "Cafetería", 3, "Descansó"),
                activity("Inventario", "Oxxo 2", 5, "Organizó inventario"),
            ],
            position=campus["Oxxo"].anchor,
        )

        personajes["Café"] = Character(
            name="Barista",
            role="Caffenio",
            color=(210, 180, 140),
            speed=70,
            cycle=[
                activity("Venta", "Caffenio", 8, "Vendió"),
                activity("Descanso", "Starbucks 2", 4, "Descansó"),
            ],
            position=campus["Caffenio"].anchor,
        )

        for personaje in personajes.values():
            personaje.reset_status()
        return personajes

    # ------------------------------------------------------------------
    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for personaje in self.characters.values():
                        personaje.reset_status()

            self._handle_player_input(dt)
            self._update_characters(dt)
            self._draw()

        pygame.quit()

    # ------------------------------------------------------------------
    def _handle_player_input(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        if dx or dy:
            length = math.hypot(dx, dy)
            if length:
                dx /= length
                dy /= length
            px, py = self.player.position
            self.player.position = (px + dx * self.player.speed * dt, py + dy * self.player.speed * dt)

            # Mantener al jugador dentro del mapa principal
            px, py = self.player.position
            px = max(20, min(WIDTH - 20, px))
            py = max(20, min(HEIGHT - 20, py))
            self.player.position = (px, py)

    # ------------------------------------------------------------------
    def _update_characters(self, dt: float) -> None:
        for personaje in self.characters.values():
            if personaje is self.player:
                continue
            personaje.update(dt, self.campus)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill(BACKGROUND_COLOR)
        self._draw_map()
        self._draw_characters()
        self._draw_hover_panel()
        self._draw_goal_banner()
        pygame.display.flip()

    def _draw_map(self) -> None:
        for area in self.campus.values():
            pygame.draw.rect(self.screen, area.color, area.rect, border_radius=12)
            pygame.draw.rect(self.screen, (160, 160, 160), area.rect, 2, border_radius=12)
            label = self.font_small.render(area.name, True, (40, 40, 40))
            self.screen.blit(label, (area.rect.x + 8, area.rect.y + 8))

    def _draw_characters(self) -> None:
        for personaje in self.characters.values():
            personaje.draw(self.screen, self.font_small)

    def _draw_hover_panel(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hovered: Optional[Character] = None
        for personaje in self.characters.values():
            if personaje.is_hovered(mouse_pos):
                hovered = personaje
                break

        if hovered is None:
            return

        panel_width = 300
        panel_height = 26 + 20 * len(hovered.status)
        panel = pygame.Rect(WIDTH - panel_width - 30, 30, panel_width, panel_height)
        pygame.draw.rect(self.screen, (30, 30, 30), panel, border_radius=10)
        pygame.draw.rect(self.screen, (240, 240, 240), panel.inflate(-6, -6), border_radius=10)

        title = self.font_medium.render(f"{hovered.name} ({hovered.role})", True, (20, 20, 20))
        self.screen.blit(title, (panel.x + 20, panel.y + 12))

        for idx, (status, completed) in enumerate(sorted(hovered.status.items())):
            color = (46, 204, 113) if completed else (231, 76, 60)
            text = self.font_small.render(f"{status}: {'✔' if completed else '…'}", True, color)
            self.screen.blit(text, (panel.x + 24, panel.y + 44 + idx * 20))

    def _draw_goal_banner(self) -> None:
        texto = "Objetivo: Mantener la UP estable - clases, ventas y bienestar al día"
        banner = pygame.Rect(0, HEIGHT - 40, WIDTH, 40)
        pygame.draw.rect(self.screen, (52, 73, 94), banner)
        label = self.font_medium.render(texto, True, (255, 255, 255))
        self.screen.blit(label, (banner.centerx - label.get_width() // 2, banner.centery - label.get_height() // 2))


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------
def main() -> None:
    game = ProyectoTachiGame()
    game.run()


if __name__ == "__main__":
    main()
