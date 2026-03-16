#!/usr/bin/env python3
"""
Pip-Boy Octopus Edition
Una interfaz estilo Fallout con Otto el pulpo cibernético
"""

import pygame
import math
import random
import time
import sys

from core import (
    SystemStats, NetworkInfo, SystemInfo, 
    LogManager, OctopusAnimator, Navigation, HelpSystem
)

# Inicializar pygame
pygame.init()

# Detectar resolución
info = pygame.display.Info()
WIDTH = info.current_w if info.current_w > 0 else 1366
HEIGHT = info.current_h if info.current_h > 0 else 768

print(f"Pip-Boy Octopus Edition - {WIDTH}x{HEIGHT}")

# Colores Pip-Boy
COLOR_BG = (10, 15, 10)
COLOR_PRIMARY = (30, 255, 30)
COLOR_DIM = (15, 120, 15)
COLOR_ACCENT = (50, 200, 50)
COLOR_SCANLINE = (0, 40, 0)
COLOR_BRIGHT = (100, 255, 100)
COLOR_SHADOW = (8, 25, 8)
COLOR_GLOW = (40, 180, 40)

# Pantalla completa
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Pip-Boy 3000 - Octopus Edition")

# Fuentes
def get_font(size):
    try:
        return pygame.font.Font("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", size)
    except:
        return pygame.font.SysFont("monospace", size)

font_large = get_font(int(HEIGHT * 0.055))
font_medium = get_font(int(HEIGHT * 0.037))
font_small = get_font(int(HEIGHT * 0.028))
font_tiny = get_font(int(HEIGHT * 0.022))

clock = pygame.time.Clock()

# Instancias
system_stats = SystemStats()
log_manager = LogManager()
octopus_animator = OctopusAnimator()
navigation = Navigation()

show_help_overlay = False


def draw_scanlines(surface):
    for y in range(0, HEIGHT, 3):
        pygame.draw.line(surface, COLOR_SCANLINE, (0, y), (WIDTH, y))


def draw_text(text, font, color, x, y, center=False):
    text_surface = font.render(text, True, color)
    if center:
        rect = text_surface.get_rect(center=(x, y))
        screen.blit(text_surface, rect)
    else:
        screen.blit(text_surface, (x, y))


def draw_bar(x, y, width, height, value, max_value=100, label=""):
    pygame.draw.rect(screen, COLOR_DIM, (x, y, width, height), 1)
    fill_width = int((value / max_value) * (width - 4))
    pygame.draw.rect(screen, COLOR_PRIMARY, (x + 2, y + 2, fill_width, height - 4))
    if label:
        draw_text(label, font_tiny, COLOR_ACCENT, x, y - 18)
    draw_text(f"{value:.1f}%", font_tiny, COLOR_PRIMARY, x + width + 10, y + 2)


