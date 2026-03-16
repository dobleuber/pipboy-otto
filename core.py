#!/usr/bin/env python3
"""
Pip-Boy Core Logic
Lógica del sistema separada de la UI para facilitar testing
"""

import math
import random
import time
import socket
import subprocess
from datetime import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemStats:
    """Clase para manejar estadísticas del sistema"""
    
    def __init__(self):
        self.cpu = 0.0
        self.memory = 0.0
        self.disk = 0.0
        self.temp = 0.0
        self.uptime_seconds = 0
    
    def update(self):
        """Actualizar todas las estadísticas"""
        if not HAS_PSUTIL:
            return False
        
        try:
            self.cpu = psutil.cpu_percent(interval=0.1)
            self.memory = psutil.virtual_memory().percent
            self.disk = psutil.disk_usage('/').percent
            self.uptime_seconds = int(time.time() - psutil.boot_time())
            
            # Temperatura (si está disponible)
            self.temp = self._get_temperature()
            return True
        except Exception:
            return False
    
    def _get_temperature(self):
        """Obtener temperatura del sistema"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        return entries[0].current
        except Exception:
            pass
        return 0.0
    
    @property
    def uptime_formatted(self):
        """Retornar uptime formateado"""
        days = self.uptime_seconds // 86400
        hours = (self.uptime_seconds % 86400) // 3600
        mins = (self.uptime_seconds % 3600) // 60
        return f"{days}d {hours}h {mins}m"
    
    def to_dict(self):
        """Convertir a diccionario"""
        return {
            "cpu": self.cpu,
            "memory": self.memory,
            "disk": self.disk,
            "temp": self.temp,
            "uptime": self.uptime_formatted
        }


class NetworkInfo:
    """Clase para información de red"""
    
    @staticmethod
    def get_hostname():
        """Obtener hostname"""
        try:
            return socket.gethostname()
        except Exception:
            return "unknown"
    
    @staticmethod
    def get_local_ip():
        """Obtener IP local"""
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "N/A"
    
    @staticmethod
    def get_interfaces():
        """Obtener interfaces de red"""
        if not HAS_PSUTIL:
            return {}
        
        try:
            interfaces = {}
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces[iface] = addr.address
            return interfaces
        except Exception:
            return {}
    
    @staticmethod
    def get_traffic():
        """Obtener estadísticas de tráfico"""
        if not HAS_PSUTIL:
            return None
        
        try:
            net_io = psutil.net_io_counters()
            return {
                "sent_mb": net_io.bytes_sent / (1024**2),
                "recv_mb": net_io.bytes_recv / (1024**2)
            }
        except Exception:
            return None


class SystemInfo:
    """Clase para información del sistema"""
    
    @staticmethod
    def get_kernel():
        """Obtener versión del kernel"""
        try:
            return subprocess.getoutput('uname -r').strip()
        except Exception:
            return "unknown"
    
    @staticmethod
    def get_arch():
        """Obtener arquitectura"""
        try:
            return subprocess.getoutput('uname -m').strip()
        except Exception:
            return "unknown"
    
    @staticmethod
    def get_cpu_count():
        """Obtener número de CPUs"""
        if HAS_PSUTIL:
            return psutil.cpu_count()
        return 0
    
    @staticmethod
    def get_total_ram():
        """Obtener RAM total en GB"""
        if HAS_PSUTIL:
            return psutil.virtual_memory().total / (1024**3)
        return 0.0
    
    @staticmethod
    def get_total_disk():
        """Obtener disco total en GB"""
        if HAS_PSUTIL:
            return psutil.disk_usage('/').total / (1024**3)
        return 0.0
    
    @staticmethod
    def get_python_version():
        """Obtener versión de Python"""
        try:
            return subprocess.getoutput('python3 --version').strip()
        except Exception:
            return "unknown"


class LogManager:
    """Clase para manejar logs"""
    
    def __init__(self, max_entries=50):
        self.max_entries = max_entries
        self.entries = []
    
    def add(self, message):
        """Agregar entrada al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.entries.append(f"[{timestamp}] {message}")
        
        if len(self.entries) > self.max_entries:
            self.entries.pop(0)
    
    def get_recent(self, count=15):
        """Obtener entradas recientes"""
        return self.entries[-count:] if self.entries else ["[INIT] Sistema iniciado"]
    
    def clear(self):
        """Limpiar logs"""
        self.entries = []


