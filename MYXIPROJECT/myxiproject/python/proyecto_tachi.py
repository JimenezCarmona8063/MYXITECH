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
    """Construye un plano escolar con salones y zonas clave."""
    margin = 40
    area_w, area_h = 220, 130
    gap_x, gap_y = 18, 18

    areas: Dict[str, CampusArea] = {}
    grid_positions = [
        ("Biblioteca", 0, 0),
        ("Sala Profesores", 1, 0),
        ("Dirección", 2, 0),
        ("Administración", 3, 0),
        ("Entrada", 0, 1),
        ("Pasillo", 1, 1),
        ("Salón 101", 2, 1),
        ("Salón 102", 3, 1),
        ("Cafetería", 0, 2),
        ("Pasillo Sur", 1, 2),
        ("Salón 201", 2, 2),
        ("Servicios", 3, 2),
    ]

    palette = [
        (217, 233, 255), (222, 247, 234), (255, 241, 214),
        (255, 224, 230), (235, 223, 255), (210, 242, 255),
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

    def go_to(self, location: str, campus: Dict[str, CampusArea]) -> None:
        """Fija un destino directo para el personaje."""
        area = campus.get(location)
        if area is None:
            return
        self.target = area.anchor
        self.wait_timer = 0

    def in_area(self, area: CampusArea) -> bool:
        return area.rect.collidepoint(int(self.position[0]), int(self.position[1]))

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
        self.player: Optional[Character] = None
        self.selected_role: Optional[str] = None
        self.role_selected = False
        self.event_messages: List[Tuple[str, float]] = []
        self.message_duration = 6.0

        self.classmates = [self.characters[name] for name in self.classmate_names]
        self.teacher_character = self.characters[self.teacher_name]
        self.staff_character = self.characters[self.staff_name]

        self._reset_story_state()

    # ------------------------------------------------------------------
    def _create_characters(self) -> Dict[str, Character]:
        campus = build_campus_map()

        def activity(label: str, location: str, duration: int, status: str) -> Activity:
            return Activity(label=label, location=location, duration=duration, status_key=status)

        personajes: Dict[str, Character] = {}

        personajes["Alumno"] = Character(
            name="Alumno",
            role="Alumno",
            color=(246, 229, 141),
            speed=130,
            cycle=[
                activity("Llegar", "Entrada", 4, "Llegó a la escuela"),
                activity("Clase", "Salón 101", 8, "Asistió a clase"),
                activity("Comida", "Cafetería", 5, "Comió"),
                activity("Estudio", "Biblioteca", 6, "Estudió"),
            ],
            position=campus["Entrada"].anchor,
        )

        personajes["Maestro"] = Character(
            name="Maestro",
            role="Maestro",
            color=(94, 109, 217),
            speed=105,
            cycle=[
                activity("Preparación", "Sala Profesores", 5, "Preparó clase"),
                activity("Clase", "Salón 101", 8, "Impartió clase"),
                activity("Reporte", "Dirección", 4, "Entregó reportes"),
                activity("Descanso", "Cafetería", 4, "Tomó descanso"),
            ],
            position=campus["Sala Profesores"].anchor,
        )

        personajes["Funcionario"] = Character(
            name="Funcionario",
            role="Funcionario",
            color=(255, 190, 118),
            speed=95,
            cycle=[
                activity("Apertura", "Administración", 6, "Aperturó salones"),
                activity("Supervisión", "Pasillo", 6, "Supervisó pasillo"),
                activity("Cafetería", "Cafetería", 4, "Revisó cafetería"),
            ],
            position=campus["Administración"].anchor,
        )

        personajes["Carla"] = Character(
            name="Carla",
            role="Alumna",
            color=(39, 174, 96),
            speed=110,
            cycle=[
                activity("Llegar", "Entrada", 4, "Llegó"),
                activity("Clase", "Salón 101", 8, "Asistió"),
                activity("Comida", "Cafetería", 5, "Comió"),
            ],
            position=campus["Entrada"].anchor,
        )

        personajes["Luis"] = Character(
            name="Luis",
            role="Alumno",
            color=(236, 112, 99),
            speed=110,
            cycle=[
                activity("Llegar", "Entrada", 4, "Llegó"),
                activity("Clase", "Salón 101", 8, "Asistió"),
                activity("Recreo", "Pasillo Sur", 5, "Tomó recreo"),
            ],
            position=campus["Entrada"].anchor,
        )

        personajes["Prefecto"] = Character(
            name="Prefecto",
            role="Funcionario",
            color=(155, 89, 182),
            speed=90,
            cycle=[
                activity("Reportes", "Dirección", 6, "Entregó reportes"),
                activity("Ronda", "Pasillo", 6, "Vigiló pasillo"),
                activity("Café", "Cafetería", 4, "Tomó café"),
            ],
            position=campus["Dirección"].anchor,
        )

        for personaje in personajes.values():
            personaje.reset_status()

        self.player_options = {
            "alumno": "Alumno",
            "maestro": "Maestro",
            "funcionario": "Funcionario",
        }
        self.classmate_names = ["Carla", "Luis"]
        self.teacher_name = "Maestro"
        self.staff_name = "Funcionario"

        return personajes

    # ------------------------------------------------------------------
    def _reset_story_state(self) -> None:
        self.elapsed_time = 0.0
        self.class_start_time = 12.0
        self.class_in_session = False
        self.teacher_cancelled_class = False
        self.student_entered_class = False
        self.student_reported = False
        self.cafeteria_open = True

    # ------------------------------------------------------------------
    def _push_message(self, text: str) -> None:
        self.event_messages.append((text, self.message_duration))

    def _handle_role_selection_event(self, key: int) -> None:
        mapping = {
            pygame.K_1: ("alumno", "Alumno", "Entrada"),
            pygame.K_2: ("maestro", "Maestro", "Sala Profesores"),
            pygame.K_3: ("funcionario", "Funcionario", "Administración"),
        }
        data = mapping.get(key)
        if data is None:
            return

        role_code, character_key, start_area = data
        character_name = self.player_options[role_code]
        self.player = self.characters[character_name]
        self.selected_role = role_code
        self.role_selected = True
        self._reset_story_state()
        self.event_messages = []

        for personaje in self.characters.values():
            personaje.reset_status()

        area = self.campus[start_area]
        self.player.position = area.anchor
        self.player.target = None
        self.player.wait_timer = 0

        self._push_message(f"Elegiste ser {character_key}. Tus decisiones afectarán a todos.")

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_e:
            self._player_interact()
        elif key == pygame.K_n and self.selected_role == "maestro":
            self._teacher_cancel_class()

    def _handle_story_logic(self, dt: float) -> None:
        self.elapsed_time += dt

        if (
            not self.class_in_session
            and not self.teacher_cancelled_class
            and self.elapsed_time >= self.class_start_time
            and self.selected_role != "maestro"
        ):
            self._start_class(manual=False)

        if self.selected_role == "alumno":
            if (
                not self.student_entered_class
                and not self.student_reported
                and self.elapsed_time >= self.class_start_time + 5
            ):
                self.student_reported = True
                self._push_message("El maestro te puso falta y te reportó en Dirección.")
                if self.teacher_character is not self.player:
                    self.teacher_character.go_to("Dirección", self.campus)

    def _player_interact(self) -> None:
        if self.player is None:
            return
        area = self._current_player_area()
        if area is None:
            return

        if area.name.startswith("Salón"):
            self._push_message(f"Entraste a {area.name}.")

        if self.selected_role == "alumno":
            if area.name == "Salón 101":
                if not self.student_entered_class:
                    self.student_entered_class = True
                    self._push_message("Tomaste tu lugar. El maestro registró tu asistencia.")
            else:
                self._push_message(f"Exploras {area.name} como alumno.")

        elif self.selected_role == "maestro":
            if area.name == "Salón 101":
                if self.teacher_cancelled_class:
                    self._push_message("Reconsideraste. La clase continúa.")
                if not self.class_in_session:
                    self._start_class(manual=True)
                else:
                    self._push_message("La clase ya está en marcha.")
            elif area.name == "Sala Profesores":
                self._push_message("Preparas material y revisas tareas.")

        elif self.selected_role == "funcionario":
            if area.name in {"Administración", "Cafetería"}:
                self.cafeteria_open = not self.cafeteria_open
                if self.cafeteria_open:
                    self._push_message("Abriste la cafetería. El personal y alumnos pueden comer.")
                else:
                    self._push_message("Cerraste la cafetería para inspección. Buscarán otro lugar.")
                    for personaje in self.characters.values():
                        if personaje is self.player:
                            continue
                        activity = personaje.current_activity()
                        if activity and activity.location == "Cafetería":
                            personaje.go_to("Pasillo Sur", self.campus)
            elif area.name == "Salón 101":
                self._push_message("Autorizaste el Salón 101 y dejaste pasar a los maestros.")

    def _teacher_cancel_class(self) -> None:
        if self.player is None or self.selected_role != "maestro":
            return
        area = self._current_player_area()
        if area is None or area.name != "Salón 101":
            self._push_message("Debes estar dentro del salón para cancelar la clase.")
            return
        if self.teacher_cancelled_class:
            self._push_message("La clase ya fue cancelada.")
            return
        self.teacher_cancelled_class = True
        self.class_in_session = False
        self._dismiss_students_from_class()
        self._push_message("Decidiste no dar clase. Los alumnos abandonan el salón.")

    def _start_class(self, manual: bool) -> None:
        self.class_in_session = True
        self.teacher_cancelled_class = False
        self._send_students_to_class()
        if manual:
            self._push_message("Iniciaste la clase en el Salón 101.")
        elif self.selected_role != "maestro":
            self._push_message("El maestro inició la clase en el Salón 101.")

    def _send_students_to_class(self) -> None:
        for mate in self.classmates:
            mate.go_to("Salón 101", self.campus)
        if self.teacher_character is not self.player:
            self.teacher_character.go_to("Salón 101", self.campus)

    def _dismiss_students_from_class(self) -> None:
        for mate in self.classmates:
            mate.go_to("Cafetería", self.campus)
        if self.teacher_character is not self.player:
            self.teacher_character.go_to("Sala Profesores", self.campus)

    def _update_messages(self, dt: float) -> None:
        if not self.event_messages:
            return
        updated: List[Tuple[str, float]] = []
        for text, timer in self.event_messages:
            timer -= dt
            if timer > 0:
                updated.append((text, timer))
        self.event_messages = updated

    def _current_player_area(self) -> Optional[CampusArea]:
        if self.player is None:
            return None
        return self._area_for_position(self.player.position)

    def _area_for_position(self, position: Tuple[float, float]) -> Optional[CampusArea]:
        px, py = int(position[0]), int(position[1])
        for area in self.campus.values():
            if area.rect.collidepoint(px, py):
                return area
        return None

    # ------------------------------------------------------------------
    def run(self) -> None:
        self.running = True
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif not self.role_selected:
                        self._handle_role_selection_event(event.key)
                    else:
                        self._handle_keydown(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for personaje in self.characters.values():
                        personaje.reset_status()

            if self.role_selected and self.player is not None:
                self._handle_player_input(dt)
                self._handle_story_logic(dt)

            self._update_characters(dt)
            self._update_messages(dt)
            self._draw()

        pygame.quit()

    # ------------------------------------------------------------------
    def _handle_player_input(self, dt: float) -> None:
        if not self.role_selected or self.player is None:
            return
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
            self._enforce_story_constraints(personaje)
            personaje.update(dt, self.campus)

    def _enforce_story_constraints(self, character: Character) -> None:
        if character.name in self.classmate_names:
            if self.teacher_cancelled_class:
                cafeteria = self.campus["Cafetería"]
                if not character.in_area(cafeteria):
                    character.go_to("Cafetería", self.campus)
            elif self.class_in_session:
                classroom = self.campus["Salón 101"]
                if not character.in_area(classroom):
                    character.go_to("Salón 101", self.campus)

        if character is self.teacher_character and character is not self.player:
            if self.class_in_session:
                classroom = self.campus["Salón 101"]
                if not character.in_area(classroom):
                    character.go_to("Salón 101", self.campus)
            elif self.teacher_cancelled_class:
                lounge = self.campus["Sala Profesores"]
                if not character.in_area(lounge):
                    character.go_to("Sala Profesores", self.campus)

        if not self.cafeteria_open:
            activity = character.current_activity()
            if activity and activity.location == "Cafetería":
                character.go_to("Pasillo", self.campus)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill(BACKGROUND_COLOR)
        self._draw_map()
        self._draw_characters()
        self._draw_hover_panel()
        self._draw_messages()
        self._draw_goal_banner()
        if not self.role_selected:
            self._draw_role_menu()
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

    def _draw_messages(self) -> None:
        if not self.event_messages:
            return

        visible = list(self.event_messages)[-3:]
        for index, (text, _) in enumerate(reversed(visible)):
            rect = pygame.Rect(30, HEIGHT - 140 - index * 60, 440, 50)
            pygame.draw.rect(self.screen, (20, 20, 20), rect, border_radius=12)
            pygame.draw.rect(self.screen, (245, 245, 245), rect.inflate(-8, -8), border_radius=12)
            label = self.font_small.render(text, True, (40, 40, 40))
            self.screen.blit(label, (rect.x + 16, rect.y + 16))

    def _draw_role_menu(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 520, 320)
        panel.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(self.screen, (245, 245, 245), panel, border_radius=18)
        pygame.draw.rect(self.screen, (45, 52, 54), panel, 4, border_radius=18)

        title = self.font_large.render("Elige tu rol", True, (40, 40, 40))
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 24))

        options = [
            "1 - Alumno: llega al salón y evita reportes.",
            "2 - Maestro: decide si impartes o cancelas la clase.",
            "3 - Funcionario: administra la cafetería y los accesos.",
            "Presiona la tecla indicada para comenzar.",
        ]
        for idx, line in enumerate(options):
            label = self.font_medium.render(line, True, (60, 60, 60))
            self.screen.blit(label, (panel.x + 32, panel.y + 96 + idx * 44))

    def _draw_goal_banner(self) -> None:
        texto = "Objetivo: Vive un día escolar y decide como alumno, maestro o funcionario"
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