def draw_octopus(cx, cy, size=100, t=0):
    """
    Otto - Pulpo feliz estilo emoji 🐙
    Simple, limpio y reconocible
    """
    
    # === CABEZA GRANDE (50% más grande) ===
    head_w = size * 1.10
    head_h = size * 0.90
    head_y = cy - size * 0.10
    
    # Sombra
    pygame.draw.ellipse(screen, COLOR_SHADOW,
                       (cx - head_w/2 + 4, head_y - head_h/2 + 4, head_w, head_h))
    
    # Cabeza
    pygame.draw.ellipse(screen, COLOR_DIM,
                       (cx - head_w/2, head_y - head_h/2, head_w, head_h))
    
    # Brillo
    pygame.draw.ellipse(screen, COLOR_GLOW,
                       (cx - head_w * 0.30, head_y - head_h * 0.35,
                        head_w * 0.55, head_h * 0.35))
    pygame.draw.ellipse(screen, COLOR_BRIGHT,
                       (cx - head_w * 0.15, head_y - head_h * 0.40,
                        head_w * 0.28, head_h * 0.18))
    
    # Contorno
    pygame.draw.ellipse(screen, COLOR_PRIMARY,
                       (cx - head_w/2, head_y - head_h/2, head_w, head_h), 4)
    
    # === TENTÁCULOS (5 cortos y gordos) ===
    tentacles = [
        (-0.30, -0.7, 0.35),  # izq ext
        (-0.08, -0.2, 0.42),  # izq
        ( 0.08,  0.2, 0.42),  # der
        ( 0.30,  0.7, 0.35),  # der ext
    ]
    
    for i, (x_off, curve, length) in enumerate(tentacles):
        ox = cx + x_off * head_w
        oy = head_y + head_h * 0.38
        tent_len = size * length
        
        # Puntos del tentáculo
        num_pts = 10
        left_pts = []
        right_pts = []
        base_thick = size * 0.07
        
        for j in range(num_pts):
            p = j / (num_pts - 1)
            
            # Curva natural
            curve_amt = math.sin(p * math.pi * 0.8) * size * 0.10 * curve
            
            # Ondulación (más movimiento)
            wave = math.sin(t * 1.2 + p * 3.0 + i * 0.7) * size * 0.06 * p
            
            # Centro
            mx = ox + curve_amt + wave
            my = oy + p * tent_len
            
            # Grosor
            thick = base_thick * (1 - p * 0.45)
            
            left_pts.append((mx - thick, my))
            right_pts.append((mx + thick, my))
        
        # Polígono
        right_pts.reverse()
        polygon = left_pts + right_pts
        
        # Sombra
        shadow = [(p[0] + 3, p[1] + 3) for p in polygon]
        pygame.draw.polygon(screen, COLOR_SHADOW, shadow)
        
        # Cuerpo
        pygame.draw.polygon(screen, COLOR_DIM, polygon)
        pygame.draw.polygon(screen, COLOR_PRIMARY, polygon, 2)
        
        # Punta
        tip_x = (left_pts[-1][0] + right_pts[-1][0]) / 2
        tip_y = left_pts[-1][1]
        tip_r = base_thick * 0.30
        pygame.draw.circle(screen, COLOR_DIM, (int(tip_x), int(tip_y)), int(tip_r))
        pygame.draw.circle(screen, COLOR_PRIMARY, (int(tip_x), int(tip_y)), int(tip_r), 2)
        
        # Ventosas
        for v in [2, 4, 6]:
            if v < len(left_pts):
                vx = (left_pts[v][0] + right_pts[-(v+1)][0]) / 2
                vy = left_pts[v][1]
                vr = base_thick * 0.18 * (1 - v/num_pts * 0.4)
                pygame.draw.circle(screen, COLOR_ACCENT, (int(vx), int(vy)), int(max(2, vr)))
    
    # === OJOS GRANDES ===
    eye_spacing = head_w * 0.25
    eye_r = head_w * 0.14
    
    blink = octopus_animator.get_eye_state(t) == "closed"
    
    for side in [-1, 1]:
        ex = cx + side * eye_spacing
        ey = head_y - head_h * 0.08
        
        if blink:
            pygame.draw.arc(screen, COLOR_PRIMARY,
                          (ex - eye_r, ey - eye_r * 0.35, eye_r * 2, eye_r * 0.7),
                          0, math.pi, 3)
        else:
            pygame.draw.circle(screen, COLOR_SHADOW, (int(ex + 2), int(ey + 2)), int(eye_r))
            pygame.draw.circle(screen, (20, 55, 20), (int(ex), int(ey)), int(eye_r))
            
            # Pupila móvil
            px = ex + math.sin(t * 1.2 + side * 1.5) * eye_r * 0.15
            py = ey + math.cos(t * 0.8 + side) * eye_r * 0.08
            
            pygame.draw.circle(screen, COLOR_ACCENT, (int(px), int(py)), int(eye_r * 0.55))
            pygame.draw.circle(screen, (5, 15, 5), (int(px), int(py)), int(eye_r * 0.28))
            
            # Brillos
            pygame.draw.circle(screen, COLOR_BRIGHT,
                             (int(ex - eye_r * 0.25), int(ey - eye_r * 0.25)), int(eye_r * 0.20))
            pygame.draw.circle(screen, COLOR_BRIGHT,
                             (int(ex + eye_r * 0.12), int(ey + eye_r * 0.12)), int(eye_r * 0.08))
            
            pygame.draw.circle(screen, COLOR_PRIMARY, (int(ex), int(ey)), int(eye_r), 3)
    
    # === CEJAS MUY FELICES (arqueadas hacia arriba) ===
    for side in [-1, 1]:
        bx = cx + side * eye_spacing
        by = head_y - head_h * 0.35
        pygame.draw.arc(screen, COLOR_PRIMARY,
                       (bx - eye_r * 1.2, by - eye_r * 0.5, eye_r * 2.4, eye_r * 0.8),
                       0.05 * math.pi, 0.95 * math.pi, 5)
    
    # === BOCA CON GRAN SONRISA ===
    mouth_y = head_y + head_h * 0.18
    mouth_w = head_w * 0.40  # Más ancha
    mouth_h = head_w * 0.28  # Más alta
    pygame.draw.arc(screen, COLOR_PRIMARY,
                   (cx - mouth_w/2, mouth_y - mouth_h * 0.4, mouth_w, mouth_h),
                   0.08 * math.pi, 0.92 * math.pi, 4)  # Sonrisa más grande
    
    # === MEJILLAS ===
    for side in [-1, 1]:
        cheek_x = cx + side * head_w * 0.34
        cheek_y = head_y + head_h * 0.10
        pygame.draw.circle(screen, COLOR_GLOW, (int(cheek_x), int(cheek_y)), int(head_w * 0.055))


