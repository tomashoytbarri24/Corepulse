"""WASAPI compartido, endpoint predeterminado multimedia; sin servicios externos.

Cada operación vive en su hilo COM y libera interfaces/buffers al terminar.
Enumerar no inicializa ni inicia un stream de captura o reproducción.
"""
import ctypes as C
import math
import os
import struct
import time
import uuid
from contextlib import contextmanager

P = C.c_void_p
U = C.c_uint32
H = C.c_int32


class AudioError(RuntimeError):
    pass


class GUID(C.Structure):
    _fields_ = [('data', C.c_ubyte * 16)]
    def __init__(self, value):
        super().__init__()
        self.data[:] = uuid.UUID(value).bytes_le


class Key(C.Structure):
    _fields_ = [('fmtid', GUID), ('pid', U)]


def checked(hr):
    if hr < 0:
        code = hr & 0xffffffff
        hint = ' Revisa los permisos de micrófono de Windows para aplicaciones de escritorio.' if code == 0x80070005 else ''
        raise AudioError(f'Windows Audio: HRESULT 0x{code:08X}.{hint}')


def call(ptr, index, types=(), args=()):
    table = C.cast(ptr, C.POINTER(C.POINTER(P))).contents
    result = C.WINFUNCTYPE(H, P, *types)(table[index])(ptr, *args)
    checked(result)
    return result


def release(ptr):
    if ptr:
        call(ptr, 2)


@contextmanager
def com():
    if os.name != 'nt':
        raise AudioError('Audio disponible sólo en Windows.')
    ole = C.OleDLL('ole32')
    ole.CoInitializeEx.argtypes = [P, U]
    ole.CoInitializeEx.restype = H
    ole.CoCreateInstance.argtypes = [P, P, U, P, C.POINTER(P)]
    ole.CoCreateInstance.restype = H
    ole.CoTaskMemFree.argtypes = [P]
    checked(ole.CoInitializeEx(None, 0))
    try:
        yield ole
    finally:
        ole.CoUninitialize()


ENUM_CLS = 'bcde0395-e52f-467c-8e3d-c4579291692e'
ENUM_IID = 'a95664d2-9614-4f35-a746-de8db63617e6'
CLIENT_IID = '1cb9ad4c-dbfa-4c32-b178-c2f568a703b2'
RENDER_IID = 'f294acfc-3146-4483-a7bf-addca7c260e2'
CAPTURE_IID = 'c8adbd64-e71e-48a0-a4de-185c395cd317'


@contextmanager
def endpoint(flow):
    with com() as ole:
        enum, device, client, fmt = P(), P(), P(), P()
        try:
            checked(ole.CoCreateInstance(C.byref(GUID(ENUM_CLS)), None, 23, C.byref(GUID(ENUM_IID)), C.byref(enum)))
            call(enum, 4, (U, U, C.POINTER(P)), (flow, 1, C.byref(device)))
            identity = P()
            call(device, 5, (C.POINTER(P),), (C.byref(identity),))
            try:
                device_id = C.wstring_at(identity)
            finally:
                ole.CoTaskMemFree(identity)
            store = P()
            name = None
            try:
                call(device, 4, (U, C.POINTER(P)), (0, C.byref(store)))
                # PROPVARIANT: 8-byte header followed by the pointer union.
                value = C.create_string_buffer(24)
                key = Key(GUID('a45c254e-df1c-4efd-8020-67d146a850e0'), 14)
                try:
                    call(store, 5, (P, P), (C.byref(key), C.byref(value)))
                    if C.c_uint16.from_buffer(value).value == 31:
                        address = P.from_buffer(value, 8).value
                        name = C.wstring_at(address) if address else None
                finally:
                    ole.PropVariantClear(C.byref(value))
            finally:
                release(store)
            call(device, 3, (P, U, P, C.POINTER(P)), (C.byref(GUID(CLIENT_IID)), 23, None, C.byref(client)))
            call(client, 8, (C.POINTER(P),), (C.byref(fmt),))
            raw = C.string_at(fmt, 18)
            extra = struct.unpack_from('<H', raw, 16)[0]
            spec = parse_format(C.string_at(fmt, 18 + extra))
            info = {'id': device_id, 'name': name or 'N/A', 'available': True, **spec}
            yield client, fmt, info
        finally:
            if fmt:
                ole.CoTaskMemFree(fmt)
            release(client)
            release(device)
            release(enum)


