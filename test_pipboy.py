#!/usr/bin/env python3
"""
Tests unitarios para Pip-Boy Octopus
Ejecutar con: pytest test_pipboy.py -v
"""

import pytest
import time
from unittest.mock import patch, MagicMock

# Importar módulos a testear
from core import (
    SystemStats,
    NetworkInfo,
    SystemInfo,
    LogManager,
    OctopusAnimator,
    Navigation,
    HelpSystem
)


class TestSystemStats:
    """Tests para SystemStats"""
    
    def test_initial_values(self):
        """Verificar valores iniciales"""
        stats = SystemStats()
        assert stats.cpu == 0.0
        assert stats.memory == 0.0
        assert stats.disk == 0.0
        assert stats.temp == 0.0
        assert stats.uptime_seconds == 0
    
    def test_uptime_format_zero(self):
        """Verificar formato de uptime en cero"""
        stats = SystemStats()
        assert stats.uptime_formatted == "0d 0h 0m"
    
    def test_uptime_format_days(self):
        """Verificar formato de uptime con días"""
        stats = SystemStats()
        stats.uptime_seconds = 90061  # 1 día, 1 hora, 1 minuto
        assert stats.uptime_formatted == "1d 1h 1m"
    
    def test_uptime_format_large(self):
        """Verificar formato con valores grandes"""
        stats = SystemStats()
        stats.uptime_seconds = 954458  # 11 días, 1 hora, 7 minutos, 38 segundos
        assert stats.uptime_formatted == "11d 1h 7m"
    
    def test_to_dict(self):
        """Verificar conversión a diccionario"""
        stats = SystemStats()
        stats.cpu = 50.5
        stats.memory = 75.2
        stats.disk = 30.0
        stats.temp = 45.0
        
        result = stats.to_dict()
        assert isinstance(result, dict)
        assert result["cpu"] == 50.5
        assert result["memory"] == 75.2
        assert result["disk"] == 30.0
        assert result["temp"] == 45.0
        assert "uptime" in result
    
    @patch('core.HAS_PSUTIL', False)
    def test_update_no_psutil(self):
        """Verificar update sin psutil"""
        stats = SystemStats()
        result = stats.update()
        assert result == False
    
    @patch('core.psutil')
    def test_update_success(self, mock_psutil):
        """Verificar update exitoso"""
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value.percent = 60.0
        mock_psutil.disk_usage.return_value.percent = 25.0
        mock_psutil.boot_time.return_value = time.time() - 3600  # 1 hora
        
        stats = SystemStats()
        result = stats.update()
        
        assert result == True
        assert stats.cpu == 45.5
        assert stats.memory == 60.0
        assert stats.disk == 25.0


class TestNetworkInfo:
    """Tests para NetworkInfo"""
    
    def test_get_hostname_success(self):
        """Verificar obtención de hostname"""
        hostname = NetworkInfo.get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0
    
    @patch('socket.gethostname')
    def test_get_hostname_error(self, mock_gethostname):
        """Verificar manejo de error en hostname"""
        mock_gethostname.side_effect = Exception("Network error")
        hostname = NetworkInfo.get_hostname()
        assert hostname == "unknown"
    
    def test_get_local_ip(self):
        """Verificar obtención de IP local"""
        ip = NetworkInfo.get_local_ip()
        assert isinstance(ip, str)
    
    @patch('core.HAS_PSUTIL', False)
    def test_get_interfaces_no_psutil(self):
        """Verificar interfaces sin psutil"""
        interfaces = NetworkInfo.get_interfaces()
        assert interfaces == {}
    
    @patch('core.HAS_PSUTIL', False)
    def test_get_traffic_no_psutil(self):
        """Verificar tráfico sin psutil"""
        traffic = NetworkInfo.get_traffic()
        assert traffic is None


class TestSystemInfo:
    """Tests para SystemInfo"""
    
    def test_get_kernel(self):
        """Verificar obtención de kernel"""
        kernel = SystemInfo.get_kernel()
        assert isinstance(kernel, str)
        # Linux kernels suelen tener formato X.Y.Z
        assert len(kernel) > 0
    
    def test_get_arch(self):
        """Verificar obtención de arquitectura"""
        arch = SystemInfo.get_arch()
        assert isinstance(arch, str)
        # Valores comunes: x86_64, aarch64, arm64
        assert len(arch) > 0
    
    @patch('core.HAS_PSUTIL', True)
    def test_get_cpu_count(self):
        """Verificar obtención de CPU count"""
        with patch('core.psutil') as mock_psutil:
            mock_psutil.cpu_count.return_value = 4
            count = SystemInfo.get_cpu_count()
            assert count == 4
    
    def test_get_python_version(self):
        """Verificar obtención de versión de Python"""
        version = SystemInfo.get_python_version()
        assert isinstance(version, str)
        assert "Python" in version


