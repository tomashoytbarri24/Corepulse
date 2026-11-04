#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include <d3d9.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "overlay_shared.h"
#include "vendor/kiero/kiero.h"
#include "vendor/kiero/examples/imgui/imgui/imgui.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_win32.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_dx9.h"

using PresentFn = HRESULT(__stdcall *)(IDirect3DDevice9 *, const RECT *, const RECT *, HWND, const RGNDATA *);
using EndSceneFn = HRESULT(__stdcall *)(IDirect3DDevice9 *);
using ResetFn = HRESULT(__stdcall *)(IDirect3DDevice9 *, D3DPRESENT_PARAMETERS *);
static PresentFn g_originalPresent = nullptr;
static EndSceneFn g_originalEndScene = nullptr;
static ResetFn g_originalReset = nullptr;
static HWND g_gameWindow = nullptr;
static WNDPROC g_originalWndProc = nullptr;
static HANDLE g_stateMap = nullptr;
static const CorePulseOverlayState *g_stateView = nullptr;
static HANDLE g_actionMap = nullptr;
static CorePulseOverlayActions *g_actions = nullptr;
static std::atomic<bool> g_imguiReady{false};
static std::atomic<bool> g_panelPreviously{false};
static volatile LONG g_virtualMouseX = 0;
static volatile LONG g_virtualMouseY = 0;
static volatile LONG g_rawMouseSeen = 0;
static volatile LONG g_rawLeftDown = 0;
static volatile LONG g_rawRightDown = 0;
static volatile LONG g_rawWheel = 0;
static volatile LONG g_mouseMessageTick = 0;
static RECT g_previousClip = {};
static LARGE_INTEGER g_frequency = {};
static LARGE_INTEGER g_previousFrame = {};
static LARGE_INTEGER g_previousScene = {};
static double g_averageFrameMs = 0.0;
static double g_averageSceneMs = 0.0;
static volatile LONG g_lastPresentTick = 0;
static ULONGLONG g_nextInitMs = 0;

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND, UINT, WPARAM, LPARAM);
static bool is_input_message(UINT msg) {
    return msg == WM_INPUT || (msg >= WM_MOUSEFIRST && msg <= WM_MOUSELAST) ||
           msg == WM_KEYDOWN || msg == WM_KEYUP || msg == WM_CHAR ||
           msg == WM_SYSKEYDOWN || msg == WM_SYSKEYUP;
}
static LRESULT CALLBACK game_window_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    if (g_imguiReady) {
        if (g_panelPreviously && msg == WM_INPUT) {
            RAWINPUT input = {};
            UINT bytes = sizeof(input);
            if (GetRawInputData((HRAWINPUT)lp, RID_INPUT, &input, &bytes, sizeof(RAWINPUTHEADER)) == bytes &&
                input.header.dwType == RIM_TYPEMOUSE) {
                InterlockedExchange(&g_rawMouseSeen, 1);
                if (!(input.data.mouse.usFlags & MOUSE_MOVE_ABSOLUTE)) {
                    InterlockedExchangeAdd(&g_virtualMouseX, input.data.mouse.lLastX);
                    InterlockedExchangeAdd(&g_virtualMouseY, input.data.mouse.lLastY);
                }
                USHORT buttons = input.data.mouse.usButtonFlags;
                if (buttons & RI_MOUSE_LEFT_BUTTON_DOWN) InterlockedExchange(&g_rawLeftDown, 1);
                if (buttons & RI_MOUSE_LEFT_BUTTON_UP) InterlockedExchange(&g_rawLeftDown, 0);
                if (buttons & RI_MOUSE_RIGHT_BUTTON_DOWN) InterlockedExchange(&g_rawRightDown, 1);
                if (buttons & RI_MOUSE_RIGHT_BUTTON_UP) InterlockedExchange(&g_rawRightDown, 0);
                if (buttons & RI_MOUSE_WHEEL)
                    InterlockedExchangeAdd(&g_rawWheel, (SHORT)input.data.mouse.usButtonData);
            }
            return DefWindowProcW(hwnd, msg, wp, lp);
        }
        if (g_panelPreviously) {
            if (msg == WM_MOUSEMOVE && !g_rawMouseSeen) {
                InterlockedExchange(&g_virtualMouseX, (SHORT)LOWORD(lp));
                InterlockedExchange(&g_virtualMouseY, (SHORT)HIWORD(lp));
                InterlockedExchange(&g_mouseMessageTick, (LONG)(DWORD)GetTickCount64());
            }
            if (!g_rawMouseSeen && (msg == WM_LBUTTONDOWN || msg == WM_LBUTTONUP ||
                                     msg == WM_LBUTTONDBLCLK || msg == WM_RBUTTONDOWN ||
                                     msg == WM_RBUTTONUP || msg == WM_RBUTTONDBLCLK)) {
                InterlockedExchange(&g_virtualMouseX, (SHORT)LOWORD(lp));
                InterlockedExchange(&g_virtualMouseY, (SHORT)HIWORD(lp));
                InterlockedExchange(&g_mouseMessageTick, (LONG)(DWORD)GetTickCount64());
            }
            if (msg == WM_LBUTTONDOWN || msg == WM_LBUTTONDBLCLK)
                InterlockedExchange(&g_rawLeftDown, 1);
            else if (msg == WM_LBUTTONUP)
                InterlockedExchange(&g_rawLeftDown, 0);
            else if (msg == WM_RBUTTONDOWN || msg == WM_RBUTTONDBLCLK)
                InterlockedExchange(&g_rawRightDown, 1);
            else if (msg == WM_RBUTTONUP)
                InterlockedExchange(&g_rawRightDown, 0);
            else if (msg == WM_MOUSEWHEEL && !g_rawMouseSeen)
                InterlockedExchangeAdd(&g_rawWheel, GET_WHEEL_DELTA_WPARAM(wp));
        }
        if (g_panelPreviously && is_input_message(msg)) return 0;
    }
    return CallWindowProcW(g_originalWndProc, hwnd, msg, wp, lp);
}
static void update_panel_mouse() {
    if (!g_panelPreviously) return;
    ImGuiIO &io = ImGui::GetIO();
    if (!g_rawMouseSeen) {
        DWORD messageAge = (DWORD)GetTickCount64() - (DWORD)g_mouseMessageTick;
        if (g_mouseMessageTick && messageAge <= 100) {
            io.MousePos = ImVec2((float)g_virtualMouseX, (float)g_virtualMouseY);
        } else {
            POINT point = {};
            if (GetCursorPos(&point) && ScreenToClient(g_gameWindow, &point))
                io.MousePos = ImVec2((float)point.x, (float)point.y);
        }
        io.MouseDown[0] = g_rawLeftDown != 0;
        io.MouseDown[1] = g_rawRightDown != 0;
        io.MouseWheel += InterlockedExchange(&g_rawWheel, 0) / (float)WHEEL_DELTA;
        return;
    }
    LONG x = g_virtualMouseX, y = g_virtualMouseY;
    LONG maxX = (LONG)io.DisplaySize.x - 1;
    LONG maxY = (LONG)io.DisplaySize.y - 1;
    if (x < 0) x = 0; else if (x > maxX) x = maxX;
    if (y < 0) y = 0; else if (y > maxY) y = maxY;
    InterlockedExchange(&g_virtualMouseX, x);
    InterlockedExchange(&g_virtualMouseY, y);
    io.MousePos = ImVec2((float)x, (float)y);
    io.MouseDown[0] = g_rawLeftDown != 0;
    io.MouseDown[1] = g_rawRightDown != 0;
    io.MouseWheel += InterlockedExchange(&g_rawWheel, 0) / (float)WHEEL_DELTA;
}
static void connect_memory() {
    if (!g_stateView) {
        if (!g_stateMap) g_stateMap = OpenFileMappingA(FILE_MAP_READ, FALSE, COREPULSE_OVERLAY_STATE);
        if (g_stateMap) g_stateView = (const CorePulseOverlayState *)MapViewOfFile(g_stateMap, FILE_MAP_READ, 0, 0, sizeof(CorePulseOverlayState));
    }
    if (!g_actions) {
        if (!g_actionMap) g_actionMap = OpenFileMappingA(FILE_MAP_WRITE | FILE_MAP_READ, FALSE, COREPULSE_OVERLAY_ACTIONS);
        if (g_actionMap) g_actions = (CorePulseOverlayActions *)MapViewOfFile(g_actionMap, FILE_MAP_WRITE | FILE_MAP_READ, 0, 0, sizeof(CorePulseOverlayActions));
    }
}
static bool read_snapshot(CorePulseOverlayState *out) {
    connect_memory();
    if (!g_stateView || !g_actions) return false;
    static thread_local CorePulseOverlayState last = {};
    static thread_local ULONGLONG lastTick = 0;
    // Retry a concurrent telemetry write before deciding to skip a frame.
    for (int attempt = 0; attempt < 6; ++attempt) {
        LONG seqBefore = g_stateView->seqBegin;
        if (seqBefore & 1) { YieldProcessor(); continue; }
        MemoryBarrier();
        memcpy(out, g_stateView, sizeof(*out));
        MemoryBarrier();
        if (seqBefore != out->seqEnd || seqBefore != g_stateView->seqBegin) {
            YieldProcessor();
            continue;
        }
        if (out->magic != COREPULSE_OVERLAY_MAGIC || out->targetPid != GetCurrentProcessId()) return false;
        if (GetTickCount64() - out->tickMs > 3000) return false;
        if (!(out->flags & COREPULSE_OVERLAY_ENABLED)) return false;
        last = *out;
        lastTick = GetTickCount64();
        return true;
    }
    // A writer preempted mid-copy must not make the OSD blink off. Keep only
    // the last valid frame and only for the same process/mode for 500 ms.
    if (lastTick && GetTickCount64() - lastTick < 500 &&
        g_stateView->targetPid == GetCurrentProcessId() &&
        (g_stateView->flags & COREPULSE_OVERLAY_ENABLED) &&
        ((g_stateView->flags ^ last.flags) & (COREPULSE_OVERLAY_PANEL | COREPULSE_OVERLAY_DRAW)) == 0) {
        *out = last;
        return true;
    }
    return false;
}
static ImVec4 rgb_color(uint32_t rgb) {
    return ImVec4(((rgb >> 16) & 255) / 255.0f,
                  ((rgb >> 8) & 255) / 255.0f,
                  (rgb & 255) / 255.0f, 1.0f);
}

