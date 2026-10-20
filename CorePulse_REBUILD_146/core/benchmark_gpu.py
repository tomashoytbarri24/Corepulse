"""Benchmark 3D DirectX 11 de CorePulse V29 (ciudad nocturna, reflejos, HDR, MSAA y bloom + medición por reloj de pared).

Objetivo: una prueba gráfica de alto nivel, visible, determinista y auditable.
El workload aumenta por niveles y la medición se basa únicamente en frames
realmente presentados durante la ventana de medición. El warm-up queda fuera.

En plataformas no Windows o si Direct3D no puede inicializarse se devuelve N/A;
no existe fallback silencioso al benchmark OpenGL anterior porque cambiaría la
metodología.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict
import math
import os
import platform
import statistics
import re
import struct
import threading
import time
from typing import Any, Callable, Optional

GPU_BENCHMARK_LABEL = 'V29'
# V27: medición (FPS por reloj de pared, frametime Present→Present, render fijo
# 1920×1080, GPU de alto rendimiento). V28: sombras, HDR con MSAA 4x, bloom y
# ACES. V29: escena nueva de ciudad nocturna con reflejo planar de calles
# mojadas, neón y vehículos: otra carga, no se compara con V28.
GPU_BENCHMARK_METHOD = 'COREPULSE_GPU_DIRECTX11_SCENES_V29_NEON_CITY_REFLECTIONS_HDR_MSAA_FIXED1080P_PRESENT_INTERVAL_WALLCLOCK_DETERMINISTIC'
GPU_PROVIDER = 'CorePulse DirectX 11 Real-World Benchmark V29'
GPU_POLICY = 'REAL_OR_NA_DIRECTX11_V29_NEON_CITY_GPU_TIMESTAMP_NO_MODEL_LOOKUP_NO_SYNTHETIC_SCORE'
RENDER_WIDTH = 1920
RENDER_HEIGHT = 1080
from core.directx_scene import (
    SceneLevel, profile_levels, build_ground, build_building, build_streetlight, build_vehicle,
    build_cloud, build_steam_plume, build_sky, city_layout, camera_pose, lamp_coverage, level_workload,
)

ProgressCallback = Optional[Callable[[float, str, str], None]]
TelemetrySampler = Optional[Callable[[], dict]]
CancelCheck = Optional[Callable[[], bool]]

WINFUNCTYPE = getattr(ctypes, 'WINFUNCTYPE', ctypes.CFUNCTYPE)

HWND_T = getattr(wintypes, 'HWND', wintypes.HANDLE)
HINSTANCE_T = getattr(wintypes, 'HINSTANCE', wintypes.HANDLE)
HICON_T = getattr(wintypes, 'HICON', wintypes.HANDLE)
HCURSOR_T = getattr(wintypes, 'HCURSOR', wintypes.HANDLE)
HBRUSH_T = getattr(wintypes, 'HBRUSH', wintypes.HANDLE)
HMENU_T = getattr(wintypes, 'HMENU', wintypes.HANDLE)
HRESULT = ctypes.c_long
UINT = ctypes.c_uint
BOOL = ctypes.c_int
FLOAT = ctypes.c_float
SIZE_T = ctypes.c_size_t
LPVOID = ctypes.c_void_p

S_OK = 0
D3D11_SDK_VERSION = 7
D3D_DRIVER_TYPE_HARDWARE = 1
D3D11_CREATE_DEVICE_BGRA_SUPPORT = 0x20
D3D_FEATURE_LEVEL_11_0 = 0xB000
D3D_FEATURE_LEVEL_10_1 = 0xA100
D3D_FEATURE_LEVEL_10_0 = 0xA000

DXGI_FORMAT_R32G32B32A32_FLOAT = 2
DXGI_FORMAT_R32G32B32_FLOAT = 6
DXGI_FORMAT_R32G32_FLOAT = 16
DXGI_FORMAT_R32_UINT = 42
DXGI_FORMAT_R8G8B8A8_UNORM = 28
DXGI_FORMAT_D24_UNORM_S8_UINT = 45
DXGI_FORMAT_R16G16B16A16_FLOAT = 10
DXGI_FORMAT_R11G11B10_FLOAT = 26
DXGI_FORMAT_R32_TYPELESS = 39
DXGI_FORMAT_D32_FLOAT = 40
DXGI_FORMAT_R32_FLOAT = 41
D3D11_BIND_RENDER_TARGET = 0x20
D3D11_DSV_DIMENSION_TEXTURE2D = 3
D3D11_SRV_DIMENSION_TEXTURE2D = 4
D3D11_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT = 0x94
D3D11_TEXTURE_ADDRESS_CLAMP = 3
D3D11_TEXTURE_ADDRESS_BORDER = 4
D3D11_COMPARISON_LESS_EQUAL = 4
CTX_DRAW = 13
CTX_RESOLVE_SUBRESOURCE = 57
DEVICE_CHECK_MULTISAMPLE_QUALITY_LEVELS = 30
SHADOW_MAP_SIZE = 4096            # debe coincidir con SHADOW_TEXEL del shader
MSAA_SAMPLES = 4
# Luna (hacia la luz): baja, para que aparezca en el cielo durante el recorrido
# y sus sombras recorten las calles entre torres.
KEY_LIGHT_DIRECTION = (-0.52, 0.40, 0.75)
KEY_LIGHT_INTENSITY = 0.55
BLOOM_THRESHOLD = 1.6
BLOOM_INTENSITY = 0.60
EXPOSURE = 1.10
INSTANCE_STRIDE = 32              # dos float4 por instancia (INSTA, INSTB)
CAMERA_FOV_DEG = 60.0
CAMERA_FAR = 1800.0
DXGI_USAGE_RENDER_TARGET_OUTPUT = 0x20
DXGI_SWAP_EFFECT_DISCARD = 0

D3D11_USAGE_DEFAULT = 0
D3D11_USAGE_IMMUTABLE = 1
D3D11_BIND_VERTEX_BUFFER = 0x1
D3D11_BIND_INDEX_BUFFER = 0x2
D3D11_BIND_CONSTANT_BUFFER = 0x4
D3D11_BIND_SHADER_RESOURCE = 0x8
D3D11_BIND_DEPTH_STENCIL = 0x40
D3D11_INPUT_PER_VERTEX_DATA = 0
D3D11_INPUT_PER_INSTANCE_DATA = 1
D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST = 4
D3D11_CLEAR_DEPTH = 0x1
D3D11_CLEAR_STENCIL = 0x2
D3D11_FILTER_MIN_MAG_MIP_LINEAR = 0x15
D3D11_TEXTURE_ADDRESS_WRAP = 1
D3D11_COMPARISON_NEVER = 1
D3D11_COMPARISON_LESS = 2
D3D11_DEPTH_WRITE_MASK_ZERO = 0
D3D11_DEPTH_WRITE_MASK_ALL = 1
D3D11_STENCIL_OP_KEEP = 1
D3D11_BLEND_ZERO = 1
D3D11_BLEND_ONE = 2
D3D11_BLEND_SRC_ALPHA = 5
D3D11_BLEND_INV_SRC_ALPHA = 6
D3D11_BLEND_OP_ADD = 1
D3D11_COLOR_WRITE_ENABLE_ALL = 0x0F
D3D11_FILL_SOLID = 3
D3D11_CULL_NONE = 1
D3D11_QUERY_TIMESTAMP = 2
D3D11_QUERY_TIMESTAMP_DISJOINT = 3
D3D11_ASYNC_GETDATA_DONOTFLUSH = 0x1
S_FALSE = 1

# ID3D11DeviceContext hereda 4 métodos de ID3D11DeviceChild además de IUnknown.
# V167 omitió esos 4 slots al invocar la vtable, causando access violations reales
# en Windows. Estos índices corresponden al orden oficial de d3d11.h.
CTX_VS_SET_CONSTANT_BUFFERS = 7
CTX_PS_SET_SHADER_RESOURCES = 8
CTX_PS_SET_SHADER = 9
CTX_PS_SET_SAMPLERS = 10
CTX_VS_SET_SHADER = 11
CTX_DRAW_INDEXED = 12
CTX_PS_SET_CONSTANT_BUFFERS = 16
CTX_IA_SET_INPUT_LAYOUT = 17
CTX_IA_SET_VERTEX_BUFFERS = 18
CTX_IA_SET_INDEX_BUFFER = 19
CTX_DRAW_INDEXED_INSTANCED = 20
CTX_IA_SET_PRIMITIVE_TOPOLOGY = 24
CTX_BEGIN = 27
CTX_END = 28
CTX_GET_DATA = 29
CTX_OM_SET_RENDER_TARGETS = 33
CTX_OM_SET_DEPTH_STENCIL_STATE = 36
CTX_OM_SET_BLEND_STATE = 35
CTX_RS_SET_STATE = 43
CTX_RS_SET_VIEWPORTS = 44
CTX_UPDATE_SUBRESOURCE = 48
CTX_CLEAR_RENDER_TARGET_VIEW = 50
CTX_CLEAR_DEPTH_STENCIL_VIEW = 53

WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_SETCURSOR = 0x0020
HTCLIENT = 1
WM_KEYDOWN = 0x0100
VK_ESCAPE = 0x1B
WS_POPUP = 0x80000000
PM_REMOVE = 0x0001
SW_SHOW = 5
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_VISIBLE = 0x10000000


class GUID(ctypes.Structure):
    _fields_ = [('Data1', ctypes.c_uint32), ('Data2', ctypes.c_uint16), ('Data3', ctypes.c_uint16), ('Data4', ctypes.c_ubyte * 8)]

    @classmethod
    def from_parts(cls, d1, d2, d3, *d4):
        return cls(d1, d2, d3, (ctypes.c_ubyte * 8)(*d4))


IID_ID3D11Texture2D = GUID.from_parts(0x6f15aaf2, 0xd208, 0x4e89, 0x9a,0xb4,0x48,0x95,0x35,0xd3,0x4f,0x9c)
IID_IDXGIDevice = GUID.from_parts(0x54ec77fa, 0x1377, 0x44e6, 0x8c,0x32,0x88,0xfd,0x5f,0x44,0xc8,0x4c)
IID_IDXGIFactory1 = GUID.from_parts(0x770aae78, 0xf26f, 0x4dba, 0xa8,0x29,0x25,0x3c,0x83,0xd1,0xb3,0x87)
IID_IDXGIFactory6 = GUID.from_parts(0xc1b6694f, 0xff09, 0x44a9, 0xb0,0x3c,0x77,0x90,0x0a,0x0a,0x1d,0x17)
IID_IDXGIAdapter1 = GUID.from_parts(0x29038f61, 0x3839, 0x4626, 0x91,0xfd,0x08,0x68,0x79,0x01,0x1a,0x05)

# Índices de vtable según dxgi.h / dxgi1_6.h (IUnknown 0-2, IDXGIObject 3-6).
FACTORY1_ENUM_ADAPTERS1 = 12
FACTORY6_ENUM_ADAPTER_BY_GPU_PREFERENCE = 29
ADAPTER1_GET_DESC1 = 10
DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE = 2
DXGI_ADAPTER_FLAG_SOFTWARE = 2
DXGI_ERROR_NOT_FOUND = 0x887A0002
D3D_DRIVER_TYPE_UNKNOWN = 0
MICROSOFT_VENDOR_ID = 0x1414


class DXGI_RATIONAL(ctypes.Structure):
    _fields_ = [('Numerator', UINT), ('Denominator', UINT)]


class DXGI_MODE_DESC(ctypes.Structure):
    _fields_ = [('Width', UINT), ('Height', UINT), ('RefreshRate', DXGI_RATIONAL), ('Format', UINT), ('ScanlineOrdering', UINT), ('Scaling', UINT)]


class DXGI_SAMPLE_DESC(ctypes.Structure):
    _fields_ = [('Count', UINT), ('Quality', UINT)]


class DXGI_SWAP_CHAIN_DESC(ctypes.Structure):
    _fields_ = [
        ('BufferDesc', DXGI_MODE_DESC), ('SampleDesc', DXGI_SAMPLE_DESC), ('BufferUsage', UINT),
        ('BufferCount', UINT), ('OutputWindow', HWND_T), ('Windowed', BOOL),
        ('SwapEffect', UINT), ('Flags', UINT),
    ]


class D3D11_BUFFER_DESC(ctypes.Structure):
    _fields_ = [('ByteWidth', UINT), ('Usage', UINT), ('BindFlags', UINT), ('CPUAccessFlags', UINT), ('MiscFlags', UINT), ('StructureByteStride', UINT)]


class D3D11_SUBRESOURCE_DATA(ctypes.Structure):
    _fields_ = [('pSysMem', LPVOID), ('SysMemPitch', UINT), ('SysMemSlicePitch', UINT)]


class D3D11_TEXTURE2D_DESC(ctypes.Structure):
    _fields_ = [
        ('Width', UINT), ('Height', UINT), ('MipLevels', UINT), ('ArraySize', UINT), ('Format', UINT),
        ('SampleDesc', DXGI_SAMPLE_DESC), ('Usage', UINT), ('BindFlags', UINT), ('CPUAccessFlags', UINT), ('MiscFlags', UINT),
    ]


class D3D11_DEPTH_STENCIL_VIEW_DESC(ctypes.Structure):
    _fields_ = [('Format', UINT), ('ViewDimension', UINT), ('Flags', UINT), ('MipSlice', UINT), ('_union_pad', UINT * 2)]


class D3D11_SHADER_RESOURCE_VIEW_DESC(ctypes.Structure):
    _fields_ = [('Format', UINT), ('ViewDimension', UINT), ('MostDetailedMip', UINT), ('MipLevels', UINT), ('_union_pad', UINT * 2)]


class D3D11_INPUT_ELEMENT_DESC(ctypes.Structure):
    _fields_ = [
        ('SemanticName', ctypes.c_char_p), ('SemanticIndex', UINT), ('Format', UINT), ('InputSlot', UINT),
        ('AlignedByteOffset', UINT), ('InputSlotClass', UINT), ('InstanceDataStepRate', UINT),
    ]


class D3D11_VIEWPORT(ctypes.Structure):
    _fields_ = [('TopLeftX', FLOAT), ('TopLeftY', FLOAT), ('Width', FLOAT), ('Height', FLOAT), ('MinDepth', FLOAT), ('MaxDepth', FLOAT)]


class D3D11_SAMPLER_DESC(ctypes.Structure):
    _fields_ = [
        ('Filter', UINT), ('AddressU', UINT), ('AddressV', UINT), ('AddressW', UINT), ('MipLODBias', FLOAT),
        ('MaxAnisotropy', UINT), ('ComparisonFunc', UINT), ('BorderColor', FLOAT * 4), ('MinLOD', FLOAT), ('MaxLOD', FLOAT),
    ]


class D3D11_RENDER_TARGET_BLEND_DESC(ctypes.Structure):
    _fields_ = [
        ('BlendEnable', BOOL), ('SrcBlend', UINT), ('DestBlend', UINT), ('BlendOp', UINT),
        ('SrcBlendAlpha', UINT), ('DestBlendAlpha', UINT), ('BlendOpAlpha', UINT), ('RenderTargetWriteMask', ctypes.c_ubyte),
        ('_pad', ctypes.c_ubyte * 3),
    ]


class D3D11_BLEND_DESC(ctypes.Structure):
    _fields_ = [('AlphaToCoverageEnable', BOOL), ('IndependentBlendEnable', BOOL), ('RenderTarget', D3D11_RENDER_TARGET_BLEND_DESC * 8)]


class D3D11_DEPTH_STENCILOP_DESC(ctypes.Structure):
    _fields_ = [('StencilFailOp', UINT), ('StencilDepthFailOp', UINT), ('StencilPassOp', UINT), ('StencilFunc', UINT)]


class D3D11_DEPTH_STENCIL_DESC(ctypes.Structure):
    _fields_ = [
        ('DepthEnable', BOOL), ('DepthWriteMask', UINT), ('DepthFunc', UINT), ('StencilEnable', BOOL),
        ('StencilReadMask', ctypes.c_ubyte), ('StencilWriteMask', ctypes.c_ubyte), ('_pad', ctypes.c_ubyte * 2),
        ('FrontFace', D3D11_DEPTH_STENCILOP_DESC), ('BackFace', D3D11_DEPTH_STENCILOP_DESC),
    ]


class D3D11_RASTERIZER_DESC(ctypes.Structure):
    _fields_ = [
        ('FillMode', UINT), ('CullMode', UINT), ('FrontCounterClockwise', BOOL), ('DepthBias', ctypes.c_int),
        ('DepthBiasClamp', FLOAT), ('SlopeScaledDepthBias', FLOAT), ('DepthClipEnable', BOOL), ('ScissorEnable', BOOL),
        ('MultisampleEnable', BOOL), ('AntialiasedLineEnable', BOOL),
    ]


class D3D11_QUERY_DESC(ctypes.Structure):
    _fields_ = [('Query', UINT), ('MiscFlags', UINT)]


class D3D11_QUERY_DATA_TIMESTAMP_DISJOINT(ctypes.Structure):
    _fields_ = [('Frequency', ctypes.c_uint64), ('Disjoint', BOOL)]


class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ('hwnd', HWND_T), ('message', UINT), ('wParam', wintypes.WPARAM), ('lParam', wintypes.LPARAM),
        ('time', wintypes.DWORD), ('pt', POINT), ('lPrivate', wintypes.DWORD),
    ]


LRESULT = ctypes.c_ssize_t
WNDPROC = WINFUNCTYPE(LRESULT, HWND_T, UINT, wintypes.WPARAM, wintypes.LPARAM)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ('style', UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int), ('cbWndExtra', ctypes.c_int),
        ('hInstance', HINSTANCE_T), ('hIcon', HICON_T), ('hCursor', HCURSOR_T),
        ('hbrBackground', HBRUSH_T), ('lpszMenuName', wintypes.LPCWSTR), ('lpszClassName', wintypes.LPCWSTR),
    ]


class DXGI_ADAPTER_DESC(ctypes.Structure):
    _fields_ = [
        ('Description', ctypes.c_wchar * 128), ('VendorId', UINT), ('DeviceId', UINT), ('SubSysId', UINT), ('Revision', UINT),
        ('DedicatedVideoMemory', SIZE_T), ('DedicatedSystemMemory', SIZE_T), ('SharedSystemMemory', SIZE_T), ('AdapterLuidLowPart', UINT), ('AdapterLuidHighPart', ctypes.c_long),
    ]


class DXGI_ADAPTER_DESC1(ctypes.Structure):
    _fields_ = DXGI_ADAPTER_DESC._fields_ + [('Flags', UINT)]


def _hr_ok(hr) -> bool:
    return int(hr) >= 0


def enable_dpi_awareness() -> str:
    """Píxeles físicos reales: sin esto, con escalado 125 % Windows informa
    1536×864 en una pantalla 1920×1080 y la ventana se estira por DWM."""
    if os.name != 'nt':
        return 'N/A'
    try:
        user32 = ctypes.WinDLL('user32.dll')
        fn = user32.SetProcessDpiAwarenessContext
        fn.argtypes = [ctypes.c_void_p]; fn.restype = BOOL
        if fn(ctypes.c_void_p(-4)):  # PER_MONITOR_AWARE_V2
            return 'PER_MONITOR_V2'
    except (OSError, AttributeError):
        pass
    try:
        if ctypes.WinDLL('shcore.dll').SetProcessDpiAwareness(2) == 0:
            return 'PER_MONITOR'
    except (OSError, AttributeError):
        pass
    try:
        if ctypes.WinDLL('user32.dll').SetProcessDPIAware():
            return 'SYSTEM'
    except (OSError, AttributeError):
        pass
    return 'UNAWARE'


def _adapter_row(adapter, preference_rank: int) -> Optional[dict]:
    desc = DXGI_ADAPTER_DESC1()
    if not _hr_ok(_com_method(adapter, ADAPTER1_GET_DESC1, HRESULT, ctypes.POINTER(DXGI_ADAPTER_DESC1))(adapter, ctypes.byref(desc))):
        return None
    software = bool(desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) or desc.VendorId == MICROSOFT_VENDOR_ID
    return {
        'name': str(desc.Description).strip() or 'Adaptador DXGI',
        'vendor_id': f'0x{int(desc.VendorId):04X}',
        'dedicated_vram_mb': int(desc.DedicatedVideoMemory // (1024 * 1024)),
        'software': software,
        'preference_rank': preference_rank,
    }


def select_high_performance_adapter():
    """Elige la GPU de alto rendimiento como hacen los juegos en equipos híbridos.

    Notebook Intel/AMD + NVIDIA/AMD: ``adapter=None`` usa la GPU predeterminada
    de Windows, que muchas veces es la integrada. DXGI 1.6 ordena por
    preferencia de rendimiento; en Windows sin DXGI 1.6 se usa la de mayor VRAM
    dedicada. Los adaptadores por software (WARP/Basic Render) nunca se eligen.
    Devuelve (adapter_ptr | None, info). El llamador libera el puntero.
    """
    info = {'selection': 'WINDOWS_DEFAULT', 'adapters': [], 'reason': None}
    if os.name != 'nt':
        return None, info
    factory = ctypes.c_void_p()
    try:
        dxgi = ctypes.WinDLL('dxgi.dll')
        create = dxgi.CreateDXGIFactory1
        create.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]; create.restype = HRESULT
        if not _hr_ok(create(ctypes.byref(IID_IDXGIFactory1), ctypes.byref(factory))) or not factory.value:
            info['reason'] = 'CreateDXGIFactory1 no disponible'
            return None, info
    except (OSError, AttributeError) as exc:
        info['reason'] = f'DXGI no disponible: {exc}'
        return None, info
    candidates = []  # (adapter, row)
    try:
        factory6 = _query_interface(factory, IID_IDXGIFactory6)
        if factory6:
            info['selection'] = 'DXGI6_HIGH_PERFORMANCE'
            enum = _com_method(factory6, FACTORY6_ENUM_ADAPTER_BY_GPU_PREFERENCE, HRESULT, UINT, UINT, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))
            try:
                for index in range(16):
                    adapter = ctypes.c_void_p()
                    hr = enum(factory6, index, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, ctypes.byref(IID_IDXGIAdapter1), ctypes.byref(adapter))
                    if not _hr_ok(hr) or not adapter.value:
                        break
                    row = _adapter_row(adapter, index)
                    if row is None:
                        _release(adapter); continue
                    candidates.append((adapter, row))
            finally:
                _release(factory6)
        else:
            info['selection'] = 'MAX_DEDICATED_VRAM'
            enum = _com_method(factory, FACTORY1_ENUM_ADAPTERS1, HRESULT, UINT, ctypes.POINTER(ctypes.c_void_p))
            for index in range(16):
                adapter = ctypes.c_void_p()
                hr = enum(factory, index, ctypes.byref(adapter))
                if not _hr_ok(hr) or not adapter.value:
                    break
                row = _adapter_row(adapter, index)
                if row is None:
                    _release(adapter); continue
                candidates.append((adapter, row))
            candidates.sort(key=lambda item: -item[1]['dedicated_vram_mb'])
            for rank, (_adapter, row) in enumerate(candidates):
                row['preference_rank'] = rank
        info['adapters'] = [row for _adapter, row in candidates]
        chosen = next(((adapter, row) for adapter, row in candidates if not row['software']), None)
        for adapter, _row in candidates:
            if chosen is None or adapter is not chosen[0]:
                _release(adapter)
        if chosen is None:
            info['selection'] = 'WINDOWS_DEFAULT'
            info['reason'] = 'Sin adaptador de hardware enumerado; Direct3D elige el predeterminado'
            return None, info
        info['chosen'] = chosen[1]['name']
        return chosen[0], info
    except Exception as exc:
        for adapter, _row in candidates:
            _release(adapter)
        info['selection'] = 'WINDOWS_DEFAULT'; info['reason'] = f'{type(exc).__name__}: {exc}'
        return None, info
    finally:
        _release(factory)


# V27: crear un prototipo WINFUNCTYPE por llamada costaba ~70 construcciones por
# frame y convertía a Python en el límite con GPUs rápidas de torre. Prototipos y
# funciones enlazadas se reutilizan; la dirección se sigue leyendo de la vtable.
_COM_PROTOTYPES: dict = {}
_COM_BOUND: dict = {}


def _com_method(ptr, index: int, restype, *argtypes):
    if not ptr:
        raise RuntimeError('COM pointer nulo')
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    address = vtbl[index]
    if not address:
        raise RuntimeError(f'Método COM {index} no disponible')
    signature = (restype, argtypes)
    key = (address, signature)
    bound = _COM_BOUND.get(key)
    if bound is None:
        prototype = _COM_PROTOTYPES.get(signature)
        if prototype is None:
            prototype = _COM_PROTOTYPES[signature] = WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
        bound = _COM_BOUND[key] = prototype(address)
    return bound


def _release(ptr):
    if ptr:
        try:
            _com_method(ptr, 2, ctypes.c_ulong)(ptr)
        except Exception:
            pass


def _query_interface(ptr, iid: GUID):
    out = ctypes.c_void_p()
    hr = _com_method(ptr, 0, HRESULT, ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))(ptr, ctypes.byref(iid), ctypes.byref(out))
    return out if _hr_ok(hr) and out.value else None


def _blob_bytes(blob) -> bytes:
    get_ptr = _com_method(blob, 3, ctypes.c_void_p)(blob)
    get_size = _com_method(blob, 4, SIZE_T)(blob)
    return ctypes.string_at(get_ptr, int(get_size))


def _compile_shader(source: str, entry: bytes, target: bytes):
    compiler = None
    last = None
    for name in ('d3dcompiler_47.dll', 'd3dcompiler_46.dll', 'd3dcompiler_43.dll'):
        try:
            compiler = ctypes.WinDLL(name)
            break
        except Exception as exc:
            last = exc
    if compiler is None:
        raise RuntimeError(f'D3DCompiler no disponible: {last}')
    fn = compiler.D3DCompile
    fn.argtypes = [LPVOID, SIZE_T, ctypes.c_char_p, LPVOID, LPVOID, ctypes.c_char_p, ctypes.c_char_p, UINT, UINT, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
    fn.restype = HRESULT
    raw = source.encode('utf-8')
    code = ctypes.c_void_p(); errors = ctypes.c_void_p()
    buf = ctypes.create_string_buffer(raw)
    hr = fn(ctypes.cast(buf, LPVOID), len(raw), f'CorePulse{GPU_BENCHMARK_LABEL}.hlsl'.encode('ascii'), None, None, entry, target, 0x00008000, 0, ctypes.byref(code), ctypes.byref(errors))
    try:
        if not _hr_ok(hr) or not code.value:
            message = _blob_bytes(errors).decode('utf-8', 'replace') if errors.value else f'HRESULT 0x{int(hr)&0xffffffff:08X}'
            raise RuntimeError(f'Error compilando {entry.decode()}/{target.decode()}: {message}')
        return code, _blob_bytes(code)
    finally:
        if errors.value:
            _release(errors)


def _vec_sub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def _dot(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _norm(v):
    l=math.sqrt(_dot(v,v)) or 1.0
    return (v[0]/l,v[1]/l,v[2]/l)


def _mat_mul(a,b):
    return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def _look_at_lh(eye, at, up=(0.0,1.0,0.0)):
    z=_norm(_vec_sub(at,eye)); x=_norm(_cross(up,z)); y=_cross(z,x)
    return [
        [x[0], y[0], z[0], 0.0],
        [x[1], y[1], z[1], 0.0],
        [x[2], y[2], z[2], 0.0],
        [-_dot(x,eye), -_dot(y,eye), -_dot(z,eye), 1.0],
    ]


def _perspective_fov_lh(fov_y, aspect, zn, zf):
    y=1.0/math.tan(fov_y/2.0); x=y/aspect
    return [[x,0,0,0],[0,y,0,0],[0,0,zf/(zf-zn),1.0],[0,0,-zn*zf/(zf-zn),0]]


def _ortho_lh(width, height, zn, zf):
    return [[2.0/width,0,0,0],[0,2.0/height,0,0],[0,0,1.0/(zf-zn),0],[0,0,-zn/(zf-zn),1.0]]


def _light_viewproj():
    """Proyección ortográfica de la luna sobre el centro de la ciudad.

    Cubre ±450 unidades alrededor del centro (el bulevar de la cámara está a
    173): 4096² texels dejan ~0,22 unidades por texel. Más lejos la niebla
    nocturna domina y no se proyectan sombras.
    """
    key=_norm(KEY_LIGHT_DIRECTION)
    center=(0.0,40.0,0.0)
    eye=(center[0]+key[0]*800.0,center[1]+key[1]*800.0,center[2]+key[2]*800.0)
    return _mat_mul(_look_at_lh(eye,center),_ortho_lh(900.0,900.0,1.0,1700.0))


def _reflect_y():
    """Espejo respecto del plano del suelo (y=0) en convención fila-vector."""
    return [[1.0,0,0,0],[0,-1.0,0,0],[0,0,1.0,0],[0,0,0,1.0]]


def _flatten_matrix(m):
    return [float(v) for row in m for v in row]


def _camera_at(t: float, level_index: int):
    # Recorrido por el bulevar circular definido en directx_scene (sin edificios).
    return camera_pose(t, level_index)


def _percentile(values, p):
    if not values:
        return None
    data=sorted(float(x) for x in values)
    pos=(len(data)-1)*float(p)
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return data[lo]
    return data[lo]*(hi-pos)+data[hi]*(pos-lo)


def _fps_stats(frame_times_ms):
    vals=[float(x) for x in frame_times_ms if x and x>0]
    if not vals:
        return {'frames':0,'fps':None,'one_percent_low_fps':None,'frametime_avg_ms':None,'frametime_median_ms':None,'frametime_p95_ms':None,'frametime_p99_ms':None,'frametime_spike_threshold_ms':None,'frametime_spike_frames':0,'frametime_spike_ratio':None}
    total_s=sum(vals)/1000.0
    fps=len(vals)/total_s if total_s>0 else None
    one_count=max(1,math.ceil(len(vals)*0.01))
    worst=sorted(vals, reverse=True)[:one_count]
    one_low=1000.0/(sum(worst)/len(worst)) if worst else None
    med=statistics.median(vals)
    spike_threshold=max(med*2.0,med+4.0)
    spikes=sum(1 for x in vals if x>spike_threshold)
    return {
        'frames':len(vals),'fps':fps,'one_percent_low_fps':one_low,
        'frametime_avg_ms':sum(vals)/len(vals),'frametime_median_ms':med,
        'frametime_p95_ms':_percentile(vals,0.95),'frametime_p99_ms':_percentile(vals,0.99),
        'frametime_spike_threshold_ms':spike_threshold,'frametime_spike_frames':spikes,
        'frametime_spike_ratio':spikes/len(vals),
    }


def _bottleneck(frame_avg_ms, gpu_avg_ms, coverage):
    """GPU ocupada / tiempo entre Present. <85 %: la GPU espera a CPU, Python o
    al sistema y los FPS no representan el máximo de la tarjeta."""
    if not frame_avg_ms or not gpu_avg_ms or not coverage or coverage < 0.5:
        return {'gpu_busy_ratio':None,'bottleneck':'N/A'}
    ratio=min(1.0,gpu_avg_ms/frame_avg_ms)
    return {'gpu_busy_ratio':ratio,'bottleneck':'GPU' if ratio >= 0.85 else 'CPU_O_SISTEMA'}


def _gpu_time_stats(values_ms, total_frames: int = 0, dropped: int = 0, disjoint: int = 0):
    vals=[float(x) for x in values_ms if x is not None and math.isfinite(float(x)) and float(x) > 0.0]
    if not vals:
        return {
            'gpu_samples': 0, 'gpu_sample_coverage': 0.0 if total_frames else None,
            'gpu_frame_time_avg_ms': None, 'gpu_frame_time_median_ms': None,
            'gpu_frame_time_p95_ms': None, 'gpu_frame_time_p99_ms': None,
            'gpu_frame_time_min_ms': None, 'gpu_frame_time_max_ms': None,
            'gpu_equivalent_fps': None, 'gpu_query_dropped_frames': int(dropped or 0),
            'gpu_query_disjoint_frames': int(disjoint or 0), 'gpu_sample_overflow_discarded': 0,
        }
    # Una consulta válida corresponde como máximo a un frame medido. Cualquier
    # exceso indica un bug de contabilidad y se informa, nunca se presenta >100%.
    overflow=max(0,len(vals)-max(0,int(total_frames))) if total_frames else 0
    if total_frames and len(vals)>int(total_frames):
        vals=vals[-int(total_frames):]
    avg=sum(vals)/len(vals)
    return {
        'gpu_samples': len(vals),
        'gpu_sample_coverage': min(1.0,(len(vals)/max(1,int(total_frames)))) if total_frames else None,
        'gpu_sample_overflow_discarded': overflow,
        'gpu_frame_time_avg_ms': avg,
        'gpu_frame_time_median_ms': statistics.median(vals),
        'gpu_frame_time_p95_ms': _percentile(vals,0.95),
        'gpu_frame_time_p99_ms': _percentile(vals,0.99),
        'gpu_frame_time_min_ms': min(vals),
        'gpu_frame_time_max_ms': max(vals),
        'gpu_equivalent_fps': (1000.0/avg) if avg > 0 else None,
        'gpu_query_dropped_frames': int(dropped or 0),
        'gpu_query_disjoint_frames': int(disjoint or 0),
    }


class _GpuTimerSlot:
    __slots__=('disjoint','start','end','in_use')
    def __init__(self, disjoint=None, start=None, end=None):
        self.disjoint=disjoint or ctypes.c_void_p()
        self.start=start or ctypes.c_void_p()
        self.end=end or ctypes.c_void_p()
        self.in_use=False


class _GpuFrameTimer:
    """Timestamp queries D3D11 sin serializar cada frame.

    Usa un pool pre-creado. Begin/End delimitan una consulta DISJOINT por frame;
    los timestamps se obtienen de forma no bloqueante durante la escena y se
    drenan fuera de la ventana medida. Si el pool se agota se omite sólo la
    muestra GPU de ese frame; nunca se inventa un tiempo.
    """
    def __init__(self, device, context, slot_count: int = 64):
        self.device=device; self.context=context
        self.slots=[]; self.pending=[]; self.completed=[]
        self.dropped_frames=0; self.disjoint_frames=0
        for _ in range(max(8,int(slot_count))):
            slot=_GpuTimerSlot(
                self._create_query(D3D11_QUERY_TIMESTAMP_DISJOINT),
                self._create_query(D3D11_QUERY_TIMESTAMP),
                self._create_query(D3D11_QUERY_TIMESTAMP),
            )
            self.slots.append(slot)

    def _create_query(self, query_type):
        out=ctypes.c_void_p(); desc=D3D11_QUERY_DESC(int(query_type),0)
        hr=_com_method(self.device,24,HRESULT,ctypes.POINTER(D3D11_QUERY_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(desc),ctypes.byref(out))
        if not _hr_ok(hr) or not out.value:
            raise RuntimeError(f'CreateQuery({query_type}) falló 0x{int(hr)&0xffffffff:08X}')
        return out

    def reset_scene(self):
        # Debe llamarse después de drenar la escena anterior.
        self.completed=[]; self.dropped_frames=0; self.disjoint_frames=0

    def begin_frame(self):
        # V14: nunca consulta GetData aquí. El sondeo de queries se hace fuera
        # de la ventana CPU/Present para que la propia auditoría GPU no fabrique
        # spikes ni degrade artificialmente el 1% Low.
        slot=next((x for x in self.slots if not x.in_use),None)
        if slot is None:
            self.dropped_frames += 1
            return None
        slot.in_use=True
        _com_method(self.context,CTX_BEGIN,None,ctypes.c_void_p)(self.context,slot.disjoint)
        # D3D11_QUERY_TIMESTAMP se marca sólo con End; Begin no es válido.
        _com_method(self.context,CTX_END,None,ctypes.c_void_p)(self.context,slot.start)
        return slot

    def end_frame(self, slot):
        if slot is None:
            return
        _com_method(self.context,CTX_END,None,ctypes.c_void_p)(self.context,slot.end)
        _com_method(self.context,CTX_END,None,ctypes.c_void_p)(self.context,slot.disjoint)
        self.pending.append(slot)

    def _read_one(self, slot, flags):
        info=D3D11_QUERY_DATA_TIMESTAMP_DISJOINT()
        hr=_com_method(self.context,CTX_GET_DATA,HRESULT,ctypes.c_void_p,ctypes.c_void_p,UINT,UINT)(
            self.context,slot.disjoint,ctypes.byref(info),ctypes.sizeof(info),flags)
        if int(hr)==S_FALSE:
            return None
        if not _hr_ok(hr):
            return ('invalid',None)
        start=ctypes.c_uint64(); end=ctypes.c_uint64()
        hs=_com_method(self.context,CTX_GET_DATA,HRESULT,ctypes.c_void_p,ctypes.c_void_p,UINT,UINT)(self.context,slot.start,ctypes.byref(start),ctypes.sizeof(start),flags)
        he=_com_method(self.context,CTX_GET_DATA,HRESULT,ctypes.c_void_p,ctypes.c_void_p,UINT,UINT)(self.context,slot.end,ctypes.byref(end),ctypes.sizeof(end),flags)
        if int(hs)==S_FALSE or int(he)==S_FALSE:
            return None
        if not _hr_ok(hs) or not _hr_ok(he) or bool(info.Disjoint) or not info.Frequency or end.value <= start.value:
            return ('disjoint',None)
        ms=(end.value-start.value)*1000.0/float(info.Frequency)
        return ('ok',ms) if math.isfinite(ms) and ms>0.0 else ('invalid',None)

    def collect_ready(self, nonblocking=True):
        flags=D3D11_ASYNC_GETDATA_DONOTFLUSH if nonblocking else 0
        fresh=[]
        # GPU completa las consultas en orden; detenerse en la primera pendiente
        # evita sondear inútilmente todas las posteriores.
        while self.pending:
            slot=self.pending[0]
            got=self._read_one(slot,flags)
            if got is None:
                break
            self.pending.pop(0); slot.in_use=False
            state,value=got
            if state=='ok':
                self.completed.append(value); fresh.append(value)
            elif state=='disjoint':
                self.disjoint_frames += 1
        return fresh

    def drain(self, timeout_s: float = 4.0):
        deadline=time.perf_counter()+max(0.1,float(timeout_s))
        while self.pending and time.perf_counter()<deadline:
            before=len(self.pending)
            self.collect_ready(nonblocking=False)
            if len(self.pending)==before:
                time.sleep(0.001)
        if self.pending:
            self.dropped_frames += len(self.pending)
            for slot in self.pending:
                slot.in_use=False
            self.pending.clear()
        return list(self.completed)

    def close(self):
        for slot in self.slots:
            _release(slot.end); _release(slot.start); _release(slot.disjoint)
            slot.in_use=False
        self.pending.clear(); self.completed.clear(); self.slots.clear()




HLSL = r'''
cbuffer SceneCB : register(b0)
{
    row_major float4x4 ViewProj;
    float4 CameraTime;      // xyz cámara, w tiempo
    float4 SceneParams;     // x tipo de objeto, y alcance de faroles dibujados, z iteraciones ALU, w muestras de textura
    float4 SceneParams2;    // x ancho, y alto, z pasada (0 escena, 1 sombras, 2 reflejo), w bruma del nivel 0..1
    row_major float4x4 LightViewProj;
    float4 KeyLight;        // xyz hacia la luna (unitario), w intensidad
    float4 Extra;           // x escala de UV del reflejo (1/divisor del nivel), y pasos volumétricos
};
Texture2D NoiseTex : register(t0);
Texture2D<float> ShadowMap : register(t1);
Texture2D ReflTex : register(t2);
SamplerState LinearWrap : register(s0);
SamplerComparisonState ShadowCmp : register(s1);
SamplerState LinearClamp : register(s2);

// V29: ciudad nocturna. Debe coincidir con CITY de core/directx_scene.py (test_073).
static const float PITCH = 76.0;
static const float ROAD = 16.0;
static const float CITY_EXTENT = 722.0;
static const float RING_R = 173.0;
static const float RING_HW = 23.0;
static const float LAMP_EDGE = 6.8;
static const float LAMP_SPACING = 19.0;
static const float LAMP_H = 9.0;
static const float SHADOW_TEXEL = 1.0 / 4096.0;
static const float TAU = 6.2831853;
static const float3 MOON_COLOR = float3(0.62, 0.74, 1.00);

struct VSIn { float3 pos:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; float4 ia:INSTA; float4 ib:INSTB; uint iid:SV_InstanceID; };
struct VSOut { float4 pos:SV_POSITION; float3 world:TEXCOORD0; float3 normal:TEXCOORD1; float2 uv:TEXCOORD2;
               nointerpolation float4 ia:TEXCOORD3; nointerpolation float4 ib:TEXCOORD4; };

float hash11(float n) { return frac(sin(n*12.9898)*43758.5453); }
float hash12(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7)))*43758.5453); }
float3 rotateX(float3 p,float a){ float s=sin(a),c=cos(a); return float3(p.x,p.y*c-p.z*s,p.y*s+p.z*c); }
float3 rotateY(float3 p,float a){ float s=sin(a),c=cos(a); return float3(p.x*c-p.z*s,p.y,p.x*s+p.z*c); }

float3 neonColor(float k)
{
    float s = frac(k * 5.0);
    if (s < 0.2) return float3(1.00, 0.10, 0.62);   // magenta
    if (s < 0.4) return float3(0.05, 0.85, 1.00);   // cian
    if (s < 0.6) return float3(1.00, 0.55, 0.08);   // ámbar
    if (s < 0.8) return float3(0.55, 0.20, 1.00);   // violeta
    return float3(0.30, 1.00, 0.45);                 // verde ácido
}

float3 nightSky(float3 d, bool stars)
{
    float h = saturate(d.y);
    float3 zenith = float3(0.004, 0.008, 0.026);
    float3 horizon = float3(0.15, 0.06, 0.13);           // contaminación lumínica magenta
    float3 col = lerp(horizon, zenith, pow(h, 0.35));
    col += float3(0.22, 0.10, 0.035) * pow(1.0 - h, 10.0);  // resplandor anaranjado de la ciudad
    if (stars && d.y > 0.03) {
        float3 g = floor(d * 260.0);
        float s = hash12(g.xz + g.y * 17.31);
        float2 f = frac(d.xz * 260.0) - 0.5;
        col += step(0.9965, s) * smoothstep(0.32, 0.0, length(f)) * float3(0.9, 0.95, 1.0) * 1.6 * smoothstep(0.03, 0.35, d.y);
    }
    float mu = dot(d, KeyLight.xyz);
    col += smoothstep(0.99935, 0.99962, mu) * float3(6.0, 6.4, 7.0);               // disco lunar HDR
    col += MOON_COLOR * (pow(saturate(mu), 300.0) * 0.55 + pow(saturate(mu), 24.0) * 0.05);
    return col;
}

float keyShadow(float3 world, float3 N)
{
    float4 ls = mul(float4(world + N * 0.45, 1.0), LightViewProj);
    float2 suv = ls.xy * float2(0.5, -0.5) + 0.5;
    if (any(suv < 0.0) || any(suv > 1.0) || ls.z > 1.0) return 1.0;
    float z = ls.z - 0.0008; float s = 0.0;
    [unroll] for (int y = -1; y <= 1; y++)
        [unroll] for (int x = -1; x <= 1; x++)
            s += ShadowMap.SampleCmpLevelZero(ShadowCmp, suv + float2(x, y) * SHADOW_TEXEL * 1.5, z);
    return s / 9.0;
}

float3 ambientNight(float3 N)
{
    // Cielo nocturno arriba, rebote cálido de las calles iluminadas abajo.
    return lerp(float3(0.030, 0.022, 0.020), float3(0.020, 0.026, 0.050), N.y * 0.5 + 0.5);
}

float3 keyShade(float3 albedo, float3 N, float shadow, float ao)
{
    return albedo * (MOON_COLOR * KeyLight.w * saturate(dot(N, KeyLight.xyz)) * shadow + ambientNight(N) * ao);
}

float3 lampAt(float3 w, float2 lp, float3 tint)
{
    float3 d = float3(lp.x, LAMP_H - 0.4, lp.y) - w;
    float dd = dot(d, d);
    float cone = saturate(d.y * rsqrt(dd + 1e-4));
    return tint * cone * cone * 42.0 / (dd + 9.0);
}

// Luz de los faroles sobre el suelo y el vapor. Repite la ubicación de
// city_layout(): hileras a 6,8 del eje de cada calle cada 19 unidades, sin
// cruces ni bulevar; el bulevar tiene dos hileras propias cada 16 de arco.
float3 lampLight(float3 w)
{
    float2 p = w.xz; float r = length(p);
    float cover = SceneParams.y;
    float band = abs(r - RING_R);
    if (band > cover + 30.0 || abs(p.x) > CITY_EXTENT + 12.0 || abs(p.y) > CITY_EXTENT + 12.0) return 0;
    float3 tint = float3(1.00, 0.70, 0.40);
    float3 acc = 0;
    if (band < RING_HW + 6.0) {
        float th = atan2(p.y, p.x);
        [unroll] for (int e = 0; e < 2; e++) {
            float re = e == 0 ? RING_R - RING_HW + 1.2 : RING_R + RING_HW - 1.2;
            float n = floor(TAU * re / 16.0); float stp = TAU / n;
            float k = round(th / stp);
            [unroll] for (int j = -1; j <= 1; j++) {
                float a = (k + j) * stp;
                acc += lampAt(w, re * float2(cos(a), sin(a)), tint);
            }
        }
    } else {
        [unroll] for (int axis = 0; axis < 2; axis++) {
            float across = axis == 0 ? p.x : p.y;
            float along = axis == 0 ? p.y : p.x;
            float rc = (round(across / PITCH - 0.5) + 0.5) * PITCH;
            float a0 = -CITY_EXTENT + round((along + CITY_EXTENT) / LAMP_SPACING) * LAMP_SPACING;
            [unroll] for (int side = -1; side <= 1; side += 2) {
                [unroll] for (int j = -1; j <= 1; j++) {
                    float al = a0 + j * LAMP_SPACING;
                    if (abs(frac(al / PITCH) - 0.5) * PITCH < ROAD * 0.5 + 1.0) continue;   // cruce
                    float2 lp = axis == 0 ? float2(rc + side * LAMP_EDGE, al) : float2(al, rc + side * LAMP_EDGE);
                    float lr = length(lp);
                    if (lr > RING_R - RING_HW - 2.0 && lr < RING_R + RING_HW + 2.0) continue;
                    acc += lampAt(w, lp, tint);
                }
            }
        }
    }
    return acc * (1.0 - smoothstep(cover, cover + 30.0, band));
}

// Luz volumétrica: marcha desde la cámara por el rayo de vista y acumula la
// luz de luna dispersada por la bruma donde el mapa de sombras dice que hay
// luna (haces entre torres). Pasos por nivel en Extra.y; ruido de píxel para
// repartir el muestreo sin bandas.
float3 moonShafts(float3 dir, float dist, float2 pix)
{
    float steps = Extra.y;
    if (steps < 0.5 || SceneParams2.z > 0.5) return 0;
    float maxD = min(dist, 650.0);
    float dt = maxD / steps;
    float jitter = frac(52.9829189 * frac(dot(pix, float2(0.06711056, 0.00583715))));
    float acc = 0.0;
    [loop] for (float k = 0.0; k < steps; k += 1.0) {
        float3 pos = CameraTime.xyz + dir * ((k + jitter) * dt);
        float4 ls = mul(float4(pos, 1.0), LightViewProj);
        float2 suv = ls.xy * float2(0.5, -0.5) + 0.5;
        float vis = (any(suv < 0.0) || any(suv > 1.0)) ? 1.0 : ShadowMap.SampleCmpLevelZero(ShadowCmp, suv, ls.z - 0.001);
        acc += vis * exp(-max(pos.y, 0.0) * 0.006);
    }
    acc *= dt;
    float mu = dot(dir, KeyLight.xyz); float g = 0.55;
    float phase = (1.0 - g * g) / pow(abs(1.0 + g * g - 2.0 * g * mu), 1.5) * 0.08;
    return MOON_COLOR * KeyLight.w * acc * 0.0011 * (0.12 + phase * 1.6) * (0.7 + SceneParams2.w * 0.6);
}

float3 atmosphere(float3 col, float3 world, float2 pix)
{
    float3 d = world - CameraTime.xyz; float dist = length(d); d /= max(dist, 1e-3);
    float haze = SceneParams2.w;
    float ext = 1.0 - exp(-max(dist - 60.0, 0.0) * (0.0011 + 0.0012 * haze));
    float low = exp(-max(world.y, 0.0) * 0.010);
    float f = saturate(ext * (0.45 + 0.55 * low));
    float3 fogc = nightSky(float3(d.x, 0.04, d.z), false) * 1.15 + float3(0.035, 0.012, 0.03);
    return lerp(col, fogc, f) + moonShafts(d, dist, pix);
}

VSOut VSMain(VSIn i)
{
    VSOut o; float3 p=i.pos; float3 n=i.normal; float type=SceneParams.x; float t=CameraTime.w;
    float4 a=i.ia, b=i.ib;
    if(type > 3.5 && type < 4.5) {          // edificios: torre unitaria escalada por instancia
        p=float3(p.x*a.z, p.y*a.w, p.z*b.x)+float3(a.x,0.0,a.y);
        n=normalize(n/float3(a.z,1.0,b.x));
    } else if(type > 4.5 && type < 5.5) {   // faroles
        p=rotateY(p,a.z)+float3(a.x,0.0,a.y); n=rotateY(n,a.z);
    } else if(type > 1.5 && type < 2.5) {   // vehículos voladores por carriles
        float3 c; float2 dir; float bank=0.0;
        if(a.x < 0.5) {
            float th=b.x*TAU + a.w*t;
            c=float3(a.y*cos(th), a.z, a.y*sin(th));
            dir=float2(-sin(th), cos(th))*sign(a.w); bank=-0.10*sign(a.w);
        } else {
            float s=-CITY_EXTENT+frac(b.x + t*a.w/(2.0*CITY_EXTENT))*2.0*CITY_EXTENT;
            if(a.x < 1.5) { c=float3(a.y,a.z,s); dir=float2(0.0,sign(a.w)); }
            else { c=float3(s,a.z,a.y); dir=float2(sign(a.w),0.0); }
        }
        c.y += sin(t*0.9+b.x*17.0)*0.35;
        float yaw=atan2(dir.y,dir.x);
        p=rotateY(rotateX(p*b.z,bank),yaw)+c; n=rotateY(rotateX(n,bank),yaw);
    } else if(type > 2.5 && type < 3.5) {   // nubes bajas sobre la ciudad
        float drift=t*1.4;
        p=p*float3(a.w*1.6,a.w*0.55,a.w)+float3(a.x+drift,a.y,a.z+drift*0.4);
    } else if(type > 7.5 && type < 8.5) {   // vapor de alcantarillas
        float rise=t*0.9+a.z*7.0;
        float swirl=sin(rise*0.82+i.uv.y*5.1+i.pos.x*0.45)*0.55;
        p=float3(i.pos.x*0.9+swirl*0.3, i.pos.y*0.85+frac(rise)*1.6, i.pos.z*0.9)+float3(a.x,0.15,a.y);
        n=float3(0.0,1.0,0.0);
    } else if(type > 5.5 && type < 6.5) {   // cielo centrado en la cámara
        p=CameraTime.xyz+p*1400.0; n=normalize(p-CameraTime.xyz);
    }
    o.world=p; o.normal=normalize(n); o.uv=i.uv; o.ia=a; o.ib=b;
    o.pos=mul(float4(p,1.0),ViewProj);
    if(type > 5.5 && type < 6.5) o.pos.z=o.pos.w*0.99999;   // el cielo siempre queda al fondo
    return o;
}

float3 shadeBuilding(VSOut i, float3 N, float3 V, float noise)
{
    float4 a=i.ia, b=i.ib; float style=b.y; float seed=b.z; float H=a.w; float t=CameraTime.w;
    float sh=keyShadow(i.world,N);
    float3 neon=neonColor(seed);
    if(i.uv.y > 1.5) {                       // techo
        float2 q=float2(i.uv.x-0.5, i.uv.y-2.5);
        float3 c=keyShade(float3(0.05,0.05,0.055),N,sh,1.0);
        float edge=0.5-max(abs(q.x),abs(q.y));
        if(style > 1.5 && style < 2.5) c+=neon*6.0*(1.0-smoothstep(0.0,0.035,edge));
        float beacon=(H > 120.0)*(1.0-smoothstep(0.03,0.07,length(q)))*step(0.55,sin(t*3.1+seed*20.0));
        return c+float3(1.0,0.06,0.03)*40.0*beacon;
    }
    float y=i.world.y;
    bool sideX=abs(N.x) > abs(N.z);
    float faceW=sideX ? b.x : a.z;
    float along=(sideX ? i.world.z-a.y : i.world.x-a.x) + faceW*0.5;
    float3 R=reflect(-V,N);
    float fres=0.04+0.96*pow(1.0-saturate(dot(N,V)),5.0);
    float3 glassRefl=nightSky(float3(R.x,abs(R.y)+0.02,R.z),false)*fres*1.6;
    if(i.uv.x > 2.5) {                       // chaflanes: franjas de neón o perfil metálico
        float3 c=keyShade(float3(0.06,0.06,0.07),N,sh,1.0)+glassRefl;
        if(style > 1.5 && style < 2.5) c+=neon*(5.0+3.0*sin(y*0.12-t*2.2+seed*30.0));
        return c;
    }
    float floorH=(style > 0.5 && style < 1.5) ? 3.6 : 3.2;
    float colW=(style < 0.5) ? 1.8 : 2.6;
    float2 g=float2(along/colW, y/floorH);
    float2 cell=floor(g), f=frac(g);
    float2 fw=fwidth(g)*1.2+1e-3;
    float wx=smoothstep(0.10,0.10+fw.x,f.x)*smoothstep(0.90,0.90-fw.x,f.x);
    float wy=smoothstep(0.16,0.16+fw.y,f.y)*smoothstep(0.84,0.84-fw.y,f.y);
    float inside=step(4.5,y)*step(y,H-1.0);
    float win=wx*wy*inside;
    // Identificador de cara redondeado: la normal interpolada varía en los últimos
    // decimales por píxel y el hash los amplifica (era la «estática» en ventanas).
    float2 face=round(float2(N.x,N.z));
    float rnd=hash12(cell+seed*97.0+face*float2(13.0,29.0));
    // Pisos de oficinas: algunos casi enteros encendidos, la mayoría a oscuras.
    float floorOn=hash12(float2(cell.y,seed*53.0+face.x*7.0+face.y*3.0));
    float density=lerp(0.08,0.38,frac(seed*7.3))*(floorOn > 0.78 ? 2.4 : (floorOn > 0.35 ? 1.0 : 0.25));
    float lit=step(rnd,density);
    // Unas pocas ventanas se encienden o apagan con el tiempo.
    if(frac(rnd*17.0+floor(t*0.15+rnd*9.0)*0.37) < 0.025) lit=1.0-lit;
    float tone=frac(rnd*31.7);
    float3 wcol=tone < 0.5 ? float3(1.0,0.72,0.42) : (tone < 0.8 ? float3(0.95,0.93,0.88) : float3(0.62,0.80,1.0));
    float3 emissive=wcol*lit*win*lerp(0.45,1.35,frac(rnd*53.1));
    // Lejos, la grilla de ventanas es más chica que un píxel: se reemplaza por
    // su brillo promedio para que no titile (antialiasing de la fachada).
    // fw = ventanas por píxel. Desde ~1/4 de ventana por píxel (lejos o de
    // costado) la grilla titila: se pasa gradualmente al promedio.
    float far=smoothstep(0.22,0.55,max(fw.x,fw.y));
    emissive=lerp(emissive,float3(0.95,0.78,0.55)*saturate(density)*0.85*0.42*inside,far);
    win=lerp(win,0.42*inside,far);
    float3 wall=(style > 0.5 && style < 1.5) ? float3(0.075,0.066,0.058) : float3(0.040,0.044,0.052);
    wall*=lerp(0.85,1.15,noise);
    float3 c=keyShade(wall,N,sh,lerp(0.55,1.0,saturate(y/12.0)))*(1.0-win*0.7);
    c+=glassRefl*lerp(0.35,1.0,win)+emissive;
    if(style > 1.5 && style < 2.5) {         // bandas de neón horizontales cada 8 pisos
        float band=frac(y/(floorH*8.0));
        c+=neon*4.0*(1.0-smoothstep(0.0,0.012,abs(band-0.5)))*(H > 40.0);
    }
    if(style > 2.5 && faceW > 12.0) {        // pantalla publicitaria animada
        float y0=H*0.42; float hh=min(H*0.24,26.0);
        float2 q=float2(along/faceW, (y-y0)/hh);
        if(q.y > 0.0 && q.y < 1.0 && q.x > 0.08 && q.x < 0.92) {
            float2 s=float2((q.x-0.08)/0.84, q.y);
            float3 c1=neonColor(seed+floor(t*0.25)*0.13), c2=neonColor(seed+0.5+floor(t*0.25)*0.13);
            float3 ad=lerp(c1,c2,smoothstep(0.0,1.0,s.x+0.25*sin(s.y*6.0+t*1.7)));
            ad*=0.55+0.45*step(0.5,frac(s.y*7.0-t*0.6));
            float logo=1.0-smoothstep(0.16,0.19,length((s-float2(0.5,0.55))*float2(1.0,faceW/hh*0.84)));
            ad=lerp(ad,float3(1.0,1.0,1.0),logo*(0.55+0.45*sin(t*3.0)));
            float bezel=step(0.02,s.x)*step(s.x,0.98)*step(0.04,s.y)*step(s.y,0.96);
            c=lerp(c*0.3,ad*3.2,bezel);
        }
    }
    if(y < 4.5 && frac(seed*13.7) < 0.6) {   // vidrieras del local a nivel de calle
        float shop=smoothstep(0.4,0.6,frac(along/4.0))*smoothstep(0.4,1.0,y)*(1.0-smoothstep(3.6,4.2,y));
        c+=lerp(float3(1.0,0.78,0.5),neon,0.35)*1.6*shop;
    }
    return c;
}

float3 shadeGround(VSOut i, float3 N, float3 V, float noise)
{
    float2 p=i.world.xz; float r=length(p); float t=CameraTime.w;
    bool inCity=abs(p.x) < CITY_EXTENT && abs(p.y) < CITY_EXTENT;
    float2 dr=abs(frac(p/PITCH)-0.5)*PITCH;                 // distancia al eje de calle (x, z)
    float roadA=(1.0-smoothstep(ROAD*0.5-0.2,ROAD*0.5+0.2,dr.x))*inCity;   // calle a lo largo de z
    float roadB=(1.0-smoothstep(ROAD*0.5-0.2,ROAD*0.5+0.2,dr.y))*inCity;   // calle a lo largo de x
    float ringD=abs(r-RING_R);
    float ring=1.0-smoothstep(RING_HW-0.3,RING_HW+0.3,ringD);
    float road=saturate(max(max(roadA,roadB),ring));
    float walk=(1.0-road)*(1.0-smoothstep(ROAD*0.5+2.6,ROAD*0.5+3.0,min(dr.x,dr.y)))*inCity;
    float4 n0=NoiseTex.Sample(LinearWrap,p*0.011), n1=NoiseTex.Sample(LinearWrap,p*0.071+0.37);
    float3 asphalt=float3(0.024,0.024,0.027)*lerp(0.75,1.3,n1.r*0.6+noise*0.4);
    float3 slab=float3(0.075,0.072,0.07)*lerp(0.85,1.1,n1.g);
    slab*=lerp(0.8,1.0,step(0.06,frac(p.x/2.0))*step(0.06,frac(p.y/2.0)));
    float3 albedo=lerp(lerp(float3(0.03,0.03,0.032),slab,walk),asphalt,road);
    // Señalización: líneas discontinuas, doble línea del bulevar y pasos peatonales.
    float paint=0.0;
    paint=max(paint,roadA*(1.0-roadB)*(1.0-ring)*step(dr.x,0.12)*step(0.5,frac(p.y/6.0)));
    paint=max(paint,roadB*(1.0-roadA)*(1.0-ring)*step(dr.y,0.12)*step(0.5,frac(p.x/6.0)));
    paint=max(paint,ring*step(abs(ringD-0.35),0.12));
    paint=max(paint,ring*step(abs(ringD-11.5),0.12)*step(0.5,frac(atan2(p.y,p.x)*RING_R/6.0)));
    float zebraA=roadA*step(ROAD*0.5+0.6,dr.y)*step(dr.y,ROAD*0.5+3.4)*step(0.5,frac(p.x/1.4));
    float zebraB=roadB*step(ROAD*0.5+0.6,dr.x)*step(dr.x,ROAD*0.5+3.4)*step(0.5,frac(p.y/1.4));
    paint=max(paint,max(zebraA,zebraB)*(1.0-ring));
    albedo=lerp(albedo,float3(0.55,0.53,0.48),paint*0.85);
    // Agua: charcos espejados y asfalto mojado.
    float puddle=smoothstep(0.56,0.64,n0.r*0.65+n1.b*0.35);
    float wet=road > 0.5 ? lerp(0.45,1.0,puddle) : 0.25+puddle*0.5;
    float sh=keyShadow(i.world,N);
    float3 lamps=lampLight(i.world);
    float3 c=albedo*(MOON_COLOR*KeyLight.w*saturate(dot(N,KeyLight.xyz))*sh+ambientNight(N)+lamps);
    if(SceneParams2.z < 0.5) {
        float2 suv=i.pos.xy/SceneParams2.xy*Extra.x;
        float2 ripple=(NoiseTex.Sample(LinearWrap,p*0.035+float2(t*0.006,-t*0.004)).rg-0.5)*0.0016*(1.0-puddle*0.85);
        float3 refl=0;
        // Reflejo estirado en vertical sobre asfalto mojado; nítido en charcos.
        [unroll] for(int k=0;k<4;k++) refl+=ReflTex.Sample(LinearClamp,suv+ripple+float2(0.0,(k-1.5)*0.004*(1.0-puddle))).rgb;
        refl*=0.25;
        float fres=0.04+0.96*pow(1.0-saturate(dot(N,V)),5.0);
        float rw=wet*lerp(0.22,0.85,fres)*lerp(0.45,0.92,puddle);
        c=c*(1.0-rw*0.6)+refl*rw;
    }
    c+=lamps*paint*0.08;
    return c;
}

float3 shadeVehicle(VSOut i, float3 N, float3 V)
{
    if(i.uv.y > 1.5)
        return i.uv.x < 0.5 ? float3(1.0,0.95,0.88)*26.0 : float3(1.0,0.04,0.03)*16.0;
    float k=i.ib.y;
    float3 paint=k < 0.5 ? float3(0.02,0.02,0.025) : (k < 1.5 ? float3(0.55,0.56,0.6) : (k < 2.5 ? float3(0.35,0.02,0.03) : float3(0.02,0.25,0.30)));
    float3 R=reflect(-V,N);
    float fres=0.05+0.95*pow(1.0-saturate(dot(N,V)),5.0);
    float3 c=keyShade(paint,N,keyShadow(i.world,N),1.0)+nightSky(float3(R.x,abs(R.y)+0.02,R.z),false)*fres*1.5;
    c+=neonColor(i.ib.x)*0.9*saturate(-N.y);                 // luz de bajos
    return c;
}

float4 PSMain(VSOut i):SV_TARGET
{
    float type=SceneParams.x; int iters=(int)SceneParams.z; int texN=(int)SceneParams.w;
    float renderPass=SceneParams2.z;
    if(renderPass > 0.5 && renderPass < 1.5) return 0;   // sombras: sólo profundidad
    if(renderPass > 1.5) { iters=0; texN=min(texN,1); }   // reflejo: misma escena, menos ALU
    float3 N=normalize(i.normal);
    float3 V=normalize(CameraTime.xyz-i.world); float t=CameraTime.w;
    float noise=0.0;
    [loop] for(int s=0;s<texN;s++){ float f=1.0+(float)s*0.63; noise+=NoiseTex.Sample(LinearWrap,i.uv*f+i.world.xz*0.003+float2(t*0.002*s,-t*0.0015*s)).r; }
    noise/=max(1,texN);
    float alu=noise;
    [loop] for(int k=0;k<iters;k++){ alu=frac(sin(alu*7.31+(float)k*0.17+i.world.x*0.002)*437.1); }
    float3 col; float alpha=1.0;
    if(type > 5.5 && type < 6.5) {
        float3 sd=normalize(i.world-CameraTime.xyz);
        return float4(nightSky(sd,true)+moonShafts(sd,650.0,i.pos.xy),1.0);
    } else if(type < 0.5) {
        col=shadeGround(i,N,V,noise);
    } else if(type < 2.5) {
        col=shadeVehicle(i,N,V);
    } else if(type < 3.5) {                   // nubes iluminadas desde abajo por la ciudad
        float2 cq=i.uv*2.0-1.0;
        float radial=saturate(1.0-dot(cq*float2(0.92,1.08),cq*float2(0.92,1.08)));
        float4 cn0=NoiseTex.Sample(LinearWrap,i.uv*1.7+i.world.xz*0.0018);
        float4 cn1=NoiseTex.Sample(LinearWrap,i.uv*4.1+float2(0.23,0.61)+t*float2(0.0007,-0.0004));
        float billow=saturate(cn0.r*0.58+cn1.g*0.42);
        float density=smoothstep(0.02,0.78,radial*(0.64+billow*0.68));
        alpha=density*0.50; if(alpha < 0.018) discard;
        col=lerp(float3(0.020,0.014,0.028),float3(0.20,0.085,0.15),saturate(billow*0.6+(1.0-i.uv.y)*0.4));
        col+=MOON_COLOR*0.06*pow(saturate(dot(-V,KeyLight.xyz)),6.0);
    } else if(type < 4.5) {
        col=shadeBuilding(i,N,V,noise);
    } else if(type < 5.5) {                   // faroles
        if(i.uv.y > 1.5) {
            float v=i.ib.x;
            col=(v < 0.5 ? float3(1.0,0.70,0.40) : (v < 1.5 ? float3(1.0,0.92,0.82) : float3(0.75,0.88,1.0)))*22.0;
        } else {
            col=keyShade(float3(0.06,0.06,0.065),N,keyShadow(i.world,N),1.0);
        }
    } else {                                  // vapor iluminado por los faroles
        float2 q=i.uv*2.0-1.0;
        float radial=saturate(1.0-dot(q*float2(0.92,1.05),q*float2(0.92,1.05)));
        float4 s0=NoiseTex.Sample(LinearWrap,i.uv*2.2+float2(0.17,0.29)+t*float2(0.011,-0.009));
        float curl=saturate(s0.r*0.6+s0.b*0.4);
        float density=saturate(radial*(0.55+curl*0.55))*lerp(1.0,0.2,saturate(i.uv.y));
        alpha=smoothstep(0.07,0.88,density)*lerp(0.55,0.05,saturate(i.uv.y));
        if(alpha < 0.012) discard;
        col=float3(0.55,0.55,0.58)*(0.05+lampLight(i.world)*0.9)+float3(0.02,0.02,0.03);
    }
    col*=0.96+(alu-0.5)*0.04;
    col=atmosphere(col,i.world,i.pos.xy);
    return float4(max(col,0),alpha);
}
'''

# Pasadas de post-proceso a pantalla completa (triángulo sin vertex buffer).
POST_HLSL = r'''
cbuffer PostCB : register(b1)
{
    float4 PostTexel;   // xy = 1/tamaño de la textura de origen
    float4 PostParams;  // x umbral bloom, y intensidad bloom, z exposición, w eje del blur (0 h, 1 v)
};
Texture2D SrcTex : register(t0);
Texture2D BloomA : register(t1);
Texture2D BloomB : register(t2);
SamplerState LinearClamp : register(s0);
struct PIn { float4 pos:SV_POSITION; float2 uv:TEXCOORD0; };

PIn VSPost(uint id:SV_VertexID)
{
    PIn o; float2 uv=float2((id<<1)&2, id&2);
    o.uv=uv; o.pos=float4(uv*float2(2.0,-2.0)+float2(-1.0,1.0),0.0,1.0); return o;
}
float3 down13(float2 uv)
{
    // Reducción de 13 muestras (estilo Jimenez/COD): sin parpadeo de píxeles brillantes.
    float2 t=PostTexel.xy;
    float3 a=SrcTex.Sample(LinearClamp,uv+t*float2(-2,-2)).rgb, b=SrcTex.Sample(LinearClamp,uv+t*float2(0,-2)).rgb, c=SrcTex.Sample(LinearClamp,uv+t*float2(2,-2)).rgb;
    float3 d=SrcTex.Sample(LinearClamp,uv+t*float2(-2,0)).rgb, e=SrcTex.Sample(LinearClamp,uv).rgb, f=SrcTex.Sample(LinearClamp,uv+t*float2(2,0)).rgb;
    float3 g=SrcTex.Sample(LinearClamp,uv+t*float2(-2,2)).rgb, h=SrcTex.Sample(LinearClamp,uv+t*float2(0,2)).rgb, k=SrcTex.Sample(LinearClamp,uv+t*float2(2,2)).rgb;
    float3 l=SrcTex.Sample(LinearClamp,uv+t*float2(-1,-1)).rgb, m=SrcTex.Sample(LinearClamp,uv+t*float2(1,-1)).rgb;
    float3 n=SrcTex.Sample(LinearClamp,uv+t*float2(-1,1)).rgb, o=SrcTex.Sample(LinearClamp,uv+t*float2(1,1)).rgb;
    return e*0.125+(a+c+g+k)*0.03125+(b+d+f+h)*0.0625+(l+m+n+o)*0.125;
}
float4 PSBright(PIn i):SV_TARGET
{
    float3 c=min(down13(i.uv),64.0);
    float l=max(c.r,max(c.g,c.b));
    float knee=PostParams.x*0.5;
    float soft=clamp(l-PostParams.x+knee,0.0,2.0*knee); soft=soft*soft/(4.0*knee+1e-4);
    float w=max(soft,l-PostParams.x)/max(l,1e-4);
    return float4(c*w,1.0);
}
float4 PSDown(PIn i):SV_TARGET { return float4(down13(i.uv),1.0); }
float4 PSBlur(PIn i):SV_TARGET
{
    float2 axis=(PostParams.w<0.5)?float2(PostTexel.x,0.0):float2(0.0,PostTexel.y);
    // Gauss de 9 taps en 5 lecturas bilineales.
    float3 c=SrcTex.Sample(LinearClamp,i.uv).rgb*0.2270270;
    c+=(SrcTex.Sample(LinearClamp,i.uv+axis*1.3846154).rgb+SrcTex.Sample(LinearClamp,i.uv-axis*1.3846154).rgb)*0.3162162;
    c+=(SrcTex.Sample(LinearClamp,i.uv+axis*3.2307692).rgb+SrcTex.Sample(LinearClamp,i.uv-axis*3.2307692).rgb)*0.0702703;
    return float4(c,1.0);
}
float3 aces(float3 x) { return saturate((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14)); }
float4 PSComposite(PIn i):SV_TARGET
{
    float3 hdr=SrcTex.Sample(LinearClamp,i.uv).rgb;
    float3 bloom=BloomA.Sample(LinearClamp,i.uv).rgb*0.55+BloomB.Sample(LinearClamp,i.uv).rgb*0.45;
    float3 c=aces((hdr+bloom*PostParams.y)*PostParams.z);
    float luma=dot(c,float3(0.2126,0.7152,0.0722));
    c=lerp(luma.xxx,c,1.12);                 // saturación leve
    c=pow(saturate(c),1.0/2.2);
    float2 q=i.uv-0.5; c*=1.0-dot(q,q)*0.38; // viñeta suave
    return float4(c,1.0);
}
'''


class _Mesh:
    def __init__(self, vb=None, ib=None, index_count=0): self.vb=vb; self.ib=ib; self.index_count=index_count


class D3D11Renderer:
    """Renderer D3D11 V29: ciudad nocturna, sombras, reflejos, HDR/MSAA, bloom y ACES; render fijo 1920×1080 en la GPU de alto rendimiento."""

    def __init__(self, width: int, height: int, visible: bool = True):
        # V27: width/height son la resolución de RENDER y nunca se recortan a la
        # pantalla. La ventana (window_width/height) sí se adapta al monitor y el
        # backbuffer se escala al presentarse, así torre 4K y notebook 1366×768
        # procesan exactamente los mismos píxeles.
        self.width=max(640,int(width)); self.height=max(360,int(height)); self.visible=bool(visible)
        self.window_width=self.width; self.window_height=self.height; self.fullscreen_window=False
        self.dpi_awareness='N/A'; self.adapter_info={'selection':'WINDOWS_DEFAULT','adapters':[]}
        self.user32=None; self.hinstance=None; self.hwnd=None; self.class_name=None; self._wndproc=None
        self.device=ctypes.c_void_p(); self.context=ctypes.c_void_p(); self.swap=ctypes.c_void_p(); self.rtv=ctypes.c_void_p(); self.depth_tex=ctypes.c_void_p(); self.dsv=ctypes.c_void_p()
        self.vs=ctypes.c_void_p(); self.ps=ctypes.c_void_p(); self.layout=ctypes.c_void_p(); self.cbuffer=ctypes.c_void_p(); self.sampler=ctypes.c_void_p(); self.noise_tex=ctypes.c_void_p(); self.noise_srv=ctypes.c_void_p(); self.blend=ctypes.c_void_p(); self.raster=ctypes.c_void_p(); self.depth_readonly=ctypes.c_void_p()
        # V28: sombras, HDR con MSAA, bloom y pasada final.
        self.shadow_tex=ctypes.c_void_p(); self.shadow_dsv=ctypes.c_void_p(); self.shadow_srv=ctypes.c_void_p(); self.shadow_cmp=ctypes.c_void_p(); self.shadow_raster=ctypes.c_void_p()
        self.hdr_tex=ctypes.c_void_p(); self.hdr_rtv=ctypes.c_void_p(); self.hdr_resolved=ctypes.c_void_p(); self.hdr_srv=ctypes.c_void_p()
        self.post_vs=ctypes.c_void_p(); self.post_ps={}; self.post_cb=ctypes.c_void_p(); self.linear_clamp=ctypes.c_void_p()
        self.bloom=[]  # [(tex, rtv, srv, w, h)]
        self.msaa_samples=1; self.light_viewproj=None
        # V29: reflejo planar de las calles y buffers de instancias de la ciudad.
        self.refl_tex=ctypes.c_void_p(); self.refl_rtv=ctypes.c_void_p(); self.refl_srv=ctypes.c_void_p(); self.refl_depth=ctypes.c_void_p(); self.refl_dsv=ctypes.c_void_p(); self.refl_size=(1,1)
        self.instances={}; self.instance_counts={}; self._lamp_cover={}
        self.meshes={}; self.ground_meshes={}
        self.gpu_timer=None; self.gpu_timing_available=False; self.gpu_timing_reason=None
        self.cancelled=False; self.feature_level=None; self.adapter_name='Direct3D 11 hardware adapter'; self.vram_mb=None
        self.startup_stage='created'
        self.startup_checks=[]
        self._shown=False
        try:
            self._run_startup_stage('window', self._init_window)
            self._run_startup_stage('device_swapchain', self._init_device)
            self._run_startup_stage('clear_present_smoke', self._smoke_clear_present)
            self._init_gpu_timing_optional()
            self._run_startup_stage('shader_pipeline', self._init_pipeline)
            self._run_startup_stage('render_targets', self._init_render_targets)
            self._run_startup_stage('scene_resources', self._init_resources)
            # Renderiza un frame real completo ANTES de mostrar la ventana. De esta
            # forma una inicialización fallida no deja al usuario mirando una ventana negra.
            self._run_startup_stage('first_scene_frame', self._validate_first_scene_frame)
            self.startup_stage='ready'
        except Exception:
            try:
                self.close()
            except Exception:
                pass
            raise

    def _run_startup_stage(self, name, fn):
        self.startup_stage=str(name)
        started=time.perf_counter()
        try:
            fn()
        except Exception as exc:
            raise RuntimeError(f'DirectX startup [{name}] falló: {type(exc).__name__}: {exc}') from exc
        self.startup_checks.append({'stage': str(name), 'status': 'OK', 'duration_ms': round((time.perf_counter()-started)*1000.0, 3)})

    def _init_window(self):
        self.user32=ctypes.WinDLL('user32.dll'); kernel32=ctypes.WinDLL('kernel32.dll')
        self.user32.DefWindowProcW.argtypes=[HWND_T,UINT,wintypes.WPARAM,wintypes.LPARAM]; self.user32.DefWindowProcW.restype=LRESULT
        self.user32.RegisterClassW.argtypes=[ctypes.POINTER(WNDCLASSW)]; self.user32.RegisterClassW.restype=wintypes.ATOM
        self.user32.CreateWindowExW.argtypes=[wintypes.DWORD,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,HWND_T,HMENU_T,HINSTANCE_T,LPVOID]; self.user32.CreateWindowExW.restype=HWND_T
        self.user32.ShowWindow.argtypes=[HWND_T,ctypes.c_int]; self.user32.UpdateWindow.argtypes=[HWND_T]
        self.user32.DestroyWindow.argtypes=[HWND_T]; self.user32.UnregisterClassW.argtypes=[wintypes.LPCWSTR,HINSTANCE_T]
        self.user32.PeekMessageW.argtypes=[ctypes.POINTER(MSG),HWND_T,UINT,UINT,UINT]; self.user32.PeekMessageW.restype=BOOL
        self.user32.TranslateMessage.argtypes=[ctypes.POINTER(MSG)]; self.user32.DispatchMessageW.argtypes=[ctypes.POINTER(MSG)]
        self.user32.SetWindowTextW.argtypes=[HWND_T,wintypes.LPCWSTR]
        self.user32.SetCursor.argtypes=[HCURSOR_T]; self.user32.SetCursor.restype=HCURSOR_T
        self.user32.GetSystemMetrics.argtypes=[ctypes.c_int]; self.user32.GetSystemMetrics.restype=ctypes.c_int
        self.user32.AdjustWindowRectEx.argtypes=[ctypes.POINTER(RECT),wintypes.DWORD,BOOL,wintypes.DWORD]; self.user32.AdjustWindowRectEx.restype=BOOL
        kernel32.GetModuleHandleW.argtypes=[wintypes.LPCWSTR]; kernel32.GetModuleHandleW.restype=HINSTANCE_T
        self.hinstance=kernel32.GetModuleHandleW(None)
        cancelled_ref=self
        @WNDPROC
        def wndproc(hwnd,msg,wparam,lparam):
            # V190: la propia ventana DirectX es la autoridad del cursor.
            # WM_SETCURSOR se procesa fuera de la región cronometrada (pump),
            # por lo que ocultarlo no altera FPS ni el workload V16. Evita que
            # Windows conserve el cursor 'watch' heredado de la navegación.
            if msg == WM_SETCURSOR:
                # Sólo el área cliente 3D queda sin cursor. En la barra de título
                # Windows conserva el puntero normal para cerrar/minimizar.
                hit_test = int(lparam) & 0xFFFF
                if hit_test == HTCLIENT:
                    try:
                        self.user32.SetCursor(None)
                    except Exception:
                        pass
                    return 1
            if msg in (WM_CLOSE,WM_DESTROY) or (msg == WM_KEYDOWN and int(wparam) == VK_ESCAPE):
                cancelled_ref.cancelled=True
                return 0
            return self.user32.DefWindowProcW(hwnd,msg,wparam,lparam)
        self._wndproc=wndproc
        self.class_name=f'CorePulseDX11Bench_{os.getpid()}_{threading.get_ident()}'
        wc=WNDCLASSW(); wc.lpfnWndProc=wndproc; wc.hInstance=self.hinstance; wc.lpszClassName=self.class_name
        if not self.user32.RegisterClassW(ctypes.byref(wc)):
            raise RuntimeError('No se pudo registrar la ventana DirectX del benchmark')
        self.dpi_awareness=enable_dpi_awareness()
        sw,sh=max(640,self.user32.GetSystemMetrics(0)),max(360,self.user32.GetSystemMetrics(1))
        # Pantalla igual o menor que el render: ventana sin bordes a pantalla
        # completa con el render 1920×1080 escalado. Pantalla mayor: ventana
        # centrada de 1920×1080 exactos.
        fullscreen = self.width >= sw or self.height >= sh
        self.fullscreen_window=fullscreen
        style = WS_POPUP if fullscreen else (WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX)
        if fullscreen:
            self.window_width,self.window_height=sw,sh
            ow,oh=sw,sh; x=y=0
        else:
            self.window_width,self.window_height=self.width,self.height
            rect=RECT(0,0,self.width,self.height); self.user32.AdjustWindowRectEx(ctypes.byref(rect),style,False,0)
            ow,oh=rect.right-rect.left,rect.bottom-rect.top
            x=max(0,(sw-ow)//2); y=max(0,(sh-oh)//2)
        # Siempre se crea oculta. Sólo se muestra después de que un frame 3D real
        # haya sido renderizado y Present haya terminado correctamente.
        self.hwnd=self.user32.CreateWindowExW(0,self.class_name,f'CorePulse Benchmark {GPU_BENCHMARK_LABEL} — DirectX 11',style,x,y,ow,oh,None,None,self.hinstance,None)
        if not self.hwnd: raise RuntimeError('No se pudo crear la ventana DirectX 11')

    def _init_device(self):
        d3d11=ctypes.WinDLL('d3d11.dll')
        create=d3d11.D3D11CreateDeviceAndSwapChain
        create.argtypes=[ctypes.c_void_p,UINT,ctypes.c_void_p,UINT,ctypes.POINTER(UINT),UINT,UINT,ctypes.POINTER(DXGI_SWAP_CHAIN_DESC),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(UINT),ctypes.POINTER(ctypes.c_void_p)]
        create.restype=HRESULT
        desc=DXGI_SWAP_CHAIN_DESC(); desc.BufferDesc.Width=self.width; desc.BufferDesc.Height=self.height; desc.BufferDesc.RefreshRate=DXGI_RATIONAL(0,1); desc.BufferDesc.Format=DXGI_FORMAT_R8G8B8A8_UNORM; desc.SampleDesc=DXGI_SAMPLE_DESC(1,0); desc.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT; desc.BufferCount=2; desc.OutputWindow=self.hwnd; desc.Windowed=1; desc.SwapEffect=DXGI_SWAP_EFFECT_DISCARD
        levels=(UINT*3)(D3D_FEATURE_LEVEL_11_0,D3D_FEATURE_LEVEL_10_1,D3D_FEATURE_LEVEL_10_0); fl=UINT()
        adapter,self.adapter_info=select_high_performance_adapter()
        try:
            # Con adaptador explícito Direct3D exige DRIVER_TYPE_UNKNOWN.
            driver=D3D_DRIVER_TYPE_UNKNOWN if adapter else D3D_DRIVER_TYPE_HARDWARE
            hr=create(adapter,driver,None,D3D11_CREATE_DEVICE_BGRA_SUPPORT,levels,3,D3D11_SDK_VERSION,ctypes.byref(desc),ctypes.byref(self.swap),ctypes.byref(self.device),ctypes.byref(fl),ctypes.byref(self.context))
            if not _hr_ok(hr) and adapter:
                # Último recurso: el predeterminado de Windows, informado como tal.
                self.adapter_info={**self.adapter_info,'selection':'WINDOWS_DEFAULT','reason':f'Adaptador elegido rechazado (0x{int(hr)&0xffffffff:08X})'}
                hr=create(None,D3D_DRIVER_TYPE_HARDWARE,None,D3D11_CREATE_DEVICE_BGRA_SUPPORT,levels,3,D3D11_SDK_VERSION,ctypes.byref(desc),ctypes.byref(self.swap),ctypes.byref(self.device),ctypes.byref(fl),ctypes.byref(self.context))
        finally:
            _release(adapter)
        if not _hr_ok(hr): raise RuntimeError(f'D3D11CreateDeviceAndSwapChain falló (0x{int(hr)&0xffffffff:08X})')
        self.feature_level=int(fl.value)
        # Backbuffer -> RTV.
        back=ctypes.c_void_p(); hr=_com_method(self.swap,9,HRESULT,UINT,ctypes.POINTER(GUID),ctypes.POINTER(ctypes.c_void_p))(self.swap,0,ctypes.byref(IID_ID3D11Texture2D),ctypes.byref(back))
        if not _hr_ok(hr): raise RuntimeError('IDXGISwapChain::GetBuffer falló')
        try:
            hr=_com_method(self.device,9,HRESULT,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,back,None,ctypes.byref(self.rtv))
            if not _hr_ok(hr): raise RuntimeError('CreateRenderTargetView falló')
        finally: _release(back)
        # V28: el depth buffer se crea con las render targets HDR (mismo MSAA).
        # Adaptador real que creó el device.
        try:
            dxgi_dev=_query_interface(self.device,IID_IDXGIDevice)
            if dxgi_dev:
                adapter=ctypes.c_void_p(); hr=_com_method(dxgi_dev,7,HRESULT,ctypes.POINTER(ctypes.c_void_p))(dxgi_dev,ctypes.byref(adapter))
                if _hr_ok(hr) and adapter.value:
                    ad=DXGI_ADAPTER_DESC(); hr2=_com_method(adapter,8,HRESULT,ctypes.POINTER(DXGI_ADAPTER_DESC))(adapter,ctypes.byref(ad))
                    if _hr_ok(hr2):
                        self.adapter_name=str(ad.Description).strip() or self.adapter_name; self.vram_mb=int(ad.DedicatedVideoMemory/(1024*1024))
                    _release(adapter)
                _release(dxgi_dev)
        except Exception:
            pass

    def _init_gpu_timing_optional(self):
        self.startup_stage='gpu_timestamp_queries'
        started=time.perf_counter()
        try:
            self.gpu_timer=_GpuFrameTimer(self.device,self.context,slot_count=192)
            self.gpu_timing_available=True
            self.gpu_timing_reason=None
            status='OK'
        except Exception as exc:
            self.gpu_timer=None; self.gpu_timing_available=False
            self.gpu_timing_reason=f'{type(exc).__name__}: {exc}'
            status='N/A'
        self.startup_checks.append({'stage':'gpu_timestamp_queries','status':status,'duration_ms':round((time.perf_counter()-started)*1000.0,3),'reason':self.gpu_timing_reason})

    def begin_scene_gpu_timing(self):
        if self.gpu_timer is None:
            return
        self.gpu_timer.drain(timeout_s=2.0)
        self.gpu_timer.reset_scene()

    def finish_scene_gpu_timing(self, timeout_s: float = 4.0):
        if self.gpu_timer is None:
            return [], {'dropped':0,'disjoint':0}
        vals=self.gpu_timer.drain(timeout_s=timeout_s)
        return vals, {'dropped':self.gpu_timer.dropped_frames,'disjoint':self.gpu_timer.disjoint_frames}

    def poll_gpu_timing(self):
        """Recoge queries listas fuera del frametime medido."""
        if self.gpu_timer is None:
            return []
        return self.gpu_timer.collect_ready(nonblocking=True)

    def prepare_timed_frame(self):
        """Trabajo de ventana/auditoría deliberadamente fuera del cronómetro."""
        self.pump()
        self.poll_gpu_timing()
        self._show_if_ready()

    def _show_if_ready(self):
        if self.visible and not self._shown and self.hwnd:
            self.user32.ShowWindow(self.hwnd,SW_SHOW)
            self.user32.UpdateWindow(self.hwnd)
            try:
                self.user32.SetCursor(None)
            except Exception:
                pass
            self._shown=True

    def _present(self):
        hr=_com_method(self.swap,8,HRESULT,UINT,UINT)(self.swap,0,0)
        if not _hr_ok(hr):
            raise RuntimeError(f'IDXGISwapChain::Present falló 0x{int(hr)&0xffffffff:08X}')

    def _smoke_clear_present(self):
        # Smoke test mínimo: valida DeviceContext + RTV + SwapChain sin depender
        # todavía de shaders ni geometría. Se ejecuta con la ventana oculta.
        clear=(FLOAT*4)(0.035,0.07,0.12,1.0)
        _com_method(self.context,CTX_CLEAR_RENDER_TARGET_VIEW,None,ctypes.c_void_p,ctypes.POINTER(FLOAT))(self.context,self.rtv,clear)
        self._present()

    def _validate_first_scene_frame(self):
        level=profile_levels('standard')[0]
        # Un frame completo real: input assembler, shaders, constant buffer,
        # texturas, depth, instancing y Present.
        self.render_frame(level,0.0,0,show_after_present=False)
        self._show_if_ready()

    def _create_buffer(self, raw: bytes, bind_flags: int, usage: int=D3D11_USAGE_IMMUTABLE):
        out=ctypes.c_void_p(); desc=D3D11_BUFFER_DESC(len(raw),usage,bind_flags,0,0,0)
        buf=ctypes.create_string_buffer(raw); sub=D3D11_SUBRESOURCE_DATA(ctypes.cast(buf,LPVOID),0,0)
        hr=_com_method(self.device,3,HRESULT,ctypes.POINTER(D3D11_BUFFER_DESC),ctypes.POINTER(D3D11_SUBRESOURCE_DATA),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(desc),ctypes.byref(sub),ctypes.byref(out))
        if not _hr_ok(hr): raise RuntimeError(f'CreateBuffer falló: 0x{int(hr)&0xffffffff:08X}')
        return out

    def _make_mesh(self, vertices, indices):
        vb_raw=b''.join(struct.pack('<8f',*map(float,v)) for v in vertices); ib_raw=struct.pack('<%dI'%len(indices),*indices)
        return _Mesh(self._create_buffer(vb_raw,D3D11_BIND_VERTEX_BUFFER),self._create_buffer(ib_raw,D3D11_BIND_INDEX_BUFFER),len(indices))

    def _init_pipeline(self):
        vs_blob,vs_bytes=_compile_shader(HLSL,b'VSMain',b'vs_5_0' if self.feature_level>=D3D_FEATURE_LEVEL_11_0 else b'vs_4_0')
        ps_blob,ps_bytes=_compile_shader(HLSL,b'PSMain',b'ps_5_0' if self.feature_level>=D3D_FEATURE_LEVEL_11_0 else b'ps_4_0')
        try:
            vs_buf=ctypes.create_string_buffer(vs_bytes); hr=_com_method(self.device,12,HRESULT,LPVOID,SIZE_T,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.cast(vs_buf,LPVOID),len(vs_bytes),None,ctypes.byref(self.vs));
            if not _hr_ok(hr): raise RuntimeError('CreateVertexShader falló')
            ps_buf=ctypes.create_string_buffer(ps_bytes); hr=_com_method(self.device,15,HRESULT,LPVOID,SIZE_T,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.cast(ps_buf,LPVOID),len(ps_bytes),None,ctypes.byref(self.ps));
            if not _hr_ok(hr): raise RuntimeError('CreatePixelShader falló')
            # Slot 0: vértice del mesh. Slot 1: datos por instancia (city_layout).
            elems=(D3D11_INPUT_ELEMENT_DESC*5)(
                D3D11_INPUT_ELEMENT_DESC(b'POSITION',0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D11_INPUT_PER_VERTEX_DATA,0),
                D3D11_INPUT_ELEMENT_DESC(b'NORMAL',0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D11_INPUT_PER_VERTEX_DATA,0),
                D3D11_INPUT_ELEMENT_DESC(b'TEXCOORD',0,DXGI_FORMAT_R32G32_FLOAT,0,24,D3D11_INPUT_PER_VERTEX_DATA,0),
                D3D11_INPUT_ELEMENT_DESC(b'INSTA',0,DXGI_FORMAT_R32G32B32A32_FLOAT,1,0,D3D11_INPUT_PER_INSTANCE_DATA,1),
                D3D11_INPUT_ELEMENT_DESC(b'INSTB',0,DXGI_FORMAT_R32G32B32A32_FLOAT,1,16,D3D11_INPUT_PER_INSTANCE_DATA,1),
            )
            hr=_com_method(self.device,11,HRESULT,ctypes.POINTER(D3D11_INPUT_ELEMENT_DESC),UINT,LPVOID,SIZE_T,ctypes.POINTER(ctypes.c_void_p))(self.device,elems,5,ctypes.cast(vs_buf,LPVOID),len(vs_bytes),ctypes.byref(self.layout))
            if not _hr_ok(hr): raise RuntimeError('CreateInputLayout falló')
        finally:
            _release(vs_blob); _release(ps_blob)
        # Constant buffer 208 B (LightViewProj, KeyLight y Extra) -> múltiplo de 16.
        cb_desc=D3D11_BUFFER_DESC(208,D3D11_USAGE_DEFAULT,D3D11_BIND_CONSTANT_BUFFER,0,0,0); hr=_com_method(self.device,3,HRESULT,ctypes.POINTER(D3D11_BUFFER_DESC),ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(cb_desc),None,ctypes.byref(self.cbuffer))
        if not _hr_ok(hr): raise RuntimeError('CreateBuffer(constant) falló')
        # Sampler.
        sd=D3D11_SAMPLER_DESC(); sd.Filter=D3D11_FILTER_MIN_MAG_MIP_LINEAR; sd.AddressU=sd.AddressV=sd.AddressW=D3D11_TEXTURE_ADDRESS_WRAP; sd.ComparisonFunc=D3D11_COMPARISON_NEVER; sd.MinLOD=0.0; sd.MaxLOD=1000.0
        hr=_com_method(self.device,23,HRESULT,ctypes.POINTER(D3D11_SAMPLER_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(sd),ctypes.byref(self.sampler));
        if not _hr_ok(hr): raise RuntimeError('CreateSamplerState falló')
        # Alpha blend for clouds.
        bd=D3D11_BLEND_DESC(); rt=bd.RenderTarget[0]; rt.BlendEnable=1; rt.SrcBlend=D3D11_BLEND_SRC_ALPHA; rt.DestBlend=D3D11_BLEND_INV_SRC_ALPHA; rt.BlendOp=D3D11_BLEND_OP_ADD; rt.SrcBlendAlpha=D3D11_BLEND_ONE; rt.DestBlendAlpha=D3D11_BLEND_ZERO; rt.BlendOpAlpha=D3D11_BLEND_OP_ADD; rt.RenderTargetWriteMask=D3D11_COLOR_WRITE_ENABLE_ALL
        hr=_com_method(self.device,20,HRESULT,ctypes.POINTER(D3D11_BLEND_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(bd),ctypes.byref(self.blend));
        if not _hr_ok(hr): self.blend=ctypes.c_void_p()
        # V14: transparencias (nubes) y sky prueban profundidad, pero NO escriben
        # en el depth buffer. Evita halos/planos que oculten puffs posteriores y
        # permite dibujar el cielo antes de la capa transparente correctamente.
        keep=D3D11_DEPTH_STENCILOP_DESC(D3D11_STENCIL_OP_KEEP,D3D11_STENCIL_OP_KEEP,D3D11_STENCIL_OP_KEEP,D3D11_COMPARISON_NEVER)
        dsd=D3D11_DEPTH_STENCIL_DESC(1,D3D11_DEPTH_WRITE_MASK_ZERO,D3D11_COMPARISON_LESS,0,0xff,0xff,(ctypes.c_ubyte*2)(0,0),keep,keep)
        hr=_com_method(self.device,21,HRESULT,ctypes.POINTER(D3D11_DEPTH_STENCIL_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(dsd),ctypes.byref(self.depth_readonly))
        if not _hr_ok(hr): self.depth_readonly=ctypes.c_void_p()
        rd=D3D11_RASTERIZER_DESC(D3D11_FILL_SOLID,D3D11_CULL_NONE,0,0,0.0,0.0,1,0,0,0); hr=_com_method(self.device,22,HRESULT,ctypes.POINTER(D3D11_RASTERIZER_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(rd),ctypes.byref(self.raster));
        if not _hr_ok(hr): self.raster=ctypes.c_void_p()
        # Sombras: sesgo por pendiente en la pasada de profundidad.
        srd=D3D11_RASTERIZER_DESC(D3D11_FILL_SOLID,D3D11_CULL_NONE,0,0,0.0,1.6,1,0,0,0)
        hr=_com_method(self.device,22,HRESULT,ctypes.POINTER(D3D11_RASTERIZER_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(srd),ctypes.byref(self.shadow_raster))
        if not _hr_ok(hr): raise RuntimeError('CreateRasterizerState(sombras) falló')
        self.shadow_cmp=self._create_sampler(D3D11_FILTER_COMPARISON_MIN_MAG_LINEAR_MIP_POINT,D3D11_TEXTURE_ADDRESS_BORDER,D3D11_COMPARISON_LESS_EQUAL,border=1.0)
        self.linear_clamp=self._create_sampler(D3D11_FILTER_MIN_MAG_MIP_LINEAR,D3D11_TEXTURE_ADDRESS_CLAMP,D3D11_COMPARISON_NEVER)
        self._init_post_pipeline()
        self._create_noise_texture()

    def _create_sampler(self, filt, address, comparison, border=0.0):
        sd=D3D11_SAMPLER_DESC(); sd.Filter=filt; sd.AddressU=sd.AddressV=sd.AddressW=address; sd.ComparisonFunc=comparison
        sd.MinLOD=0.0; sd.MaxLOD=1000.0; sd.MaxAnisotropy=1
        for k in range(4): sd.BorderColor[k]=border
        out=ctypes.c_void_p()
        hr=_com_method(self.device,23,HRESULT,ctypes.POINTER(D3D11_SAMPLER_DESC),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(sd),ctypes.byref(out))
        if not _hr_ok(hr): raise RuntimeError(f'CreateSamplerState falló 0x{int(hr)&0xffffffff:08X}')
        return out

    def _init_post_pipeline(self):
        sm5=self.feature_level>=D3D_FEATURE_LEVEL_11_0
        blob,raw=_compile_shader(POST_HLSL,b'VSPost',b'vs_5_0' if sm5 else b'vs_4_0')
        try:
            buf=ctypes.create_string_buffer(raw)
            hr=_com_method(self.device,12,HRESULT,LPVOID,SIZE_T,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.cast(buf,LPVOID),len(raw),None,ctypes.byref(self.post_vs))
            if not _hr_ok(hr): raise RuntimeError('CreateVertexShader(post) falló')
        finally:
            _release(blob)
        for name in ('PSBright','PSDown','PSBlur','PSComposite'):
            blob,raw=_compile_shader(POST_HLSL,name.encode('ascii'),b'ps_5_0' if sm5 else b'ps_4_0')
            try:
                shader=ctypes.c_void_p(); buf=ctypes.create_string_buffer(raw)
                hr=_com_method(self.device,15,HRESULT,LPVOID,SIZE_T,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.cast(buf,LPVOID),len(raw),None,ctypes.byref(shader))
                if not _hr_ok(hr): raise RuntimeError(f'CreatePixelShader({name}) falló')
                self.post_ps[name]=shader
            finally:
                _release(blob)
        desc=D3D11_BUFFER_DESC(32,D3D11_USAGE_DEFAULT,D3D11_BIND_CONSTANT_BUFFER,0,0,0)
        hr=_com_method(self.device,3,HRESULT,ctypes.POINTER(D3D11_BUFFER_DESC),ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(desc),None,ctypes.byref(self.post_cb))
        if not _hr_ok(hr): raise RuntimeError('CreateBuffer(post) falló')

    def _texture(self, w, h, fmt, bind, samples=1):
        tex=ctypes.c_void_p()
        td=D3D11_TEXTURE2D_DESC(int(w),int(h),1,1,fmt,DXGI_SAMPLE_DESC(int(samples),0),D3D11_USAGE_DEFAULT,bind,0,0)
        hr=_com_method(self.device,5,HRESULT,ctypes.POINTER(D3D11_TEXTURE2D_DESC),ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(td),None,ctypes.byref(tex))
        if not _hr_ok(hr): raise RuntimeError(f'CreateTexture2D({w}x{h}, formato {fmt}, MSAA {samples}) falló 0x{int(hr)&0xffffffff:08X}')
        return tex

    def _view(self, index, resource, desc=None, what='vista'):
        out=ctypes.c_void_p()
        hr=_com_method(self.device,index,HRESULT,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,resource,ctypes.byref(desc) if desc is not None else None,ctypes.byref(out))
        if not _hr_ok(hr): raise RuntimeError(f'Crear {what} falló 0x{int(hr)&0xffffffff:08X}')
        return out

    def _msaa_supported(self, fmt, samples):
        levels=UINT(0)
        try:
            hr=_com_method(self.device,DEVICE_CHECK_MULTISAMPLE_QUALITY_LEVELS,HRESULT,UINT,UINT,ctypes.POINTER(UINT))(self.device,fmt,samples,ctypes.byref(levels))
        except RuntimeError:
            return False
        return _hr_ok(hr) and levels.value > 0

    def _init_render_targets(self):
        w,h=self.width,self.height
        # MSAA 4x si la GPU lo admite para HDR y profundidad (garantizado en FL 10.1+).
        self.msaa_samples=MSAA_SAMPLES if (self._msaa_supported(DXGI_FORMAT_R16G16B16A16_FLOAT,MSAA_SAMPLES) and self._msaa_supported(DXGI_FORMAT_D24_UNORM_S8_UINT,MSAA_SAMPLES)) else 1
        ms=self.msaa_samples
        bind_rt=D3D11_BIND_RENDER_TARGET|(D3D11_BIND_SHADER_RESOURCE if ms==1 else 0)
        self.hdr_tex=self._texture(w,h,DXGI_FORMAT_R16G16B16A16_FLOAT,bind_rt,ms)
        self.hdr_rtv=self._view(9,self.hdr_tex,what='RTV HDR')
        if ms>1:
            self.hdr_resolved=self._texture(w,h,DXGI_FORMAT_R16G16B16A16_FLOAT,D3D11_BIND_SHADER_RESOURCE,1)
            self.hdr_srv=self._view(7,self.hdr_resolved,what='SRV HDR')
        else:
            self.hdr_srv=self._view(7,self.hdr_tex,what='SRV HDR')
        self.depth_tex=self._texture(w,h,DXGI_FORMAT_D24_UNORM_S8_UINT,D3D11_BIND_DEPTH_STENCIL,ms)
        self.dsv=self._view(10,self.depth_tex,what='DSV')
        # Cadena de bloom: 1/2 (umbral), 1/4 (+blur), 1/8 (+blur).
        for div in (2,4,4,8,8):
            bw,bh=max(1,w//div),max(1,h//div)
            tex=self._texture(bw,bh,DXGI_FORMAT_R11G11B10_FLOAT,D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE)
            self.bloom.append((tex,self._view(9,tex,what='RTV bloom'),self._view(7,tex,what='SRV bloom'),bw,bh))
        # Mapa de sombras: textura sin tipo vista como D32 (escritura) y R32 (lectura).
        self.shadow_tex=self._texture(SHADOW_MAP_SIZE,SHADOW_MAP_SIZE,DXGI_FORMAT_R32_TYPELESS,D3D11_BIND_DEPTH_STENCIL|D3D11_BIND_SHADER_RESOURCE)
        self.shadow_dsv=self._view(10,self.shadow_tex,D3D11_DEPTH_STENCIL_VIEW_DESC(DXGI_FORMAT_D32_FLOAT,D3D11_DSV_DIMENSION_TEXTURE2D,0,0),'DSV sombras')
        self.shadow_srv=self._view(7,self.shadow_tex,D3D11_SHADER_RESOURCE_VIEW_DESC(DXGI_FORMAT_R32_FLOAT,D3D11_SRV_DIMENSION_TEXTURE2D,0,1),'SRV sombras')
        # Reflejo planar del suelo: escena espejada a media resolución.
        rw,rh=w,h  # cada nivel dibuja en w/divisor × h/divisor (reflection_divisor)
        self.refl_tex=self._texture(rw,rh,DXGI_FORMAT_R16G16B16A16_FLOAT,D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE)
        self.refl_rtv=self._view(9,self.refl_tex,what='RTV reflejo'); self.refl_srv=self._view(7,self.refl_tex,what='SRV reflejo')
        self.refl_depth=self._texture(rw,rh,DXGI_FORMAT_D24_UNORM_S8_UINT,D3D11_BIND_DEPTH_STENCIL)
        self.refl_dsv=self._view(10,self.refl_depth,what='DSV reflejo')
        self.refl_size=(rw,rh)
        self.light_viewproj=_light_viewproj()

    def _create_noise_texture(self):
        """Textura procedural determinista multicanal para materiales V13.

        Los tres canales no son el mismo ruido: combinan ondas amplias con una
        componente fina determinista. Esto permite que terreno, corteza, follaje
        y agua tengan detalle sin depender de assets externos ni datos aleatorios
        diferentes entre ejecuciones.
        """
        w=h=512; data=bytearray(w*h*4); seed=0x2468ACE1
        for y in range(h):
            fy=y/float(h)
            for x in range(w):
                fx=x/float(w)
                seed=(1664525*seed+1013904223)&0xffffffff
                rnd=((seed>>8)&0xffff)/65535.0
                a=0.50+0.24*math.sin(fx*math.tau*3.0+fy*1.7)+0.18*math.cos(fy*math.tau*5.0-fx*2.1)
                b=0.50+0.22*math.sin((fx+fy)*math.tau*7.0)+0.15*math.cos((fx-fy)*math.tau*11.0)
                c=0.50+0.20*math.sin(fx*math.tau*17.0)*math.cos(fy*math.tau*13.0)
                r=int(max(0,min(255,(a*0.72+rnd*0.28)*255.0)))
                g=int(max(0,min(255,(b*0.78+rnd*0.22)*255.0)))
                bl=int(max(0,min(255,(c*0.68+rnd*0.32)*255.0)))
                i=(y*w+x)*4; data[i:i+4]=bytes((r,g,bl,255))
        raw=ctypes.create_string_buffer(bytes(data)); td=D3D11_TEXTURE2D_DESC(w,h,1,1,DXGI_FORMAT_R8G8B8A8_UNORM,DXGI_SAMPLE_DESC(1,0),D3D11_USAGE_IMMUTABLE,D3D11_BIND_SHADER_RESOURCE,0,0); sub=D3D11_SUBRESOURCE_DATA(ctypes.cast(raw,LPVOID),w*4,0)
        hr=_com_method(self.device,5,HRESULT,ctypes.POINTER(D3D11_TEXTURE2D_DESC),ctypes.POINTER(D3D11_SUBRESOURCE_DATA),ctypes.POINTER(ctypes.c_void_p))(self.device,ctypes.byref(td),ctypes.byref(sub),ctypes.byref(self.noise_tex));
        if not _hr_ok(hr): raise RuntimeError('CreateTexture2D(surface procedural) falló')
        hr=_com_method(self.device,7,HRESULT,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p))(self.device,self.noise_tex,None,ctypes.byref(self.noise_srv));
        if not _hr_ok(hr): raise RuntimeError('CreateShaderResourceView falló')

    def _init_resources(self):
        self.meshes['building']=self._make_mesh(*build_building())
        self.meshes['streetlight']=self._make_mesh(*build_streetlight())
        self.meshes['vehicle']=self._make_mesh(*build_vehicle())
        self.meshes['cloud']=self._make_mesh(*build_cloud())
        self.meshes['steam']=self._make_mesh(*build_steam_plume())
        self.meshes['sky']=self._make_mesh(*build_sky())
        for level in profile_levels('standard'):
            self.ground_meshes[level.ground_resolution]=self._make_mesh(*build_ground(level.ground_resolution))
        # Instancias deterministas de la ciudad (dos float4 cada una). Los
        # dibujos sin instancias leen la instancia «dummy» de ceros.
        layout=city_layout()
        for key in ('buildings','streetlights','vehicles','clouds','steam'):
            rows=layout[key]
            raw=b''.join(struct.pack('<8f',*map(float,row)) for row in rows)
            self.instances[key]=self._create_buffer(raw,D3D11_BIND_VERTEX_BUFFER)
            self.instance_counts[key]=len(rows)
        self.instances['dummy']=self._create_buffer(bytes(INSTANCE_STRIDE),D3D11_BIND_VERTEX_BUFFER)

    def pump(self):
        msg=MSG()
        while self.user32.PeekMessageW(ctypes.byref(msg),None,0,0,PM_REMOVE):
            self.user32.TranslateMessage(ctypes.byref(msg)); self.user32.DispatchMessageW(ctypes.byref(msg))

    def _set_mesh(self, mesh: _Mesh, inst='dummy'):
        vbs=(ctypes.c_void_p*2)(mesh.vb.value,self.instances[inst].value)
        strides=(UINT*2)(32,INSTANCE_STRIDE); offsets=(UINT*2)(0,0)
        _com_method(self.context,CTX_IA_SET_VERTEX_BUFFERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(UINT),ctypes.POINTER(UINT))(self.context,0,2,vbs,strides,offsets)
        _com_method(self.context,CTX_IA_SET_INDEX_BUFFER,None,ctypes.c_void_p,UINT,UINT)(self.context,mesh.ib,DXGI_FORMAT_R32_UINT,0)

    def _update_cb(self, viewproj, camera, elapsed, object_type, level: SceneLevel, render_pass=0):
        # Bruma por nivel 0..1: sólo atmósfera, la carga GPU sigue en shader_iterations.
        haze=max(0.0,min(1.0,(float(level.shader_iterations)-10.0)/54.0))
        key=_norm(KEY_LIGHT_DIRECTION)
        n=min(level.streetlight_instances,self.instance_counts.get('streetlights',0))
        cover=self._lamp_cover.get(n)
        if cover is None:
            cover=self._lamp_cover[n]=lamp_coverage(n)
        vals=(_flatten_matrix(viewproj)+[camera[0],camera[1],camera[2],elapsed,float(object_type),cover,float(level.shader_iterations),float(level.texture_samples),
              float(self.width),float(self.height),float(render_pass),haze]
              +_flatten_matrix(self.light_viewproj)+[key[0],key[1],key[2],KEY_LIGHT_INTENSITY]
              +[1.0/max(1,int(level.reflection_divisor)),float(level.volumetric_steps),0.0,0.0])
        raw=struct.pack('<52f',*vals); buf=ctypes.create_string_buffer(raw)
        _com_method(self.context,CTX_UPDATE_SUBRESOURCE,None,ctypes.c_void_p,UINT,ctypes.c_void_p,ctypes.c_void_p,UINT,UINT)(self.context,self.cbuffer,0,None,ctypes.cast(buf,LPVOID),0,0)

    def _draw(self, mesh: _Mesh, instances: int, viewproj, camera, elapsed, object_type, level, blend=False, depth_readonly=False, render_pass=0, inst='dummy'):
        if inst!='dummy': instances=min(int(instances),self.instance_counts.get(inst,0))
        if instances<=0:return
        self._set_mesh(mesh,inst); self._update_cb(viewproj,camera,elapsed,object_type,level,render_pass)
        blend_factor=(FLOAT*4)(0,0,0,0)
        _com_method(self.context,CTX_OM_SET_BLEND_STATE,None,ctypes.c_void_p,ctypes.POINTER(FLOAT),UINT)(self.context,self.blend if blend and self.blend.value else None,blend_factor,0xffffffff)
        if depth_readonly:
            depth_state=getattr(self,'depth_readonly',None)
            if depth_state is not None and getattr(depth_state,'value',None):
                try:
                    _com_method(self.context,CTX_OM_SET_DEPTH_STENCIL_STATE,None,ctypes.c_void_p,UINT)(self.context,depth_state,0)
                except RuntimeError:
                    # Compatibilidad defensiva con contextos de prueba/feature reducido.
                    # En D3D11 hardware normal el slot forma parte obligatoria de la interfaz.
                    pass
        if instances==1:
            _com_method(self.context,CTX_DRAW_INDEXED,None,UINT,UINT,ctypes.c_int)(self.context,mesh.index_count,0,0)
        else:
            _com_method(self.context,CTX_DRAW_INDEXED_INSTANCED,None,UINT,UINT,UINT,ctypes.c_int,UINT)(self.context,mesh.index_count,instances,0,0,0)

    def render_frame(self, level: SceneLevel, elapsed: float, level_index: int, *, show_after_present: bool = True, gpu_timing: bool = False, pump_messages: bool = True):
        if pump_messages:
            self.pump()
        gpu_timer=getattr(self,'gpu_timer',None)
        timer_slot=gpu_timer.begin_frame() if gpu_timing and gpu_timer is not None else None
        ctx=self.context
        set_rts=_com_method(ctx,CTX_OM_SET_RENDER_TARGETS,None,UINT,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p)
        set_srvs=_com_method(ctx,CTX_PS_SET_SHADER_RESOURCES,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))
        set_vp=_com_method(ctx,CTX_RS_SET_VIEWPORTS,None,UINT,ctypes.POINTER(D3D11_VIEWPORT))
        set_rs=_com_method(ctx,CTX_RS_SET_STATE,None,ctypes.c_void_p)
        clear_dsv=_com_method(ctx,CTX_CLEAR_DEPTH_STENCIL_VIEW,None,ctypes.c_void_p,UINT,FLOAT,ctypes.c_ubyte)
        no_srvs=(ctypes.c_void_p*3)()
        set_srvs(ctx,0,3,no_srvs)  # el mapa de sombras no puede estar leído y escrito a la vez
        _com_method(ctx,CTX_IA_SET_INPUT_LAYOUT,None,ctypes.c_void_p)(ctx,self.layout); _com_method(ctx,CTX_IA_SET_PRIMITIVE_TOPOLOGY,None,UINT)(ctx,D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST)
        _com_method(ctx,CTX_VS_SET_SHADER,None,ctypes.c_void_p,ctypes.c_void_p,UINT)(ctx,self.vs,None,0); _com_method(ctx,CTX_PS_SET_SHADER,None,ctypes.c_void_p,ctypes.c_void_p,UINT)(ctx,self.ps,None,0)
        cbs=(ctypes.c_void_p*1)(self.cbuffer.value); _com_method(ctx,CTX_VS_SET_CONSTANT_BUFFERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))(ctx,0,1,cbs); _com_method(ctx,CTX_PS_SET_CONSTANT_BUFFERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))(ctx,0,1,cbs)
        samps=(ctypes.c_void_p*3)(self.sampler.value,self.shadow_cmp.value,self.linear_clamp.value); _com_method(ctx,CTX_PS_SET_SAMPLERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))(ctx,0,3,samps)
        set_srvs(ctx,0,1,(ctypes.c_void_p*1)(self.noise_srv.value))
        eye,target=_camera_at(elapsed,level_index); view=_look_at_lh(eye,target); proj=_perspective_fov_lh(math.radians(CAMERA_FOV_DEG),self.width/self.height,0.5,CAMERA_FAR); vp_mat=_mat_mul(view,proj)
        ground=self.ground_meshes.get(level.ground_resolution) or next(iter(self.ground_meshes.values()))
        m=self.meshes; t=elapsed
        set_blend=_com_method(ctx,CTX_OM_SET_BLEND_STATE,None,ctypes.c_void_p,ctypes.POINTER(FLOAT),UINT)
        set_depth=_com_method(ctx,CTX_OM_SET_DEPTH_STENCIL_STATE,None,ctypes.c_void_p,UINT)
        no_blend=(FLOAT*4)(0,0,0,0)
        black=(FLOAT*4)(0.0,0.0,0.0,1.0)
        clear_rtv=_com_method(ctx,CTX_CLEAR_RENDER_TARGET_VIEW,None,ctypes.c_void_p,ctypes.POINTER(FLOAT))

        # 1) Sombras: profundidad desde la luna de edificios, faroles y vehículos.
        set_rts(ctx,0,None,self.shadow_dsv)
        clear_dsv(ctx,self.shadow_dsv,D3D11_CLEAR_DEPTH,1.0,0)
        svp=D3D11_VIEWPORT(0.0,0.0,float(SHADOW_MAP_SIZE),float(SHADOW_MAP_SIZE),0.0,1.0); set_vp(ctx,1,ctypes.byref(svp))
        set_rs(ctx,self.shadow_raster)
        lvp=self.light_viewproj
        self._draw(m['building'],level.building_instances,lvp,eye,t,4,level,render_pass=1,inst='buildings')
        self._draw(m['streetlight'],level.streetlight_instances,lvp,eye,t,5,level,render_pass=1,inst='streetlights')
        self._draw(m['vehicle'],level.vehicle_instances,lvp,eye,t,2,level,render_pass=1,inst='vehicles')
        if self.raster.value: set_rs(ctx,self.raster)

        # 2) Reflejo planar: la ciudad espejada en y=0 para las calles mojadas.
        set_srvs(ctx,0,2,(ctypes.c_void_p*2)(self.noise_srv.value,self.shadow_srv.value))
        set_rts(ctx,1,(ctypes.c_void_p*1)(self.refl_rtv.value),self.refl_dsv)
        clear_rtv(ctx,self.refl_rtv,black)
        clear_dsv(ctx,self.refl_dsv,D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1.0,0)
        div=max(1,int(level.reflection_divisor))
        rvp=D3D11_VIEWPORT(0.0,0.0,float(self.refl_size[0]//div),float(self.refl_size[1]//div),0.0,1.0); set_vp(ctx,1,ctypes.byref(rvp))
        mirror=_mat_mul(_reflect_y(),vp_mat)
        self._draw(m['building'],level.building_instances,mirror,eye,t,4,level,render_pass=2,inst='buildings')
        self._draw(m['streetlight'],level.streetlight_instances,mirror,eye,t,5,level,render_pass=2,inst='streetlights')
        self._draw(m['vehicle'],level.vehicle_instances,mirror,eye,t,2,level,render_pass=2,inst='vehicles')
        self._draw(m['sky'],1,mirror,eye,t,6,level,depth_readonly=True,render_pass=2)
        self._draw(m['cloud'],level.cloud_instances,mirror,eye,t,3,level,blend=True,depth_readonly=True,render_pass=2,inst='clouds')
        set_blend(ctx,None,no_blend,0xffffffff); set_depth(ctx,None,0)

        # 3) Escena en HDR (MSAA si hay soporte). Opacos -> cielo -> transparentes.
        set_rts(ctx,1,(ctypes.c_void_p*1)(self.hdr_rtv.value),self.dsv)
        clear_rtv(ctx,self.hdr_rtv,black)
        clear_dsv(ctx,self.dsv,D3D11_CLEAR_DEPTH|D3D11_CLEAR_STENCIL,1.0,0)
        vp=D3D11_VIEWPORT(0.0,0.0,float(self.width),float(self.height),0.0,1.0); set_vp(ctx,1,ctypes.byref(vp))
        set_srvs(ctx,0,3,(ctypes.c_void_p*3)(self.noise_srv.value,self.shadow_srv.value,self.refl_srv.value))
        self._draw(ground,1,vp_mat,eye,t,0,level)
        self._draw(m['building'],level.building_instances,vp_mat,eye,t,4,level,inst='buildings')
        self._draw(m['streetlight'],level.streetlight_instances,vp_mat,eye,t,5,level,inst='streetlights')
        self._draw(m['vehicle'],level.vehicle_instances,vp_mat,eye,t,2,level,inst='vehicles')
        self._draw(m['sky'],1,vp_mat,eye,t,6,level,depth_readonly=True)
        self._draw(m['cloud'],level.cloud_instances,vp_mat,eye,t,3,level,blend=True,depth_readonly=True,inst='clouds')
        self._draw(m['steam'],level.steam_instances,vp_mat,eye,t,8,level,blend=True,depth_readonly=True,inst='steam')
        # Restaura estados por claridad antes de Present.
        blend_factor=(FLOAT*4)(0,0,0,0)
        _com_method(self.context,CTX_OM_SET_BLEND_STATE,None,ctypes.c_void_p,ctypes.POINTER(FLOAT),UINT)(self.context,None,blend_factor,0xffffffff)
        try:
            _com_method(self.context,CTX_OM_SET_DEPTH_STENCIL_STATE,None,ctypes.c_void_p,UINT)(self.context,None,0)
        except RuntimeError:
            pass

        # 3) Post-proceso: resolver MSAA, bloom en cadena y composición ACES.
        set_srvs(ctx,0,3,no_srvs)
        if self.msaa_samples>1:
            _com_method(ctx,CTX_RESOLVE_SUBRESOURCE,None,ctypes.c_void_p,UINT,ctypes.c_void_p,UINT,UINT)(ctx,self.hdr_resolved,0,self.hdr_tex,0,DXGI_FORMAT_R16G16B16A16_FLOAT)
        _com_method(ctx,CTX_IA_SET_INPUT_LAYOUT,None,ctypes.c_void_p)(ctx,None)
        _com_method(ctx,CTX_VS_SET_SHADER,None,ctypes.c_void_p,ctypes.c_void_p,UINT)(ctx,self.post_vs,None,0)
        _com_method(ctx,CTX_PS_SET_SAMPLERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))(ctx,0,1,(ctypes.c_void_p*1)(self.linear_clamp.value))
        _com_method(ctx,CTX_PS_SET_CONSTANT_BUFFERS,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))(ctx,1,1,(ctypes.c_void_p*1)(self.post_cb.value))
        b0,b1,b2,b3,b4=self.bloom
        hdr_size=(self.width,self.height)
        self._post('PSBright',self.hdr_srv,hdr_size,b0)
        self._post('PSDown',b0[2],b0[3:5],b1)
        self._post('PSBlur',b1[2],b1[3:5],b2,axis=0.0)
        self._post('PSBlur',b2[2],b2[3:5],b1,axis=1.0)
        self._post('PSDown',b1[2],b1[3:5],b3)
        self._post('PSBlur',b3[2],b3[3:5],b4,axis=0.0)
        self._post('PSBlur',b4[2],b4[3:5],b3,axis=1.0)
        self._post('PSComposite',self.hdr_srv,hdr_size,None,extra=(b1[2],b3[2]))
        set_srvs(ctx,0,3,no_srvs)
        if timer_slot is not None:
            gpu_timer.end_frame(timer_slot)
        # VSync OFF (sync interval 0). CPU frametime mide el bucle presentado;
        # GPU frametime V14 usa timestamp queries dentro del command stream.
        self._present()
        # V14: GetData y ShowWindow quedan fuera de la región cronometrada cuando
        # el caller usa prepare_timed_frame(). El return se conserva por compatibilidad.
        if show_after_present:
            self._show_if_ready()
        return []

    def _post(self, shader, src_srv, src_size, target, axis=0.0, extra=()):
        """Una pasada a pantalla completa. ``target`` None = backbuffer."""
        ctx=self.context
        set_srvs=_com_method(ctx,CTX_PS_SET_SHADER_RESOURCES,None,UINT,UINT,ctypes.POINTER(ctypes.c_void_p))
        set_srvs(ctx,0,3,(ctypes.c_void_p*3)())
        rtv,w,h=(self.rtv,self.width,self.height) if target is None else (target[1],target[3],target[4])
        _com_method(ctx,CTX_OM_SET_RENDER_TARGETS,None,UINT,ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p)(ctx,1,(ctypes.c_void_p*1)(rtv.value),None)
        vp=D3D11_VIEWPORT(0.0,0.0,float(w),float(h),0.0,1.0)
        _com_method(ctx,CTX_RS_SET_VIEWPORTS,None,UINT,ctypes.POINTER(D3D11_VIEWPORT))(ctx,1,ctypes.byref(vp))
        raw=struct.pack('<8f',1.0/src_size[0],1.0/src_size[1],0.0,0.0,BLOOM_THRESHOLD,BLOOM_INTENSITY,EXPOSURE,float(axis))
        buf=ctypes.create_string_buffer(raw)
        _com_method(ctx,CTX_UPDATE_SUBRESOURCE,None,ctypes.c_void_p,UINT,ctypes.c_void_p,ctypes.c_void_p,UINT,UINT)(ctx,self.post_cb,0,None,ctypes.cast(buf,LPVOID),0,0)
        views=[src_srv]+list(extra)
        set_srvs(ctx,0,len(views),(ctypes.c_void_p*len(views))(*[v.value for v in views]))
        _com_method(ctx,CTX_PS_SET_SHADER,None,ctypes.c_void_p,ctypes.c_void_p,UINT)(ctx,self.post_ps[shader],None,0)
        _com_method(ctx,CTX_DRAW,None,UINT,UINT)(ctx,3,0)

    def set_title(self,text):
        try:self.user32.SetWindowTextW(self.hwnd,str(text))
        except Exception:pass

    def close(self):
        if self.gpu_timer is not None:
            try:self.gpu_timer.close()
            except Exception:pass
            self.gpu_timer=None
        for m in list(self.ground_meshes.values())+list(self.meshes.values()):
            _release(getattr(m,'ib',None)); _release(getattr(m,'vb',None))
        for buf in getattr(self,'instances',{}).values():
            _release(buf)
        self.instances={}
        for tex,rtv,srv,_w,_h in getattr(self,'bloom',[]):
            _release(srv); _release(rtv); _release(tex)
        self.bloom=[]
        for shader in getattr(self,'post_ps',{}).values():
            _release(shader)
        self.post_ps={}
        for name in ('refl_srv','refl_rtv','refl_tex','refl_dsv','refl_depth','shadow_srv','shadow_dsv','shadow_tex','shadow_cmp','shadow_raster','hdr_srv','hdr_resolved','hdr_rtv','hdr_tex','post_cb','post_vs','linear_clamp'):
            _release(getattr(self,name,None)); setattr(self,name,ctypes.c_void_p())
        for name in ('depth_readonly','raster','blend','noise_srv','noise_tex','sampler','cbuffer','layout','ps','vs','dsv','depth_tex','rtv','context','device','swap'):
            _release(getattr(self,name,None)); setattr(self,name,ctypes.c_void_p())
        try:
            if self.hwnd:self.user32.DestroyWindow(self.hwnd)
        except Exception:pass
        try:
            if self.class_name and self.hinstance:self.user32.UnregisterClassW(self.class_name,self.hinstance)
        except Exception:pass
        self.hwnd=None


def _telemetry_brief(sampler):
    if not callable(sampler): return {}
    try:
        row=sampler() or {}
        out={}
        for key in ('gpu_temp','gpu_usage','gpu_clock_mhz','gpu_vram_used_mb','cpu_temp'):
            value=row.get(key)
            try: out[key]=float(value) if value is not None else None
            except Exception: out[key]=None
        return out
    except Exception:
        return {}


def run_directx_benchmark(profile: str='standard', *, width: int=RENDER_WIDTH, height: int=RENDER_HEIGHT, visible: bool=True, progress_callback: ProgressCallback=None, telemetry_sampler: TelemetrySampler=None, cancel_check: CancelCheck=None) -> dict:
    """Ejecuta Benchmark V29 con los perfiles y ventanas de medida de V26.

    Cada fase medida dura un número fijo de segundos de reloj de pared y la cámara/
    animación usa ese mismo reloj. FPS = frames presentados / segundos reales y
    frametime = intervalo entre Present consecutivos. La telemetría de sensores
    la toma el proceso principal de CorePulse, no este worker.
    """
    method=GPU_BENCHMARK_METHOD
    if platform.system()!='Windows':
        return {'kind':'GPU','status':'UNAVAILABLE','value':None,'unit':'FPS','provider':GPU_PROVIDER,'reason':'DirectX 11 sólo está disponible en Windows','benchmark_method':method}
    levels=profile_levels(profile)
    total=sum(s.warmup_seconds+s.settle_seconds+s.measure_seconds for s in levels) or 1.0
    renderer=None; started=time.perf_counter(); scene_rows=[]; elapsed_base=0.0; path_base=0.0; telemetry=[]
    try:
        renderer=D3D11Renderer(width,height,visible=visible)
        for idx,level in enumerate(levels):
            if callable(cancel_check) and cancel_check(): break
            if level.warmup_seconds > 0:
                renderer.set_title(f'CorePulse Benchmark {GPU_BENCHMARK_LABEL} — {level.label} — calentamiento')
                warm_start=time.perf_counter(); next_sample=warm_start; next_progress_warm=warm_start
                while time.perf_counter()-warm_start<level.warmup_seconds:
                    if renderer.cancelled or (callable(cancel_check) and cancel_check()): break
                    frame_t=time.perf_counter(); renderer.render_frame(level,path_base+(frame_t-warm_start),idx)
                    now=time.perf_counter()
                    if now>=next_sample:
                        telemetry.append({'scene':level.key,'phase':'warmup','timestamp':time.time(),**_telemetry_brief(telemetry_sampler)}); next_sample=now+0.5
                    frac=(elapsed_base+(now-warm_start))/total
                    if callable(progress_callback) and now >= next_progress_warm:
                        progress_callback(frac,f'GPU · {level.label}',f'Warm-up {now-warm_start:.1f}/{level.warmup_seconds:.1f} s · fuera de la medición')
                        next_progress_warm=now+0.10
                if renderer.cancelled or (callable(cancel_check) and cancel_check()): break
                elapsed_base += level.warmup_seconds

            # Settle temporal por escena: se ejecuta el workload definitivo antes de
            # abrir estadísticas. Esto vacía transiciones de caché/cola y evita que
            # el primer frame de una fase destruya artificialmente el 1% Low.
            renderer.set_title(f'CorePulse Benchmark {GPU_BENCHMARK_LABEL} — {level.label} — estabilizando')
            settle_start=time.perf_counter(); settle_frames=0
            while time.perf_counter()-settle_start<level.settle_seconds:
                if renderer.cancelled or (callable(cancel_check) and cancel_check()): break
                renderer.render_frame(level,path_base+level.warmup_seconds+(time.perf_counter()-settle_start),idx)
                settle_frames += 1
            if renderer.cancelled or (callable(cancel_check) and cancel_check()): break
            elapsed_base += level.settle_seconds

            # V14: prime fijo del camino de Present y del pipeline antes de abrir
            # queries/estadísticas. Se reporta, no se mezcla con los 49 s medidos.
            prime_frames=8
            prime_time=path_base+level.warmup_seconds+level.settle_seconds
            for prime_idx in range(prime_frames):
                if renderer.cancelled or (callable(cancel_check) and cancel_check()): break
                renderer.render_frame(level,prime_time,idx,show_after_present=False)
                renderer.prepare_timed_frame()
            if renderer.cancelled or (callable(cancel_check) and cancel_check()): break

            renderer.set_title(f'CorePulse Benchmark {GPU_BENCHMARK_LABEL} — {level.label} — midiendo')
            frame_times=[]; submit_times=[]; renderer.begin_scene_gpu_timing(); next_sample=time.perf_counter()
            measured_render_s=0.0; measure_wall_start=time.perf_counter(); next_progress=measure_wall_start
            last_present_ns=None
            # V27: frametime = intervalo entre Present consecutivos (como
            # PresentMon/CapFrameX). V26 cronometraba sólo render+Present y
            # excluía el tiempo entre frames, mientras la GPU seguía trabajando:
            # la suma quedaba por debajo del reloj real y los FPS se inflaban
            # (hasta >5 % a 300+ FPS). Ahora FPS = frames / segundos reales.
            # El costo de envío CPU (render+Present) se informa aparte.
            while True:
                wall_elapsed=time.perf_counter()-measure_wall_start
                if wall_elapsed>=level.measure_seconds:
                    break
                if renderer.cancelled or (callable(cancel_check) and cancel_check()): break

                renderer.prepare_timed_frame()
                submit_start_ns=time.perf_counter_ns()
                scene_elapsed=min(wall_elapsed, level.measure_seconds)
                renderer.render_frame(
                    level,
                    path_base+level.warmup_seconds+level.settle_seconds+scene_elapsed,
                    idx,
                    gpu_timing=True,
                    show_after_present=False,
                    pump_messages=False,
                )
                present_ns=time.perf_counter_ns()
                submit_ms=(present_ns-submit_start_ns)/1_000_000.0
                if submit_ms>0.0 and math.isfinite(submit_ms):
                    submit_times.append(submit_ms)
                    measured_render_s += submit_ms/1000.0
                if last_present_ns is not None:
                    frame_ms=(present_ns-last_present_ns)/1_000_000.0
                    if frame_ms>0.0 and math.isfinite(frame_ms):
                        frame_times.append(frame_ms)
                last_present_ns=present_ns

                # Query readback y UI forman parte del intervalo entre Present,
                # igual que el trabajo de un juego entre frames.
                renderer.poll_gpu_timing()
                now=time.perf_counter()
                if now>=next_sample:
                    telemetry.append({'scene':level.key,'phase':'measure','timestamp':time.time(),**_telemetry_brief(telemetry_sampler)}); next_sample=now+0.45
                wall_elapsed=min(now-measure_wall_start, level.measure_seconds)
                frac=(elapsed_base+wall_elapsed)/total
                # La UI no debe bloquear un callback por frame. Se actualiza a 10 Hz
                # fuera del cronómetro para mantener movimiento visual fluido sin
                # alterar las estadísticas de render+Present.
                if callable(progress_callback) and now >= next_progress:
                    recent=frame_times[-240:]; fps=(len(recent)*1000.0/sum(recent)) if recent else None
                    progress_callback(frac,f'GPU · {level.label}',f'{fps:.1f} FPS · DirectX 11 · {renderer.adapter_name}' if fps else 'Midiendo frames reales…')
                    next_progress=now+0.10

            measure_wall_s=time.perf_counter()-measure_wall_start
            elapsed_base += level.measure_seconds
            gpu_times,gpu_meta=renderer.finish_scene_gpu_timing(timeout_s=4.0)
            st=_fps_stats(frame_times); gst=_gpu_time_stats(gpu_times,len(submit_times),gpu_meta.get('dropped',0),gpu_meta.get('disjoint',0)); workload=level_workload(level)
            cv=(statistics.pstdev(frame_times)/st['frametime_avg_ms']) if len(frame_times)>1 and st.get('frametime_avg_ms') else 0.0
            max_to_median=(max(frame_times)/st['frametime_median_ms']) if frame_times and st.get('frametime_median_ms') else None
            limit=_bottleneck(st.get('frametime_avg_ms'),gst.get('gpu_frame_time_avg_ms'),gst.get('gpu_sample_coverage'))
            scene_rows.append({
                'key':level.key,'label':level.label,'status':'CANCELLED' if renderer.cancelled or (callable(cancel_check) and cancel_check()) else 'OK',
                'api':'DirectX 11','feature_level':renderer.feature_level,'resolution':f'{renderer.width}x{renderer.height}','vsync':False,
                'warmup_seconds':level.warmup_seconds,'settle_seconds':level.settle_seconds,'settle_frames_discarded':settle_frames,'measurement_prime_frames_discarded':prime_frames,
                'measure_target_seconds':level.measure_seconds,'measured_seconds':min(measure_wall_s,level.measure_seconds),'measurement_wall_seconds':measure_wall_s,'render_present_accumulated_seconds':measured_render_s,'wall_clock_deterministic':True,
                'fps_method':'PRESENTED_FRAMES_DIV_WALLCLOCK','frametime_method':'PRESENT_TO_PRESENT_INTERVAL',
                'presented_frames':len(submit_times),
                'cpu_submit_avg_ms':(sum(submit_times)/len(submit_times)) if submit_times else None,
                **limit,
                'frames':st['frames'],'valid_frames':st['frames'],'frames_per_s':st['fps'],'one_percent_low_fps':st['one_percent_low_fps'],
                'frametime_avg_ms':st['frametime_avg_ms'],'frametime_median_ms':st.get('frametime_median_ms'),
                'frametime_p95_ms':st['frametime_p95_ms'],'frametime_p99_ms':st['frametime_p99_ms'],
                'frametime_spike_threshold_ms':st.get('frametime_spike_threshold_ms'),'frametime_spike_frames':st.get('frametime_spike_frames'),
                'frametime_spike_ratio':st.get('frametime_spike_ratio'),'frametime_cv':cv,'frametime_max_to_median_ratio':max_to_median,
                **gst,
                'gpu_frame_time_ms':gst.get('gpu_frame_time_avg_ms'),
                'gpu_frame_time_status':('MEASURED_D3D11_TIMESTAMP' if gst.get('gpu_samples') else ('N/A: '+str(renderer.gpu_timing_reason or 'sin muestras timestamp válidas'))),
                'workload':workload,
            })
            path_base += level.warmup_seconds + level.settle_seconds + level.measure_seconds
            if scene_rows[-1]['status']!='OK': break
        status='CANCELLED' if renderer.cancelled or (callable(cancel_check) and cancel_check()) else ('OK' if scene_rows and all(r['status']=='OK' for r in scene_rows) else 'PARTIAL')
        primary=next((r for r in scene_rows if r['key']=='megacity'),None) or (scene_rows[-1] if scene_rows else None)
        if callable(progress_callback): progress_callback(1.0,'GPU completado' if status=='OK' else 'GPU cancelado',f'{renderer.adapter_name} · DirectX 11')
        return {
            'kind':'GPU','status':status,'value':(primary or {}).get('frames_per_s'),'unit':'FPS','provider':GPU_PROVIDER,
                'benchmark_method':method,'benchmark_mode':f'VISIBLE_NEON_CITY_{GPU_BENCHMARK_LABEL}_WALLCLOCK_DETERMINISTIC',
                'scene_art_revision':'NEON_CITY_NIGHT_V1',
            'duration_s':time.perf_counter()-started,'api':'DirectX 11','feature_level':renderer.feature_level,'renderer':renderer.adapter_name,'dedicated_vram_mb':renderer.vram_mb,
            'resolution':f'{renderer.width}x{renderer.height}','vsync_disabled':True,'scenes':scene_rows,'scene_count':len(scene_rows),'telemetry_samples':telemetry,
            'render_resolution':f'{renderer.width}x{renderer.height}','window_resolution':f'{renderer.window_width}x{renderer.window_height}',
            'window_mode':('WINDOWED_NATIVE' if not renderer.fullscreen_window else 'BORDERLESS_FULLSCREEN_NATIVE' if (renderer.window_width,renderer.window_height)==(renderer.width,renderer.height) else 'BORDERLESS_FULLSCREEN_SCALED'),'dpi_awareness':renderer.dpi_awareness,
            'adapter_selection':renderer.adapter_info.get('selection'),'adapter_selection_reason':renderer.adapter_info.get('reason'),
            'adapters_detected':list(renderer.adapter_info.get('adapters') or []),
            'fps_method':'PRESENTED_FRAMES_DIV_WALLCLOCK','frametime_method':'PRESENT_TO_PRESENT_INTERVAL',
            'gpu_busy_ratio':(primary or {}).get('gpu_busy_ratio'),'bottleneck':(primary or {}).get('bottleneck'),
            'startup_stage':renderer.startup_stage,'startup_checks':list(renderer.startup_checks),
            'primary_scene':(primary or {}).get('key'),'frames_per_s':(primary or {}).get('frames_per_s'),'one_percent_low_fps':(primary or {}).get('one_percent_low_fps'),
            'frametime_avg_ms':(primary or {}).get('frametime_avg_ms'),'frametime_median_ms':(primary or {}).get('frametime_median_ms'),
            'frametime_p95_ms':(primary or {}).get('frametime_p95_ms'),'frametime_p99_ms':(primary or {}).get('frametime_p99_ms'),
            'frametime_spike_frames':(primary or {}).get('frametime_spike_frames'),'frametime_spike_ratio':(primary or {}).get('frametime_spike_ratio'),'frametime_cv':(primary or {}).get('frametime_cv'),'frametime_max_to_median_ratio':(primary or {}).get('frametime_max_to_median_ratio'),
            'gpu_frame_time_avg_ms':(primary or {}).get('gpu_frame_time_avg_ms'),'gpu_frame_time_p95_ms':(primary or {}).get('gpu_frame_time_p95_ms'),'gpu_frame_time_p99_ms':(primary or {}).get('gpu_frame_time_p99_ms'),
            'gpu_timestamp_samples':(primary or {}).get('gpu_samples'),'gpu_timestamp_coverage':(primary or {}).get('gpu_sample_coverage'),
            'gpu_timing_available':renderer.gpu_timing_available,'gpu_timing_reason':renderer.gpu_timing_reason,
            'policy':GPU_POLICY,
        }
    except Exception as exc:
        message=f'{type(exc).__name__}: {exc}'
        stage=getattr(renderer,'startup_stage',None) if renderer is not None else None
        if not stage:
            match=re.search(r'DirectX startup \[([^\]]+)\]', str(exc)); stage=match.group(1) if match else 'renderer_constructor'
        checks=list(getattr(renderer,'startup_checks',[]) or []) if renderer is not None else []
        return {'kind':'GPU','status':'ERROR','value':None,'unit':'FPS','provider':GPU_PROVIDER,'benchmark_method':method,'reason':message,'failure_stage':stage,'startup_checks':checks,'duration_s':time.perf_counter()-started,'policy':GPU_POLICY}
    finally:
        if renderer is not None:
            try: renderer.close()
            except Exception: pass

def gpu_profile_info(profile: str='standard') -> dict:
    levels=profile_levels(profile); seconds=sum(s.warmup_seconds+s.settle_seconds+s.measure_seconds for s in levels)
    return {
        'key':str(profile or 'standard').lower(),'label':f'DirectX 11 · Ciudad de neón {GPU_BENCHMARK_LABEL}','seconds':seconds,
        'resolution':f'{RENDER_WIDTH}x{RENDER_HEIGHT}','scene_count':len(levels),'prime_frames':8*len(levels),
        'warmup_policy':'5 s de warm-up global + settle temporal por escena + 8 prime frames por escena; todo excluido de estadísticas',
        'description':'Avenida de neón/Distrito financiero/Horizonte nocturno/Megaciudad: rascacielos con ventanas y pantallas, calles mojadas con reflejo planar, faroles, vehículos voladores, sombras de luna, HDR con MSAA y bloom; VSync OFF y timestamps GPU D3D11 auditados.',
    }


def _gpu_cli():
    """Worker isolated from QML: JSON-lines progress and single final result."""
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=('quick','standard','extended'), required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    # V29: escribir y vaciar stdout dentro del bucle medido metía pausas de
    # ~6 ms (1% Low clavado en ~165 FPS en escenas rápidas). Los avisos se
    # encolan y los imprime un hilo aparte, bloqueado casi siempre en E/S.
    import queue
    outbox = queue.SimpleQueue()
    def writer():
        while True:
            line = outbox.get()
            if line is None:
                return
            print(line, flush=True)
    printer = threading.Thread(target=writer, daemon=True, name='corepulse-gpu-progress')
    printer.start()

    def report(progress, name, detail):
        outbox.put(json.dumps({'event': 'progress', 'progress': max(0, min(100, int(float(progress) * 100))),
                               'stage': str(name), 'detail': str(detail)}, ensure_ascii=False))

    try:
        measured = run_directx_benchmark(args.profile, progress_callback=report)
    except BaseException as error:
        measured = {'kind': 'GPU', 'status': 'ERROR', 'value': None, 'reason': type(error).__name__ + ': ' + str(error)[:200],
                    'benchmark_method': GPU_BENCHMARK_METHOD, 'provider': GPU_PROVIDER}
    outbox.put(None)
    printer.join(timeout=3)
    from pathlib import Path
    def json_safe(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None  # REAL_OR_NA: non-finite timings are unavailable
        if isinstance(value, dict):
            return {str(k): json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [json_safe(v) for v in value]
        return value
    target = Path(args.output)
    with target.open('w', encoding='utf-8') as file:
        json.dump(json_safe(measured), file, ensure_ascii=False, allow_nan=False)
    print(json.dumps({'event': 'finished', 'status': measured.get('status','ERROR')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    _gpu_cli()