class TestLogManager:
    """Tests para LogManager"""
    
    def test_initial_empty(self):
        """Verificar log vacío inicial"""
        log = LogManager()
        assert log.entries == []
    
    def test_add_entry(self):
        """Verificar agregar entrada"""
        log = LogManager()
        log.add("Test message")
        assert len(log.entries) == 1
        assert "Test message" in log.entries[0]
    
    def test_add_multiple(self):
        """Verificar múltiples entradas"""
        log = LogManager()
        for i in range(5):
            log.add(f"Message {i}")
        assert len(log.entries) == 5
    
    def test_max_entries(self):
        """Verificar límite de entradas"""
        log = LogManager(max_entries=5)
        for i in range(10):
            log.add(f"Message {i}")
        assert len(log.entries) == 5
    
    def test_get_recent(self):
        """Verificar obtener recientes"""
        log = LogManager()
        for i in range(10):
            log.add(f"Message {i}")
        
        recent = log.get_recent(3)
        assert len(recent) == 3
        assert "Message 7" in recent[0]
    
    def test_get_recent_empty(self):
        """Verificar obtener recientes con log vacío"""
        log = LogManager()
        recent = log.get_recent()
        assert len(recent) == 1
        assert "INIT" in recent[0]
    
    def test_clear(self):
        """Verificar limpiar logs"""
        log = LogManager()
        log.add("Message 1")
        log.add("Message 2")
        log.clear()
        assert log.entries == []


class TestOctopusAnimator:
    """Tests para OctopusAnimator"""
    
    def test_initial_state(self):
        """Verificar estado inicial"""
        animator = OctopusAnimator()
        assert animator.blink_timer == 0
        assert animator.is_blinking == False
    
    def test_update_increments_timer(self):
        """Verificar que update incrementa el timer"""
        animator = OctopusAnimator()
        animator.update(0.1)
        assert animator.blink_timer == pytest.approx(0.1, 0.01)
    
    def test_get_eye_state_not_blinking(self):
        """Verificar estado de ojo cuando no parpadea"""
        animator = OctopusAnimator()
        animator.is_blinking = False
        assert animator.get_eye_state(0) == "open"
    
    def test_get_eye_state_blinking(self):
        """Verificar estado de ojo cuando parpadea"""
        animator = OctopusAnimator()
        animator.is_blinking = True
        assert animator.get_eye_state(0) == "closed"
    
    def test_calculate_tentacle_points(self):
        """Verificar cálculo de puntos de tentáculo"""
        points_top, points_bottom = OctopusAnimator.calculate_tentacle_points(
            center_x=100, center_y=100, size=50, 
            time_offset=0, tentacle_index=0, num_segments=10
        )
        
        assert len(points_top) == 10
        assert len(points_bottom) == 10
        
        # Verificar que los puntos son tuplas de 2 elementos
        for pt in points_top:
            assert len(pt) == 2
            assert isinstance(pt[0], (int, float))
            assert isinstance(pt[1], (int, float))


class TestNavigation:
    """Tests para Navigation"""
    
    def test_initial_section(self):
        """Verificar sección inicial"""
        nav = Navigation()
        assert nav.current == "STATS"
    
    def test_next_section(self):
        """Verificar navegación siguiente"""
        nav = Navigation()
        result = nav.next()
        assert result == "SYSTEM"
        assert nav.current_index == 1
    
    def test_next_wraps_around(self):
        """Verificar wrap-around en next"""
        nav = Navigation()
        # Ir al final
        for _ in range(len(Navigation.SECTIONS) - 1):
            nav.next()
        
        # Siguiente debe volver al inicio
        result = nav.next()
        assert result == "STATS"
        assert nav.current_index == 0
    
    def test_previous_section(self):
        """Verificar navegación anterior"""
        nav = Navigation()
        nav.next()  # SYSTEM
        result = nav.previous()
        assert result == "STATS"
    
    def test_previous_wraps_around(self):
        """Verificar wrap-around en previous"""
        nav = Navigation()
        result = nav.previous()  # Del inicio va al final
        assert nav.current_index == len(Navigation.SECTIONS) - 1
    
    def test_goto_valid_index(self):
        """Verificar goto con índice válido"""
        nav = Navigation()
        result = nav.goto(3)
        assert result == "OTTO"
        assert nav.current_index == 3
    
    def test_goto_invalid_index(self):
        """Verificar goto con índice inválido"""
        nav = Navigation()
        result = nav.goto(100)
        assert result is None
        assert nav.current_index == 0
    
    def test_goto_negative_index(self):
        """Verificar goto con índice negativo"""
        nav = Navigation()
        result = nav.goto(-1)
        assert result is None
    
    def test_goto_name(self):
        """Verificar goto por nombre"""
        nav = Navigation()
        result = nav.goto_name("NETWORK")
        assert result == "NETWORK"
        assert nav.current_index == 2
    
    def test_goto_name_case_insensitive(self):
        """Verificar goto por nombre (case insensitive)"""
        nav = Navigation()
        result = nav.goto_name("network")
        assert result == "NETWORK"
    
    def test_goto_name_invalid(self):
        """Verificar goto con nombre inválido"""
        nav = Navigation()
        result = nav.goto_name("INVALID")
        assert result is None
    
    def test_sections_count(self):
        """Verificar cantidad de secciones"""
        assert len(Navigation.SECTIONS) == 6