def parse_format(raw):
    tag, channels, rate, _, align, bits, extra = struct.unpack_from('<HHIIHHH', raw)
    mask = None
    if tag == 0xfffe and extra >= 22:
        mask = struct.unpack_from('<I', raw, 20)[0]
        subtype = uuid.UUID(bytes_le=raw[24:40])
        if subtype == uuid.UUID('00000003-0000-0010-8000-00aa00389b71'):
            tag = 3
        elif subtype == uuid.UUID('00000001-0000-0010-8000-00aa00389b71'):
            tag = 1
    stereo = channels == 2 and (mask is None or mask == 3)
    if channels > 2:
        stereo = mask is not None and mask & 3 == 3
    return {'channels': channels, 'rate': rate, 'bits': bits, 'align': align,
            'tag': tag, 'stereo': stereo, 'mask': mask}


def decode(raw, spec):
    bits, tag = spec['bits'], spec['tag']
    width = bits // 8
    if tag == 3 and bits == 32:
        return [max(-1., min(1., v[0])) if math.isfinite(v[0]) else 0.
                for v in struct.iter_unpack('<f', raw)]
    if tag == 1 and bits in (16, 24, 32):
        return [int.from_bytes(raw[i:i + width], 'little', signed=True) / (2 ** (bits - 1))
                for i in range(0, len(raw), width)]
    raise AudioError('Formato de audio no compatible: N/A; no se realizó la prueba.')


