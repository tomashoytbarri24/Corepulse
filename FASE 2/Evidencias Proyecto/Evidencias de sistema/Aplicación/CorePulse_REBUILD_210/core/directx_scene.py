"""Escena determinista del benchmark gráfico DirectX de CorePulse: ciudad nocturna V29.

Este módulo NO mide rendimiento. Define la ciudad (lotes, edificios, faroles,
vehículos, nubes y vapor), las mallas y el recorrido de cámara para que el
backend Direct3D ejecute exactamente el mismo workload en cualquier máquina.
La distribución se genera aquí, en Python, con una semilla fija: así las
pruebas automáticas pueden comprobar que la cámara y los vehículos nunca
atraviesan un edificio. Todos los conteos publicados se derivan de estas
estructuras.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
import random
from typing import Sequence


@dataclass(frozen=True)
class SceneLevel:
    key: str
    label: str
    ground_resolution: int
    building_instances: int
    streetlight_instances: int
    vehicle_instances: int
    cloud_instances: int
    shader_iterations: int
    texture_samples: int
    warmup_seconds: float
    settle_seconds: float
    measure_seconds: float
    steam_instances: int = 0
    reflection_divisor: int = 2   # reflejo planar: 2 = media resolución, 1 = completa
    volumetric_steps: int = 0     # pasos por píxel de la luz volumétrica de luna


SCENE_LEVELS: tuple[SceneLevel, ...] = (
    SceneLevel('avenue', 'Escena 1 · Avenida de neón', 96, 500, 260, 60, 24, 10, 5, 5.0, 0.75, 10.0, 4, 2, 12),
    SceneLevel('district', 'Escena 2 · Distrito financiero', 144, 1200, 600, 140, 40, 20, 9, 0.0, 1.00, 12.0, 8, 2, 20),
    SceneLevel('skyline', 'Escena 3 · Horizonte nocturno', 192, 2000, 1000, 260, 60, 38, 16, 0.0, 1.00, 12.0, 12, 2, 32),
    SceneLevel('megacity', 'Escena 4 · Megaciudad / Extreme', 256, 3000, 1600, 480, 90, 64, 24, 0.0, 1.25, 15.0, 18, 1, 56),
)


def profile_levels(profile: str = 'standard') -> tuple[SceneLevel, ...]:
    """Devuelve los niveles con tiempos del perfil, sin alterar su complejidad."""
    key = str(profile or 'standard').strip().lower()
    if key == 'quick':
        return tuple(SceneLevel(**{**s.__dict__, 'warmup_seconds': (2.0 if i == 0 else 0.0), 'settle_seconds': 0.75, 'measure_seconds': 5.0}) for i, s in enumerate(SCENE_LEVELS[:3]))
    if key == 'extended':
        return tuple(SceneLevel(**{**s.__dict__, 'warmup_seconds': (6.0 if i == 0 else 0.0), 'settle_seconds': 1.25, 'measure_seconds': 20.0}) for i, s in enumerate(SCENE_LEVELS))
    return SCENE_LEVELS


# ---------------------------------------------------------------------------
# Trazado urbano. Manzanas de 3×3 lotes separadas por calles; un bulevar
# circular sin edificios (anillo) es el recorrido de la cámara.
# Estos números también están escritos en el shader (ground/faroles); la
# prueba test_073 comprueba que coincidan.
# ---------------------------------------------------------------------------
CITY = {
    'lot': 20.0,            # lado del lote
    'lots_per_block': 3,
    'road': 16.0,           # ancho de calle
    'half_blocks': 9,       # manzanas -9..9 por eje
    'ring_radius': 173.0,   # centro del bulevar circular
    'ring_half_width': 23.0,
    'lamp_spacing': 19.0,
    'lamp_height': 9.0,
    'seed': 0xC17E,
}
PITCH = CITY['lot'] * CITY['lots_per_block'] + CITY['road']          # 76
CITY_EXTENT = (CITY['half_blocks'] + 0.5) * PITCH                     # 722
RING_INNER = CITY['ring_radius'] - CITY['ring_half_width']             # 150
RING_OUTER = CITY['ring_radius'] + CITY['ring_half_width']             # 196
LAMP_EDGE = CITY['road'] / 2.0 - 1.2                                   # faroles a 6,8 del eje
# Tubo que recorre la cámara (con margen): nada se ubica dentro.
CAMERA_TUBE = {'r_min': 166.0, 'r_max': 180.0, 'y_min': 30.0, 'y_max': 60.0}


def _rect_radial_range(x: float, z: float, hw: float, hd: float) -> tuple[float, float]:
    """Distancia mínima y máxima al centro de un rectángulo alineado a los ejes."""
    nx = max(abs(x) - hw, 0.0) if abs(x) > hw else 0.0
    nz = max(abs(z) - hd, 0.0) if abs(z) > hd else 0.0
    fx, fz = abs(x) + hw, abs(z) + hd
    return math.hypot(nx, nz), math.hypot(fx, fz)


def _road_centers() -> list[float]:
    hb = CITY['half_blocks']
    return [(i + 0.5) * PITCH for i in range(-hb - 1, hb + 1)]


@lru_cache(maxsize=1)
def city_layout() -> dict:
    """Instancias de la ciudad, deterministas, ordenadas por relevancia visual.

    Cada instancia son 8 floats (dos float4 por instancia en el input layout):
    - edificio: (x, z, ancho, alto), (fondo, estilo 0..3, semilla 0..1, 0)
    - farol:    (x, z, yaw, alto), (variante, semilla, 0, 0)
    - vehículo: (tipo carril, a, alto, velocidad), (fase, color, tamaño, 0)
    - nube:     (x, y, z, escala), (semilla, 0, 0, 0)
    - vapor:    (x, z, semilla, 0), (0, 0, 0, 0)
    """
    rng = random.Random(CITY['seed'])
    lot = CITY['lot']
    hb = CITY['half_blocks']
    buildings = []
    for bi in range(-hb, hb + 1):
        for bj in range(-hb, hb + 1):
            for k in range(3):
                for m in range(3):
                    x = bi * PITCH + (k - 1) * lot
                    z = bj * PITCH + (m - 1) * lot
                    w = lot * rng.uniform(0.62, 0.90)
                    d = lot * rng.uniform(0.62, 0.90)
                    r = math.hypot(x, z)
                    core = math.exp(-(r / 240.0) ** 2)
                    h = 16.0 + 260.0 * core * (0.35 + 0.65 * rng.random()) + 40.0 * rng.random() ** 2
                    if rng.random() < 0.05 * core + 0.01:
                        h *= 1.45  # rascacielos emblemáticos
                    roll = rng.random()
                    style = 0 if roll < 0.35 else 1 if roll < 0.65 else 2 if roll < 0.85 else 3
                    seed = rng.random()
                    near, far = _rect_radial_range(x, z, w / 2.0, d / 2.0)
                    if near < RING_OUTER and far > RING_INNER:
                        continue  # el bulevar circular queda libre
                    buildings.append((x, z, w, h, d, float(style), seed, 0.0))
    buildings.sort(key=lambda b: (round(math.hypot(b[0], b[1]), 3), b[0], b[1]))

    lamps = []
    spacing = CITY['lamp_spacing']
    roads = _road_centers()
    steps = int(2 * CITY_EXTENT // spacing)
    for rc in roads:
        for side in (-1.0, 1.0):
            for n in range(steps + 1):
                along = -CITY_EXTENT + n * spacing
                if any(abs(along - other) < CITY['road'] / 2.0 + 1.0 for other in roads):
                    continue  # no se ponen faroles en los cruces
                for x, z, yaw in ((rc + side * LAMP_EDGE, along, 0.0 if side < 0 else math.pi),
                                  (along, rc + side * LAMP_EDGE, math.pi / 2 if side < 0 else -math.pi / 2)):
                    if RING_INNER - 2.0 < math.hypot(x, z) < RING_OUTER + 2.0:
                        continue  # el bulevar tiene su propia hilera
                    lamps.append((x, z, yaw, CITY['lamp_height'], float(rng.randrange(3)), rng.random(), 0.0, 0.0))
    for radius, inward in ((RING_INNER + 1.2, False), (RING_OUTER - 1.2, True)):
        count = int(2 * math.pi * radius // 16.0)
        for k in range(count):
            a = 2 * math.pi * k / count
            # El brazo (+X local) apunta hacia el centro del bulevar.
            yaw = a + (math.pi if inward else 0.0)
            lamps.append((radius * math.cos(a), radius * math.sin(a), yaw, CITY['lamp_height'],
                          float(rng.randrange(3)), rng.random(), 0.0, 0.0))
    lamps.sort(key=lambda l: (round(abs(math.hypot(l[0], l[1]) - CITY['ring_radius']), 3), l[0], l[1]))

    vehicles = []
    lanes_x = [rc + off for rc in roads for off in (-3.5, 3.5)]
    while len(vehicles) < 600:
        kind = rng.random()
        phase, color, size = rng.random(), float(rng.randrange(4)), rng.uniform(0.9, 1.25)
        if kind < 0.40:
            # Bulevar: carriles lejos del tubo de la cámara o muy por encima.
            if rng.random() < 0.7:
                radius = rng.choice((154.0, 158.0, 188.0, 192.0)); height = rng.uniform(16.0, 120.0)
            else:
                radius = rng.uniform(163.0, 183.0); height = rng.uniform(78.0, 130.0)
            speed = rng.uniform(0.05, 0.11) * rng.choice((-1.0, 1.0))
            vehicles.append((0.0, radius, height, speed, phase, color, size, 0.0))
        else:
            lane = rng.choice(lanes_x)
            height = rng.uniform(10.0, 16.0) if rng.random() < 0.45 else rng.uniform(78.0, 150.0)
            speed = rng.uniform(10.0, 24.0) * rng.choice((-1.0, 1.0))
            vehicles.append((1.0 if kind < 0.70 else 2.0, lane, height, speed, phase, color, size, 0.0))

    clouds = []
    for _ in range(120):
        clouds.append((rng.uniform(-900.0, 900.0), rng.uniform(270.0, 350.0), rng.uniform(-900.0, 900.0),
                       rng.uniform(10.0, 22.0), rng.random(), 0.0, 0.0, 0.0))
    clouds.sort(key=lambda c: (round(math.hypot(c[0], c[2]), 3), c[0]))

    steam = []
    near_roads = [rc for rc in roads if abs(rc) < 300.0]
    while len(steam) < 24:
        rc = rng.choice(near_roads); along = rng.uniform(-280.0, 280.0)
        x, z = (rc, along) if rng.random() < 0.5 else (along, rc)
        if RING_INNER - 4.0 < math.hypot(x, z) < RING_OUTER + 4.0:
            continue
        steam.append((x, z, rng.random(), 0.0, 0.0, 0.0, 0.0, 0.0))
    steam.sort(key=lambda s: (round(abs(math.hypot(s[0], s[1]) - CITY['ring_radius']), 3), s[0]))
    return {'buildings': buildings, 'streetlights': lamps, 'vehicles': vehicles, 'clouds': clouds, 'steam': steam}


def lamp_coverage(count: int) -> float:
    """Distancia al bulevar hasta la que hay faroles dibujados (para el suelo)."""
    lamps = city_layout()['streetlights'][:max(0, int(count))]
    return max((abs(math.hypot(l[0], l[1]) - CITY['ring_radius']) for l in lamps), default=0.0) + 4.0


def camera_pose(t: float, level_index: int):
    """Recorrido de cámara sobre el bulevar circular (ojo, objetivo).

    Radio 169..177 y altura 34..56: siempre dentro de ``CAMERA_TUBE``, que no
    contiene edificios, faroles ni vehículos (test_073).
    """
    theta = 0.7 + level_index * 1.65 + t * 0.045
    r = CITY['ring_radius'] + 4.0 * math.sin(t * 0.29 + level_index)
    y = 45.0 + 11.0 * math.sin(t * 0.19 + level_index * 0.8)
    eye = (r * math.cos(theta), y, r * math.sin(theta))
    tangent = (-math.sin(theta), 0.0, math.cos(theta))
    inward = (-math.cos(theta), 0.0, -math.sin(theta))
    lean = 18.0 + 8.0 * math.sin(t * 0.13 + level_index)
    drop = -16.0 + 6.0 * math.sin(t * 0.23 + level_index * 0.5)
    target = (eye[0] + tangent[0] * 70.0 + inward[0] * lean, eye[1] + drop, eye[2] + tangent[2] * 70.0 + inward[2] * lean)
    return eye, target


# ---------------------------------------------------------------------------
# Mallas. Vértice = posición3, normal3, uv2. UV.y >= 1.5 marca techo o luces
# emisivas; UV.x >= 2.5 marca chaflanes (bordes de neón) en edificios.
# ---------------------------------------------------------------------------

def build_ground(resolution: int, span: float = 1600.0):
    n = max(8, int(resolution))
    vertices: list[tuple[float, ...]] = []
    indices: list[int] = []
    for j in range(n):
        v = j / (n - 1); z = (v - 0.5) * span
        for i in range(n):
            u = i / (n - 1); x = (u - 0.5) * span
            vertices.append((x, 0.0, z, 0.0, 1.0, 0.0, u, v))
    for j in range(n - 1):
        for i in range(n - 1):
            a = j * n + i; b = a + 1; c = a + n; d = c + 1
            indices.extend((a, c, b, b, c, d))
    return vertices, indices


def _quad(verts, idx, p0, p1, p2, p3, normal, uv):
    base = len(verts)
    for p, t in zip((p0, p1, p2, p3), uv):
        verts.append((*p, *normal, *t))
    idx.extend((base, base + 1, base + 2, base, base + 2, base + 3))


def build_building(chamfer: float = 0.07):
    """Torre unitaria (x,z en -0,5..0,5; y en 0..1) con aristas achaflanadas.

    El VS la escala por instancia. Las caras principales llevan UV 0..1, los
    chaflanes UV.x 3..4 (franjas de neón) y el techo UV.y 2..3.
    """
    c = 0.5 - chamfer
    ring = [(c, -0.5), (0.5, -c), (0.5, c), (c, 0.5), (-c, 0.5), (-0.5, c), (-0.5, -c), (-c, -0.5)]
    verts: list[tuple[float, ...]] = []; idx: list[int] = []
    for k in range(8):
        (x0, z0), (x1, z1) = ring[k], ring[(k + 1) % 8]
        ex, ez = x1 - x0, z1 - z0
        ln = math.hypot(ex, ez) or 1.0
        normal = (ez / ln, 0.0, -ex / ln)
        u0, u1 = (0.0, 1.0) if k % 2 == 1 else (3.0, 4.0)
        _quad(verts, idx, (x0, 0.0, z0), (x1, 0.0, z1), (x1, 1.0, z1), (x0, 1.0, z0), normal,
              ((u0, 0.0), (u1, 0.0), (u1, 1.0), (u0, 1.0)))
    base = len(verts)
    verts.append((0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.5, 2.5))
    for x, z in ring:
        verts.append((x, 1.0, z, 0.0, 1.0, 0.0, x + 0.5, z + 2.5))
    for k in range(8):
        idx.extend((base, base + 1 + k, base + 1 + (k + 1) % 8))
    return verts, idx


def _box(verts, idx, cx, cy, cz, hx, hy, hz, uv_y=0.5):
    faces = (
        ((1, 0, 0), [(cx + hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz + hz), (cx + hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz - hz)]),
        ((-1, 0, 0), [(cx - hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz - hz), (cx - hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz + hz)]),
        ((0, 0, 1), [(cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz), (cx - hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz + hz)]),
        ((0, 0, -1), [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz)]),
        ((0, 1, 0), [(cx - hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]),
        ((0, -1, 0), [(cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz - hz), (cx - hx, cy - hy, cz - hz)]),
    )
    for normal, pts in faces:
        _quad(verts, idx, *pts, normal, ((0.0, uv_y), (1.0, uv_y), (1.0, uv_y), (0.0, uv_y)))


def build_streetlight():
    """Farol: poste, brazo hacia +X y cabezal con la cara inferior emisiva."""
    verts: list[tuple[float, ...]] = []; idx: list[int] = []
    h = CITY['lamp_height']
    _box(verts, idx, 0.0, h / 2.0, 0.0, 0.14, h / 2.0, 0.14)
    _box(verts, idx, 1.25, h - 0.15, 0.0, 1.25, 0.08, 0.08)
    _box(verts, idx, 2.35, h - 0.28, 0.0, 0.42, 0.10, 0.20)
    # Lente emisiva bajo el cabezal (UV.y 2).
    _quad(verts, idx, (1.98, h - 0.39, 0.17), (2.72, h - 0.39, 0.17), (2.72, h - 0.39, -0.17), (1.98, h - 0.39, -0.17),
          (0.0, -1.0, 0.0), ((0.0, 2.0), (1.0, 2.0), (1.0, 2.0), (0.0, 2.0)))
    return verts, idx


def build_vehicle():
    """Vehículo volador: casco en cuña (proa +X) y franjas de luz emisivas.

    Luces: UV.y 2, UV.x 0 = faros delanteros, 1 = luces traseras rojas.
    """
    verts: list[tuple[float, ...]] = []; idx: list[int] = []
    l, w, h = 2.4, 0.95, 0.55
    top = [(-l, h, -w * 0.8), (l * 0.55, h * 0.9, -w * 0.62), (l * 0.55, h * 0.9, w * 0.62), (-l, h, w * 0.8)]
    bot = [(-l, -h * 0.6, -w), (l, -h * 0.2, -w * 0.55), (l, -h * 0.2, w * 0.55), (-l, -h * 0.6, w)]
    nose = (l * 1.08, 0.0, 0.0)

    def face(p0, p1, p2, p3):
        ax, ay, az = (p1[i] - p0[i] for i in range(3)); bx, by, bz = (p3[i] - p0[i] for i in range(3))
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        _quad(verts, idx, p0, p1, p2, p3, (nx / ln, ny / ln, nz / ln), ((0.0, 0.5), (1.0, 0.5), (1.0, 0.5), (0.0, 0.5)))

    face(top[0], top[3], top[2], top[1])             # techo
    face(bot[0], bot[1], bot[2], bot[3])             # panza
    face(bot[0], top[0], top[1], bot[1])             # lateral izquierdo
    face(bot[3], bot[2], top[2], top[3])             # lateral derecho
    face(bot[0], bot[3], top[3], top[0])             # cola
    face(bot[1], top[1], nose, bot[1])               # morro izquierdo (triángulo degenerado en quad)
    face(bot[2], bot[1], nose, nose)
    face(top[2], bot[2], nose, nose)
    face(top[1], top[2], nose, nose)
    # Franjas de luz (UV.y 2): faros en el morro y barra trasera.
    _quad(verts, idx, (l * 0.98, -0.05, -w * 0.5), (l * 0.98, -0.05, w * 0.5), (l * 0.98, 0.10, w * 0.45), (l * 0.98, 0.10, -w * 0.45),
          (1.0, 0.0, 0.0), ((0.0, 2.0), (0.0, 2.0), (0.0, 2.0), (0.0, 2.0)))
    _quad(verts, idx, (-l - 0.01, 0.05, w * 0.75), (-l - 0.01, 0.05, -w * 0.75), (-l - 0.01, 0.22, -w * 0.72), (-l - 0.01, 0.22, w * 0.72),
          (-1.0, 0.0, 0.0), ((1.0, 2.0), (1.0, 2.0), (1.0, 2.0), (1.0, 2.0)))
    return verts, idx


def _append_cloud_card(dst_v, dst_i, center, half_w, half_h, yaw, pitch=0.0):
    """Tarjeta suave; UV 0..1 se usa para el alpha radial en el PS."""
    cx, cy, cz = center
    sy, cyaw = math.sin(yaw), math.cos(yaw)
    sp, cp = math.sin(pitch), math.cos(pitch)
    rx, ry, rz = cyaw, 0.0, -sy
    ux, uy, uz = sy * sp, cp, cyaw * sp
    nx, ny, nz = sy * cp, -sp, cyaw * cp
    base = len(dst_v)
    for sx, syy, u, v in ((-1, -1, 0, 0), (1, -1, 1, 0), (1, 1, 1, 1), (-1, 1, 0, 1)):
        px = cx + rx * (sx * half_w) + ux * (syy * half_h)
        py = cy + ry * (sx * half_w) + uy * (syy * half_h)
        pz = cz + rz * (sx * half_w) + uz * (syy * half_h)
        dst_v.append((px, py, pz, nx, ny, nz, float(u), float(v)))
    dst_i.extend((base, base + 1, base + 2, base, base + 2, base + 3))


def build_cloud():
    """Nube de tarjetas cruzadas con puffs de distintas escalas."""
    verts: list[tuple[float, ...]] = []; idx: list[int] = []
    puffs = (
        (0.00, 0.00, 0.00, 1.70, 0.82),
        (1.18, 0.02, 0.12, 1.15, 0.68), (-1.20, 0.00, 0.06, 1.20, 0.70),
        (0.42, 0.48, -0.10, 1.02, 0.72), (-0.48, 0.44, 0.10, 0.98, 0.70),
        (1.78, -0.08, 0.02, 0.86, 0.54), (-1.76, -0.06, -0.04, 0.90, 0.56),
        (0.02, 0.70, 0.04, 0.88, 0.62), (0.72, 0.64, 0.18, 0.72, 0.54),
        (-0.74, 0.62, -0.16, 0.74, 0.54),
    )
    for pi, (x, y, z, hw, hh) in enumerate(puffs):
        phase = (pi * 0.754877666) % 1.0 * math.tau
        _append_cloud_card(verts, idx, (x, y, z), hw, hh, phase, 0.0)
        _append_cloud_card(verts, idx, (x, y, z), hw * 0.96, hh * 0.96, phase + math.pi / 2.0, 0.0)
        _append_cloud_card(verts, idx, (x, y + 0.08, z), hw * 0.88, hh * 0.82, phase + math.pi / 4.0, 0.20 if pi % 2 == 0 else -0.20)
    return verts, idx


def build_steam_plume():
    """Columna de vapor de alcantarilla con tarjetas apiladas."""
    verts: list[tuple[float, ...]] = []; idx: list[int] = []
    layers = (
        (0.00, 0.15, 0.00, 0.55, 0.85, 0.0),
        (0.08, 1.35, 0.06, 0.82, 1.10, 0.7),
        (-0.10, 2.85, -0.04, 1.05, 1.34, 1.5),
        (0.18, 4.65, 0.08, 1.26, 1.56, 2.2),
        (-0.16, 6.90, 0.02, 1.46, 1.82, 2.9),
        (0.10, 9.35, -0.08, 1.64, 2.02, 3.6),
    )
    for li, (x, y, z, hw, hh, phase) in enumerate(layers):
        _append_cloud_card(verts, idx, (x, y, z), hw, hh, phase, 0.0)
        _append_cloud_card(verts, idx, (x, y, z), hw * 0.94, hh * 0.94, phase + math.pi / 2.0, 0.0)
        if li >= 2:
            _append_cloud_card(verts, idx, (x, y + 0.12, z), hw * 0.84, hh * 0.80, phase + math.pi / 4.0, 0.12 if li % 2 == 0 else -0.12)
    return verts, idx


def build_sky(lat_segments: int = 22, lon_segments: int = 44):
    """Esfera UV limpia; el VS la centra en la cámara."""
    lat = max(8, int(lat_segments)); lon = max(16, int(lon_segments))
    verts = []; idx = []
    for y in range(lat + 1):
        v = y / lat; phi = math.pi * v
        sp = math.sin(phi); cp = math.cos(phi)
        for x in range(lon + 1):
            u = x / lon; th = 2.0 * math.pi * u
            px = sp * math.cos(th); py = cp; pz = sp * math.sin(th)
            verts.append((px, py, pz, px, py, pz, u, v))
    row = lon + 1
    for y in range(lat):
        for x in range(lon):
            a = y * row + x; b = a + 1; c = (y + 1) * row + x; d = c + 1
            idx.extend((a, c, b, b, c, d))
    return verts, idx


def mesh_triangles(indices: Sequence[int]) -> int:
    return len(indices) // 3


def level_workload(level: SceneLevel) -> dict:
    layout = city_layout()
    counts = {
        'building_instances': min(level.building_instances, len(layout['buildings'])),
        'streetlight_instances': min(level.streetlight_instances, len(layout['streetlights'])),
        'vehicle_instances': min(level.vehicle_instances, len(layout['vehicles'])),
        'cloud_instances': min(level.cloud_instances, len(layout['clouds'])),
        'steam_instances': min(level.steam_instances, len(layout['steam'])),
    }
    ground_tri = 2 * (level.ground_resolution - 1) ** 2
    per_mesh = {
        'building_instances': mesh_triangles(build_building()[1]),
        'streetlight_instances': mesh_triangles(build_streetlight()[1]),
        'vehicle_instances': mesh_triangles(build_vehicle()[1]),
        'cloud_instances': mesh_triangles(build_cloud()[1]),
        'steam_instances': mesh_triangles(build_steam_plume()[1]),
    }
    scene_tri = ground_tri + sum(per_mesh[k] * counts[k] for k in counts) + mesh_triangles(build_sky()[1])
    # Sombras (edificios, faroles, vehículos) y reflejo del suelo (todo menos suelo y vapor).
    shadow_tri = sum(per_mesh[k] * counts[k] for k in ('building_instances', 'streetlight_instances', 'vehicle_instances'))
    reflection_tri = scene_tri - ground_tri - per_mesh['steam_instances'] * counts['steam_instances']
    return {
        'ground_resolution': level.ground_resolution,
        'ground_triangles': ground_tri,
        **counts,
        'shader_iterations': level.shader_iterations,
        'texture_samples': level.texture_samples,
        'reflection_resolution': f'1/{max(1, int(level.reflection_divisor))}',
        'volumetric_steps': level.volumetric_steps,
        'approx_triangles_per_frame': scene_tri + shadow_tri + reflection_tri,
        'object_instances': sum(counts.values()) + 2,
        'render_passes': 'sombras + reflejo + escena HDR + 8 pasadas de post-proceso',
        'warmup_seconds': level.warmup_seconds,
        'settle_seconds': level.settle_seconds,
        'measure_seconds': level.measure_seconds,
    }


def all_workloads(profile: str = 'standard') -> list[dict]:
    return [{'key': s.key, 'label': s.label, **level_workload(s)} for s in profile_levels(profile)]
