"""Gestión segura de perfiles y Game Boost de CorePulse."""
from .profile_manager import PerformanceProfileManager
from .game_detector import GameDetector
from .power_manager import PowerManager
from .game_boost import GameBoostOptimizer

__all__ = ['PerformanceProfileManager', 'GameDetector', 'PowerManager', 'GameBoostOptimizer']

# Aliases para compatibilidad de imports anteriores a V480; no se ejecuta lógica extra.
# Ambos módulos se importan arriba indirectamente al construir la API performance.
import sys as _sys
from . import profile_manager as settings_backup
from . import power_manager as managed_power_plans
_sys.modules.setdefault(__name__ + '.settings_backup', settings_backup)
_sys.modules.setdefault(__name__ + '.managed_power_plans', managed_power_plans)
del _sys