class TestHelpSystem:
    """Tests para HelpSystem"""
    
    def test_controls_not_empty(self):
        """Verificar que hay controles definidos"""
        assert len(HelpSystem.CONTROLS) > 0
    
    def test_sections_info_not_empty(self):
        """Verificar que hay info de secciones"""
        assert len(HelpSystem.SECTIONS_INFO) > 0
    
    def test_get_controls_text(self):
        """Verificar obtención de texto de controles"""
        lines = HelpSystem.get_controls_text()
        assert isinstance(lines, list)
        assert len(lines) == len(HelpSystem.CONTROLS)
        
        for line in lines:
            assert isinstance(line, str)
            assert len(line) > 0
    
    def test_get_sections_help(self):
        """Verificar obtención de ayuda de secciones"""
        lines = HelpSystem.get_sections_help()
        assert isinstance(lines, list)
        assert len(lines) == len(HelpSystem.SECTIONS_INFO)
        
        for line in lines:
            assert isinstance(line, str)
            assert "-" in line  # Formato: "SECTION - description"
    
    def test_controls_format(self):
        """Verificar formato de controles"""
        for key, desc in HelpSystem.CONTROLS:
            assert isinstance(key, str)
            assert isinstance(desc, str)
            assert len(key) > 0
            assert len(desc) > 0
    
    def test_sections_info_complete(self):
        """Verificar que todas las secciones tienen info"""
        nav_sections = Navigation.SECTIONS
        for section in nav_sections:
            assert section in HelpSystem.SECTIONS_INFO, f"Falta info para {section}"


class TestIntegration:
    """Tests de integración"""
    
    def test_log_and_navigation(self):
        """Verificar interacción entre log y navegación"""
        log = LogManager()
        nav = Navigation()
        
        # Simular navegación y logging
        nav.next()
        log.add(f"Navegando a: {nav.current}")
        
        nav.goto_name("OTTO")
        log.add(f"Navegando a: {nav.current}")
        
        assert len(log.entries) == 2
        assert "SYSTEM" in log.entries[0]
        assert "OTTO" in log.entries[1]
    
    def test_stats_to_log(self):
        """Verificar logging de estadísticas"""
        stats = SystemStats()
        log = LogManager()
        
        stats.cpu = 95.5
        stats.memory = 80.0
        
        if stats.cpu > 90:
            log.add(f"ALERTA: CPU alto: {stats.cpu}%")
        if stats.memory > 75:
            log.add(f"ALERTA: Memoria alta: {stats.memory}%")
        
        assert len(log.entries) == 2
        assert any("CPU alto" in e for e in log.entries)
        assert any("Memoria alta" in e for e in log.entries)


# Fixtures para tests
@pytest.fixture
def stats():
    """Fixture para SystemStats"""
    return SystemStats()


@pytest.fixture
def log():
    """Fixture para LogManager"""
    return LogManager()


@pytest.fixture
def nav():
    """Fixture para Navigation"""
    return Navigation()


# Tests usando fixtures
class TestWithFixtures:
    """Tests usando fixtures"""
    
    def test_stats_fixture(self, stats):
        assert stats.cpu == 0.0
    
    def test_log_fixture(self, log):
        log.add("test")
        assert len(log.entries) == 1
    
    def test_nav_fixture(self, nav):
        assert nav.current == "STATS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