def encode(values, spec):
    bits, tag = spec['bits'], spec['tag']
    if tag == 3 and bits == 32:
        return b''.join(struct.pack('<f', x) for x in values)
    if tag == 1 and bits in (16, 24, 32):
        limit = 2 ** (bits - 1)
        return b''.join(int(max(-limit, min(limit - 1, x * limit))).to_bytes(bits // 8, 'little', signed=True) for x in values)
    raise AudioError('Formato de audio no compatible: N/A.')


def tone(spec, channel):
    if channel in ('left', 'right') and not spec['stereo']:
        raise AudioError('Prueba estéreo no disponible: N/A.')
    rate, channels = spec['rate'], spec['channels']
    count = int(rate * .65)
    values = []
    for i in range(count):
        envelope = min(1., i / max(1, rate * .02), (count - 1 - i) / max(1, rate * .02))
        value = .08 * envelope * math.sin(2 * math.pi * 440 * i / rate)
        values.extend(value if ((channel == 'left' and c == 0) or
                                (channel == 'right' and c == 1) or
                                (channel == 'both' and c < min(channels, 2))) else 0.
                      for c in range(channels))
    return encode(values, spec)


class WindowsAudio:
    def default_ids(self):
        """Sólo consulta identidad; no activa IAudioClient ni abre streams."""
        result = {}
        with com() as ole:
            enum = P()
            try:
                checked(ole.CoCreateInstance(C.byref(GUID(ENUM_CLS)), None, 23, C.byref(GUID(ENUM_IID)), C.byref(enum)))
                for label, flow in (('output', 0), ('input', 1)):
                    device, value = P(), P()
                    try:
                        call(enum, 4, (U, U, C.POINTER(P)), (flow, 1, C.byref(device)))
                        call(device, 5, (C.POINTER(P),), (C.byref(value),))
                        result[label] = C.wstring_at(value)
                    except Exception:
                        result[label] = None
                    finally:
                        if value:
                            ole.CoTaskMemFree(value)
                        release(device)
            finally:
                release(enum)
        return result

    def devices(self):
        result = {}
        for label, flow in (('output', 0), ('input', 1)):
            try:
                with endpoint(flow) as (_, __, info):
                    result[label] = info
            except Exception as exc:
                result[label] = {'available': False, 'id': None, 'name': 'N/A', 'error': str(exc)}
        return result

    @staticmethod
    def validate(info, expected):
        if info['id'] != expected:
            raise AudioError('Cambió el dispositivo predeterminado. Actualiza dispositivos y repite la prueba.')
        if not 1 <= info['channels'] <= 32 or not 8000 <= info['rate'] <= 384000:
            raise AudioError('Formato del dispositivo no evaluable: N/A.')
        if info['align'] != info['channels'] * (info['bits'] // 8):
            raise AudioError('Formato con alineación no compatible: N/A.')
        decode(bytes(info['align']), info)

    def play(self, channel, expected, cancel, recording=None):
        if cancel.is_set():
            raise AudioError('Prueba cancelada.')
        with endpoint(0) as (client, fmt, info):
            self.validate(info, expected)
            if recording is None:
                payload = tone(info, channel)
            else:
                source, rate = recording
                peak = max((abs(v) for v in source), default=0.)
                gain = min(1., .25 / peak) if peak else 1.
                values = []
                for i in range(int(len(source) * info['rate'] / rate)):
                    value = source[min(len(source) - 1, int(i * rate / info['rate']))] * gain
                    values.extend(value if c < min(2, info['channels']) else 0. for c in range(info['channels']))
                payload = encode(values, info)
            self._render(client, fmt, info, payload, cancel)

    def _render(self, client, fmt, info, payload, cancel):
        service = P()
        started = False
        try:
            if cancel.is_set():
                raise AudioError('Prueba cancelada.')
            call(client, 3, (U, U, C.c_int64, C.c_int64, P, P), (0, 0, 1000000, 0, fmt, None))
            call(client, 14, (P, C.POINTER(P)), (C.byref(GUID(RENDER_IID)), C.byref(service)))
            capacity, padding = U(), U()
            call(client, 4, (C.POINTER(U),), (C.byref(capacity),))
            cursor, total = 0, len(payload) // info['align']
            deadline = time.monotonic() + total / info['rate'] + 3
            while not cancel.is_set():
                if time.monotonic() > deadline:
                    raise AudioError('La reproducción no terminó dentro del tiempo esperado.')
                call(client, 6, (C.POINTER(U),), (C.byref(padding),))
                if cursor == total and padding.value == 0:
                    return
                count = min(capacity.value - padding.value, total - cursor)
                if count:
                    buffer = P()
                    call(service, 3, (U, C.POINTER(P)), (count, C.byref(buffer)))
                    block = payload[cursor * info['align']:(cursor + count) * info['align']]
                    C.memmove(buffer, block, len(block))
                    call(service, 4, (U, U), (count, 0))
                    cursor += count
                if not started:
                    if cancel.is_set():
                        raise AudioError('Prueba cancelada.')
                    call(client, 10)
                    started = True
                cancel.wait(.01)
            raise AudioError('Prueba cancelada.')
        finally:
            if started:
                try:
                    call(client, 11)
                except AudioError:
                    pass
            release(service)

    def record(self, expected, cancel, on_level):
        if cancel.is_set():
            raise AudioError('Grabación cancelada.')
        with endpoint(1) as (client, fmt, info):
            self.validate(info, expected)
            service, started = P(), False
            samples = []
            try:
                if cancel.is_set():
                    raise AudioError('Grabación cancelada.')
                call(client, 3, (U, U, C.c_int64, C.c_int64, P, P), (0, 0, 1000000, 0, fmt, None))
                call(client, 14, (P, C.POINTER(P)), (C.byref(GUID(CAPTURE_IID)), C.byref(service)))
                if cancel.is_set():
                    raise AudioError('Grabación cancelada.')
                call(client, 10)
                started = True
                limit = int(5 * info['rate'])
                deadline = time.monotonic() + 7
                while len(samples) < limit and not cancel.is_set():
                    if time.monotonic() > deadline:
                        raise AudioError('No se recibieron cinco segundos de audio. Revisa micrófono y permisos.')
                    packet = U()
                    call(service, 5, (C.POINTER(U),), (C.byref(packet),))
                    if not packet.value:
                        cancel.wait(.01)
                        continue
                    buffer, frames, flags = P(), U(), U()
                    call(service, 3, (C.POINTER(P), C.POINTER(U), C.POINTER(U), P, P),
                         (C.byref(buffer), C.byref(frames), C.byref(flags), None, None))
                    try:
                        raw = (bytes(frames.value * info['align']) if flags.value & 2 else
                               C.string_at(buffer, frames.value * info['align']))
                        values = decode(raw, info)
                        # Discontinuidad tras la primera entrega invalida la grabación.
                        if flags.value & 1 and samples:
                            raise AudioError('La captura tuvo una interrupción; repite la grabación.')
                        peak = max((abs(v) for v in values), default=0.)
                        on_level(peak)
                        mono = [sum(values[i:i + info['channels']]) / info['channels']
                                for i in range(0, len(values), info['channels'])]
                        samples.extend(mono[:limit - len(samples)])
                    finally:
                        call(service, 4, (U,), (frames.value,))
                if cancel.is_set():
                    samples.clear()
                    raise AudioError('Grabación cancelada.')
                return samples, info['rate']
            finally:
                if started:
                    try:
                        call(client, 11)
                    except AudioError:
                        pass
                release(service)


# V482: integrado sin cambiar algoritmos desde core/maintenance/audio_test.py
import copy
import json
import math
import os
import threading
import time
import uuid
from pathlib import Path

from core.runtime_paths import data_path

ANSWERS = {'Sí': 'VERIFICADO', 'No': 'PROBLEMA REPORTADO', 'No estoy seguro': 'NO CONCLUYENTE'}
RECENT_SECONDS = 24 * 3600


def empty_result(reason='Prueba guiada no realizada.'):
    return {'schema': 1, 'timestamp': None, 'devices': {}, 'technical': {},
            'answers': {}, 'status': 'NO EVALUADO', 'reason': reason}


def summary(result):
    answers = result.get('answers', {})
    if 'PROBLEMA REPORTADO' in answers.values():
        return 'PROBLEMA REPORTADO'
    if all(answers.get(key) == 'VERIFICADO' for key in ('left', 'right', 'both', 'microphone')):
        return 'AUDIO VERIFICADO'
    return 'VERIFICACIÓN PARCIAL' if answers else 'NO EVALUADO'


class AudioTest:
    def __init__(self, provider=None, path=None):
        self.provider = provider or WindowsAudio()
        self.path = Path(path) if path else data_path('audio_test_latest.json')
        self.result = empty_result()
        self.recording = None
        self.cancel = threading.Event()
        self.closed = False
        self.pending = None
        self.lock = threading.RLock()

    def save(self):
        with self.lock:
            self.result['status'] = summary(self.result)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
            try:
                temp.write_text(json.dumps(self.result, ensure_ascii=False), encoding='utf-8')
                os.replace(temp, self.path)
            finally:
                temp.unlink(missing_ok=True)

    def refresh(self):
        devices = self.provider.devices()
        with self.lock:
            if self.closed:
                return
            before = self.result.get('devices', {})
            if before and any(before.get(k, {}).get('id') != devices[k].get('id') for k in ('output', 'input')):
                self.clear_recording()
                self.result = empty_result('Cambió el dispositivo predeterminado; repite la prueba.')
                self.pending = None
                self.save()
            self.result['devices'] = devices
        return devices

    def clear_recording(self):
        if self.recording:
            self.recording[0].clear()
        self.recording = None

    def _begin(self, key, direction):
        if self.closed:
            raise AudioError('Prueba cerrada.')
        self.pending = None
        self.result['answers'].pop(key, None)
        self.result['technical'].pop(key, None)
        self.result['timestamp'] = time.time()
        self.save()  # Invalida el resultado anterior antes de iniciar otra carga.
        devices = self.refresh()
        info = devices[direction]
        if not info.get('available'):
            raise AudioError(info.get('error') or 'Dispositivo no disponible: N/A.')
        return info

    def play(self, key):
        info = self._begin(key, 'output')
        if key == 'microphone' and not self.recording:
            raise AudioError('Primero graba una prueba.')
        self.provider.play('both' if key == 'microphone' else key, info['id'], self.cancel,
                           recording=self.recording if key == 'microphone' else None)
        self._completed(key, {'api_completed': True})

    def record(self, on_level):
        self.clear_recording()
        self.result['technical'].pop('capture', None)
        info = self._begin('microphone', 'input')
        peak = 0.
        def level(value):
            nonlocal peak
            if math.isfinite(value):
                peak = max(peak, value)
                on_level(value)
        recording = self.provider.record(info['id'], self.cancel, level)
        if recording[1] <= 0 or len(recording[0]) < recording[1] * 4.5:
            recording[0].clear()
            raise AudioError('Grabación incompleta; repite la prueba.')
        with self.lock:
            if self.closed or self.cancel.is_set():
                recording[0].clear()
                raise AudioError('Grabación cancelada.')
            self.recording = recording
            self.result['technical']['capture'] = {'frames': len(recording[0]), 'sample_rate': recording[1],
                'duration_s': len(recording[0]) / recording[1], 'peak': peak,
                'signal_detected': peak > 0., 'completed': True}
            self.save()

    def _completed(self, key, technical):
        with self.lock:
            if self.closed or self.cancel.is_set():
                raise AudioError('Prueba cancelada.')
            self.result['technical'][key] = technical
            self.pending = key
            self.save()

    def confirm(self, answer):
        with self.lock:
            if self.closed or self.pending is None or answer not in ANSWERS:
                raise AudioError('No hay una reproducción finalizada pendiente de confirmación.')
            ids = self.provider.default_ids()
            if any(ids.get(k) != self.result['devices'].get(k, {}).get('id') for k in ('output', 'input')):
                self.result = empty_result('Cambió el dispositivo; confirmación descartada.')
                self.pending = None
                self.clear_recording()
                self.save()
                raise AudioError('Cambió el dispositivo predeterminado. Repite la prueba.')
            self.result['answers'][self.pending] = ANSWERS[answer]
            self.result['timestamp'] = time.time()
            self.pending = None
            self.save()

    def close(self):
        with self.lock:
            self.closed = True
            self.cancel.set()
            self.pending = None
            self.clear_recording()


def recent_audio_result(path=None, provider=None, now=None):
    """Consulta pasiva para Diagnóstico: jamás llama play/record/devices."""
    try:
        target = Path(path) if path else data_path('audio_test_latest.json')
        if not target.is_file():
            return empty_result()
        result = json.loads(target.read_text(encoding='utf-8'))
        age = (time.time() if now is None else now) - float(result.get('timestamp') or 0)
        if result.get('schema') != 1 or not 0 <= age <= RECENT_SECONDS:
            return empty_result('Sin prueba de las últimas 24 horas.')
        ids = (provider or WindowsAudio()).default_ids()
        if any(ids.get(k) != result.get('devices', {}).get(k, {}).get('id') for k in ('output', 'input')):
            return empty_result('Dispositivos predeterminados cambiados; repetir prueba.')
        # No confiar en el status persistido ni en confirmaciones sin ejecución.
        answers = result.get('answers', {})
        tech = result.get('technical', {})
        result['answers'] = {k: v for k, v in answers.items()
                             if k in ('left', 'right', 'both', 'microphone')
                             and v in ANSWERS.values() and tech.get(k, {}).get('api_completed')}
        if not tech.get('capture', {}).get('completed'):
            result['answers'].pop('microphone', None)
        result['status'] = summary(result)
        return copy.deepcopy(result)
    except Exception:
        return empty_result('Evidencia de audio no disponible o no verificable.')


def evidence_rows(result):
    result = result or empty_result()
    devices = result.get('devices', {})
    answers = result.get('answers', {})
    capture = result.get('technical', {}).get('capture', {})
    stereo = devices.get('output', {}).get('stereo')
    return [('Salida', devices.get('output', {}).get('name') or 'N/A'),
            ('Canal izquierdo', answers.get('left', 'N/A' if stereo is False else 'NO EVALUADO')),
            ('Canal derecho', answers.get('right', 'N/A' if stereo is False else 'NO EVALUADO')),
            ('Ambos canales', answers.get('both', 'NO EVALUADO')),
            ('Micrófono', devices.get('input', {}).get('name') or 'N/A'),
            ('Señal capturada', 'SÍ' if capture.get('signal_detected') else 'NO' if capture.get('completed') else 'N/A'),
            ('Pico de amplitud (0–1)', str(round(capture['peak'], 4)) if 'peak' in capture else 'N/A'),
            ('Reproducción del micrófono', answers.get('microphone', 'NO EVALUADO'))]