static void send_action(LONG code) {
    if (g_actions) InterlockedExchange(&g_actions->code, code);
}

#include "gamehook_ui.h"

static bool init_renderer(IDirect3DDevice9 *device) {
    if (g_imguiReady) return true;
    ULONGLONG now = GetTickCount64();
    if (now < g_nextInitMs) return false;
    g_nextInitMs = now + 1000;
    if (ImGui::GetCurrentContext()) {
        ImGui_ImplDX9_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    g_gameWindow = nullptr;
    D3DDEVICE_CREATION_PARAMETERS params = {};
    if (FAILED(device->GetCreationParameters(&params)) || !params.hFocusWindow) return false;
    g_gameWindow = params.hFocusWindow;
    ImGui::CreateContext();
    ImGui::StyleColorsDark();
    panel_init_fonts();
    if (!ImGui_ImplWin32_Init(g_gameWindow) || !ImGui_ImplDX9_Init(device)) return false;
    g_originalWndProc = (WNDPROC)SetWindowLongPtrW(g_gameWindow, GWLP_WNDPROC, (LONG_PTR)game_window_proc);
    g_imguiReady = g_originalWndProc != nullptr;
    return g_imguiReady;
}
static HRESULT __stdcall hooked_present(IDirect3DDevice9 *device, const RECT *source, const RECT *dest, HWND overrideWindow, const RGNDATA *dirty) {
    CorePulseOverlayState snapshot = {};
    if (read_snapshot(&snapshot)) {
        LARGE_INTEGER now = {}; QueryPerformanceCounter(&now);
        if (g_previousFrame.QuadPart && g_frequency.QuadPart) {
            double ms = (double)(now.QuadPart - g_previousFrame.QuadPart) * 1000.0 / g_frequency.QuadPart;
            if (ms > 0.1 && ms < 1000.0) {
                g_averageFrameMs = g_averageFrameMs ? g_averageFrameMs * 0.85 + ms * 0.15 : ms;
                InterlockedExchange(&g_actions->fpsMilli, (LONG)(1000000.0 / g_averageFrameMs));
                InterlockedExchange(&g_actions->fpsSource, 1);
            }
        }
        g_previousFrame = now;
        InterlockedExchange(&g_lastPresentTick, (LONG)(DWORD)GetTickCount64());
        if (!(snapshot.flags & COREPULSE_OVERLAY_DRAW)) {
            InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
            InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
        }
    }
    return g_originalPresent(device, source, dest, overrideWindow, dirty);
}
static HRESULT __stdcall hooked_end_scene(IDirect3DDevice9 *device) {
    CorePulseOverlayState snapshot = {};
    if (!read_snapshot(&snapshot)) {
        if (g_panelPreviously) {
            ClipCursor(&g_previousClip);
            g_panelPreviously = false;
        }
        return g_originalEndScene(device);
    }
    // Some D3D9/D3D9Ex devices bypass the base Present hook. EndScene gives a
    // usable estimate in that case, but multiple scenes per frame can differ
    // from true presented FPS; the controller labels this source explicitly.
    DWORD tick = (DWORD)GetTickCount64();
    if (tick - (DWORD)g_lastPresentTick > 1000) {
        LARGE_INTEGER now = {}; QueryPerformanceCounter(&now);
        if (g_previousScene.QuadPart && g_frequency.QuadPart) {
            double ms = (double)(now.QuadPart - g_previousScene.QuadPart) * 1000.0 / g_frequency.QuadPart;
            if (ms > 0.1 && ms < 1000.0) {
                g_averageSceneMs = g_averageSceneMs ? g_averageSceneMs * 0.85 + ms * 0.15 : ms;
                InterlockedExchange(&g_actions->fpsMilli, (LONG)(1000000.0 / g_averageSceneMs));
                InterlockedExchange(&g_actions->fpsSource, 2);
            }
        }
        g_previousScene = now;
    }
    if (!(snapshot.flags & COREPULSE_OVERLAY_DRAW)) {
        if (g_panelPreviously) { ClipCursor(&g_previousClip); g_panelPreviously = false; }
        InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
        InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
        return g_originalEndScene(device);
    }
    if (!init_renderer(device)) return g_originalEndScene(device);
    ImGui_ImplDX9_NewFrame();
    ImGui_ImplWin32_NewFrame();
    prepare_panel_mouse(snapshot);
    update_panel_mouse();
    ImGui::NewFrame();
    draw_overlay(snapshot);
    ImGui::EndFrame();
    ImGui::Render();
    ImGui_ImplDX9_RenderDrawData(ImGui::GetDrawData());
    InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
    InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
    return g_originalEndScene(device);
}
static HRESULT __stdcall hooked_reset(IDirect3DDevice9 *device, D3DPRESENT_PARAMETERS *params) {
    if (g_imguiReady) ImGui_ImplDX9_InvalidateDeviceObjects();
    HRESULT result = g_originalReset(device, params);
    if (SUCCEEDED(result) && g_imguiReady) ImGui_ImplDX9_CreateDeviceObjects();
    return result;
}
static DWORD WINAPI setup_hook(void *) {
    QueryPerformanceFrequency(&g_frequency);
    connect_memory();
    for (int i = 0; i < 240; ++i) {
        if (GetModuleHandleW(L"d3d9.dll")) break;
        Sleep(250);
    }
    if (kiero::init(kiero::RenderType::D3D9) == kiero::Status::Success) {
        bool okay = kiero::bind(16, (void **)&g_originalReset, (void *)hooked_reset) == kiero::Status::Success;
        okay &= kiero::bind(17, (void **)&g_originalPresent, (void *)hooked_present) == kiero::Status::Success;
        okay &= kiero::bind(42, (void **)&g_originalEndScene, (void *)hooked_end_scene) == kiero::Status::Success;
        if (!okay && g_actions) InterlockedExchange(&g_actions->error, 2);
    } else if (g_actions) InterlockedExchange(&g_actions->error, 3);
    return 0;
}
BOOL WINAPI DllMain(HINSTANCE module, DWORD reason, void *) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(module);
        HANDLE worker = CreateThread(nullptr, 0, setup_hook, nullptr, 0, nullptr);
        if (worker) CloseHandle(worker);
    }
    return TRUE;
}