class OctopusAnimator:
    """Clase para animar a Otto el pulpo"""
    
    def __init__(self):
        self.blink_timer = 0
        self.is_blinking = False
    
    def update(self, dt):
        """Actualizar estado de animación"""
        self.blink_timer += dt
        
        # Parpadeo aleatorio cada ~3-5 segundos
        if self.blink_timer > random.uniform(3, 5):
            self.is_blinking = True
            self.blink_timer = 0
        elif self.blink_timer > 0.15:
            self.is_blinking = False
    
    def get_eye_state(self, time_offset):
        """Obtener estado del ojo (abierto/cerrado)"""
        if self.is_blinking:
            return "closed"
        return "open"
    
    @staticmethod
    def calculate_tentacle_points(center_x, center_y, size, time_offset, tentacle_index, num_segments=12):
        """Calcular puntos de un tentáculo - orientación cabeza arriba, tentáculos abajo"""
        # 8 tentáculos distribuidos en la parte inferior
        # Ángulo base para cada tentáculo (de -85° a -95°, distribuidos horizontalmente)
        spread = 160  # Grados de separación total entre el primero y último
        base_angle = (-90 - spread/2 + (tentacle_index / 7) * spread) * math.pi / 180
        
        points_top = []
        points_bottom = []
        
        base_thickness = size * 0.06
        
        # Movimiento de lado a lado (ondulación suave)
        sway_phase = tentacle_index * 0.4  # Cada tentáculo se mueve con diferente fase
        
        for j in range(num_segments):
            progress = j / (num_segments - 1)  # 0.0 al inicio, 1.0 en la punta
            
            # Longitud del segmento
            length = size * 0.25 + j * (size * 0.10)
            
            # Posición base (hacia abajo)
            base_x = center_x + math.sin(base_angle) * length
            base_y = center_y + size * 0.3 + j * (size * 0.11)
            
            # Movimiento de lado a lado (sway) - aumenta hacia la punta
            sway_amount = progress * size * 0.4
            sway = math.sin(time_offset * 0.7 + sway_phase + progress * 1.5) * sway_amount
            
            # Pequeña ondulación vertical
            wave = math.sin(time_offset * 1.2 + progress * 4 + sway_phase) * progress * size * 0.03
            
            # Posición final
            px = base_x + sway
            py = base_y + wave
            
            # Grosor disminuye hacia la punta
            thickness = base_thickness * (1 - progress * 0.6)
            
            # Perpendicular para grosor (horizontal)
            perp = thickness
            
            points_top.append((px + perp, py))
            points_bottom.append((px - perp, py))
        
        return points_top, points_bottom


class Navigation:
    """Clase para manejar navegación entre secciones"""
    
    SECTIONS = ["STATS", "SYSTEM", "NETWORK", "OTTO", "LOGS", "HELP"]
    
    def __init__(self):
        self.current_index = 0
    
    @property
    def current(self):
        """Sección actual"""
        return self.SECTIONS[self.current_index]
    
    def next(self):
        """Ir a siguiente sección"""
        self.current_index = (self.current_index + 1) % len(self.SECTIONS)
        return self.current
    
    def previous(self):
        """Ir a sección anterior"""
        self.current_index = (self.current_index - 1) % len(self.SECTIONS)
        return self.current
    
    def goto(self, index):
        """Ir a sección específica"""
        if 0 <= index < len(self.SECTIONS):
            self.current_index = index
            return self.current
        return None
    
    def goto_name(self, name):
        """Ir a sección por nombre"""
        if name.upper() in self.SECTIONS:
            self.current_index = self.SECTIONS.index(name.upper())
            return self.current
        return None


class HelpSystem:
    """Sistema de ayuda"""
    
    CONTROLS = [
        ("TAB / →", "Siguiente sección"),
        ("SHIFT+TAB / ←", "Sección anterior"),
        ("1-6", "Saltar a sección"),
        ("ESC", "Salir"),
        ("L", "Agregar log (en LOGS)"),
        ("H", "Mostrar/ocultar ayuda"),
    ]
    
    SECTIONS_INFO = {
        "STATS": "Monitoreo de CPU, RAM, disco y temperatura",
        "SYSTEM": "Información del sistema operativo y hardware",
        "NETWORK": "Estado de red, IPs y tráfico",
        "OTTO": "Tu asistente cibernético animado",
        "LOGS": "Historial de eventos del sistema",
        "HELP": "Esta pantalla de ayuda",
    }
    
    @classmethod
    def get_controls_text(cls):
        """Obtener texto de controles"""
        lines = []
        for key, desc in cls.CONTROLS:
            lines.append(f"  {key:20} {desc}")
        return lines
    
    @classmethod
    def get_sections_help(cls):
        """Obtener ayuda de secciones"""
        lines = []
        for section, desc in cls.SECTIONS_INFO.items():
            lines.append(f"  {section:10} - {desc}")
        return lines