def draw_header():
    from datetime import datetime
    pygame.draw.line(screen, COLOR_PRIMARY, (20, 20), (WIDTH - 20, 20), 2)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    current_date = datetime.now().strftime("%Y-%m-%d")
    draw_text(f"{current_date}  {current_time}", font_medium, COLOR_PRIMARY, 30, 35)
    draw_text("PIP-BOY 3000", font_large, COLOR_PRIMARY, WIDTH // 2, 35, center=True)
    draw_text("OCTOPUS EDITION", font_small, COLOR_ACCENT, WIDTH // 2, 60, center=True)
    
    tab_y = 90
    tab_width = int(WIDTH / len(navigation.SECTIONS) * 0.8)
    start_x = (WIDTH - len(navigation.SECTIONS) * tab_width) // 2
    
    for i, section in enumerate(navigation.SECTIONS):
        x = start_x + i * tab_width
        is_selected = i == navigation.current_index
        
        if is_selected:
            pygame.draw.rect(screen, COLOR_DIM, (x, tab_y, tab_width - 5, 30), 0)
        
        color = COLOR_PRIMARY if is_selected else COLOR_DIM
        pygame.draw.rect(screen, color, (x, tab_y, tab_width - 5, 30), 2)
        draw_text(section, font_small, color, x + tab_width//2 - 25, tab_y + 5)
    
    pygame.draw.line(screen, COLOR_PRIMARY, (20, 130), (WIDTH - 20, 130), 1)


def draw_footer():
    pygame.draw.line(screen, COLOR_PRIMARY, (20, HEIGHT - 40), (WIDTH - 20, HEIGHT - 40), 1)
    draw_text("[TAB/ARROWS] Navigate  [ESC] Exit  [H] Help  [1-6] Jump", font_tiny, COLOR_DIM, WIDTH // 2, HEIGHT - 28, center=True)


def draw_help_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((10, 15, 10, 240))
    screen.blit(overlay, (0, 0))
    
    box_w = int(WIDTH * 0.7)
    box_h = int(HEIGHT * 0.75)
    box_x = (WIDTH - box_w) // 2
    box_y = (HEIGHT - box_h) // 2
    
    pygame.draw.rect(screen, COLOR_DIM, (box_x, box_y, box_w, box_h), 0, border_radius=10)
    pygame.draw.rect(screen, COLOR_PRIMARY, (box_x, box_y, box_w, box_h), 3, border_radius=10)
    
    draw_text(">>> AYUDA - PIP-BOY 3000 <<<", font_large, COLOR_BRIGHT, WIDTH // 2, box_y + 30, center=True)
    
    y = box_y + 80
    draw_text("CONTROLES:", font_medium, COLOR_PRIMARY, box_x + 30, y)
    y += 35
    
    for key, desc in HelpSystem.CONTROLS:
        draw_text(f"  {key:20} {desc}", font_small, COLOR_ACCENT, box_x + 30, y)
        y += 26
    
    y += 20
    draw_text("SECCIONES:", font_medium, COLOR_PRIMARY, box_x + 30, y)
    y += 35
    
    for section, desc in HelpSystem.SECTIONS_INFO.items():
        section_num = navigation.SECTIONS.index(section) + 1
        draw_text(f"  [{section_num}] {section:10} - {desc}", font_small, COLOR_ACCENT, box_x + 30, y)
        y += 26
    
    y += 30
    draw_text("PRESIONA [H] O [ESC] PARA CERRAR", font_medium, COLOR_BRIGHT, WIDTH // 2, y, center=True)


def draw_stats_section():
    y_start = 160
    x_left = 50
    x_right = int(WIDTH * 0.55)
    
    system_stats.update()
    
    draw_text("SYSTEM STATUS", font_medium, COLOR_PRIMARY, x_left, y_start)
    
    y = y_start + 45
    bar_width = int(WIDTH * 0.25)
    bar_height = 22
    
    draw_bar(x_left, y, bar_width, bar_height, system_stats.cpu, label="CPU")
    y += 55
    draw_bar(x_left, y, bar_width, bar_height, system_stats.memory, label="MEMORY")
    y += 55
    draw_bar(x_left, y, bar_width, bar_height, system_stats.disk, label="DISK")
    y += 55
    
    if system_stats.temp > 0:
        draw_bar(x_left, y, bar_width, bar_height, system_stats.temp, max_value=100, label="TEMP")
    
    draw_text(f"UPTIME: {system_stats.uptime_formatted}", font_small, COLOR_ACCENT, x_left, y + 70)
    draw_text("UNIT: OTTO-v1.0", font_small, COLOR_PRIMARY, x_right, y_start)
    # Pulpo más grande en stats
    draw_octopus(x_right + int(WIDTH * 0.18), y_start + int(HEIGHT * 0.35), 250, time.time())


def draw_system_section():
    y_start = 160
    x_left = 50
    
    draw_text("SYSTEM INFORMATION", font_medium, COLOR_PRIMARY, x_left, y_start)
    
    y = y_start + 40
    line_height = 30
    
    info = [
        f"HOSTNAME: {NetworkInfo.get_hostname()}",
        f"OS: Linux (Ubuntu)",
        f"KERNEL: {SystemInfo.get_kernel()}",
        f"ARCH: {SystemInfo.get_arch()}",
        f"CPU CORES: {SystemInfo.get_cpu_count()}",
        f"TOTAL RAM: {SystemInfo.get_total_ram():.1f} GB",
        f"DISK SIZE: {SystemInfo.get_total_disk():.1f} GB",
        "",
        f"PYTHON: {SystemInfo.get_python_version()}",
        f"PYGAME: {pygame.version.ver}",
    ]
    
    for line in info:
        draw_text(line, font_small, COLOR_ACCENT, x_left, y)
        y += line_height
    
    draw_text("SYSTEM DIAGRAM", font_medium, COLOR_PRIMARY, int(WIDTH * 0.6), y_start)
    
    system_stats.update()
    
    diag_x = int(WIDTH * 0.55)
    box_w = int(WIDTH * 0.25)
    box_h = 55
    
    pygame.draw.rect(screen, COLOR_PRIMARY, (diag_x, y_start + 40, box_w, box_h), 2)
    draw_text("CPU", font_small, COLOR_PRIMARY, diag_x + box_w//2, y_start + 50, center=True)
    draw_text(f"{system_stats.cpu:.0f}%", font_tiny, COLOR_ACCENT, diag_x + box_w//2, y_start + 72, center=True)
    
    pygame.draw.rect(screen, COLOR_PRIMARY, (diag_x, y_start + 105, box_w, box_h), 2)
    draw_text("MEMORY", font_small, COLOR_PRIMARY, diag_x + box_w//2, y_start + 115, center=True)
    draw_text(f"{system_stats.memory:.0f}%", font_tiny, COLOR_ACCENT, diag_x + box_w//2, y_start + 137, center=True)
    
    pygame.draw.rect(screen, COLOR_PRIMARY, (diag_x, y_start + 170, box_w, box_h), 2)
    draw_text("STORAGE", font_small, COLOR_PRIMARY, diag_x + box_w//2, y_start + 180, center=True)
    draw_text(f"{system_stats.disk:.0f}%", font_tiny, COLOR_ACCENT, diag_x + box_w//2, y_start + 202, center=True)


def draw_network_section():
    y_start = 160
    x_left = 50
    
    draw_text("NETWORK STATUS", font_medium, COLOR_PRIMARY, x_left, y_start)
    
    y = y_start + 40
    line_height = 28
    
    draw_text(f"HOSTNAME: {NetworkInfo.get_hostname()}", font_small, COLOR_ACCENT, x_left, y)
    y += line_height
    
    draw_text(f"LOCAL IP: {NetworkInfo.get_local_ip()}", font_small, COLOR_ACCENT, x_left, y)
    y += line_height
    
    traffic = NetworkInfo.get_traffic()
    if traffic:
        y += 10
        draw_text("TRAFFIC:", font_small, COLOR_PRIMARY, x_left, y)
        y += line_height
        draw_text(f"  SENT: {traffic['sent_mb']:.1f} MB", font_small, COLOR_ACCENT, x_left, y)
        y += line_height
        draw_text(f"  RECV: {traffic['recv_mb']:.1f} MB", font_small, COLOR_ACCENT, x_left, y)
        y += line_height * 2
    
    interfaces = NetworkInfo.get_interfaces()
    if interfaces:
        draw_text("INTERFACES:", font_small, COLOR_PRIMARY, x_left, y)
        y += line_height
        for iface, addr in list(interfaces.items())[:5]:
            draw_text(f"  {iface}: {addr}", font_tiny, COLOR_DIM, x_left, y)
            y += 22
    
    draw_text("NETWORK MAP", font_medium, COLOR_PRIMARY, int(WIDTH * 0.6), y_start)
    
    center_x, center_y = int(WIDTH * 0.7), int(HEIGHT * 0.45)
    pygame.draw.circle(screen, COLOR_PRIMARY, (center_x, center_y), 35, 2)
    draw_text("OTTO", font_tiny, COLOR_PRIMARY, center_x, center_y - 5, center=True)
    
    nodes = [("ROUTER", 130, -80), ("GATEWAY", 160, 50), ("WAN", 80, 150)]
    
    for name, dx, dy in nodes:
        nx = center_x + dx
        ny = center_y + dy
        pygame.draw.line(screen, COLOR_DIM, (center_x, center_y), (nx, ny), 1)
        pygame.draw.circle(screen, COLOR_ACCENT, (nx, ny), 22, 1)
        draw_text(name, font_tiny, COLOR_DIM, nx, ny - 5, center=True)


def draw_otto_section():
    draw_octopus(WIDTH // 2, int(HEIGHT * 0.45), min(180, HEIGHT * 0.3), time.time())
    draw_text("OTTO-v1.0", font_large, COLOR_PRIMARY, WIDTH // 2, HEIGHT - 120, center=True)
    draw_text("Cybernetic Octopus Assistant", font_small, COLOR_ACCENT, WIDTH // 2, HEIGHT - 80, center=True)
    
    system_stats.update()
    
    stats_y = 170
    draw_text("OTTO STATUS", font_medium, COLOR_PRIMARY, 50, stats_y)
    
    y = stats_y + 40
    bar_w = int(WIDTH * 0.18)
    draw_bar(50, y, bar_w, 18, 100 - system_stats.cpu, label="ENERGY")
    y += 50
    draw_bar(50, y, bar_w, 18, 100 - system_stats.memory, label="MEMORY BANK")
    y += 50
    draw_bar(50, y, bar_w, 18, random.randint(85, 100), label="MOOD")


def draw_logs_section():
    y_start = 160
    draw_text("SYSTEM LOG", font_medium, COLOR_PRIMARY, 50, y_start)
    
    y = y_start + 35
    for log in log_manager.get_recent(18):
        draw_text(log, font_tiny, COLOR_DIM, 50, y)
        y += 20
    
    draw_text("Press [L] to add test log", font_tiny, COLOR_ACCENT, 50, HEIGHT - 55)


def draw_help_section():
    y_start = 160
    draw_text("CONTROLS & HELP", font_medium, COLOR_PRIMARY, 50, y_start)
    
    y = y_start + 40
    draw_text("KEYBOARD CONTROLS:", font_small, COLOR_BRIGHT, 50, y)
    y += 30
    
    for key, desc in HelpSystem.CONTROLS:
        draw_text(f"  {key:20} - {desc}", font_small, COLOR_ACCENT, 50, y)
        y += 25
    
    y += 20
    draw_text("SECTIONS:", font_small, COLOR_BRIGHT, 50, y)
    y += 30
    
    for section, desc in HelpSystem.SECTIONS_INFO.items():
        num = navigation.SECTIONS.index(section) + 1
        draw_text(f"  [{num}] {section:10} - {desc}", font_small, COLOR_ACCENT, 50, y)
        y += 25
    
    draw_octopus(WIDTH - 150, int(HEIGHT * 0.5), 80, time.time())


def main():
    global show_help_overlay
    
    running = True
    log_manager.add("Pip-Boy Octopus Edition iniciado")
    log_manager.add("Sistema listo")
    log_manager.add(f"Resolución: {WIDTH}x{HEIGHT}")
    
    last_time = time.time()
    
    while running:
        dt = time.time() - last_time
        last_time = time.time()
        
        octopus_animator.update(dt)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.KEYDOWN:
                if show_help_overlay:
                    if event.key in [pygame.K_h, pygame.K_ESCAPE]:
                        show_help_overlay = False
                    continue
                
                if event.key == pygame.K_ESCAPE:
                    running = False
                
                elif event.key == pygame.K_TAB:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        navigation.previous()
                    else:
                        navigation.next()
                    log_manager.add(f"Navegando a: {navigation.current}")
                
                elif event.key == pygame.K_LEFT:
                    navigation.previous()
                
                elif event.key == pygame.K_RIGHT:
                    navigation.next()
                
                elif event.key == pygame.K_h:
                    show_help_overlay = True
                
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6]:
                    idx = event.key - pygame.K_1
                    if idx < len(navigation.SECTIONS):
                        navigation.goto(idx)
                
                elif event.key == pygame.K_l:
                    log_manager.add(f"Test log entry #{len(log_manager.entries) + 1}")
        
        screen.fill(COLOR_BG)
        
        draw_header()
        
        section = navigation.current
        if section == "STATS":
            draw_stats_section()
        elif section == "SYSTEM":
            draw_system_section()
        elif section == "NETWORK":
            draw_network_section()
        elif section == "OTTO":
            draw_otto_section()
        elif section == "LOGS":
            draw_logs_section()
        elif section == "HELP":
            draw_help_section()
        
        draw_footer()
        draw_scanlines(screen)
        
        if show_help_overlay:
            draw_help_overlay()
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()
    log_manager.add("Pip-Boy cerrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
