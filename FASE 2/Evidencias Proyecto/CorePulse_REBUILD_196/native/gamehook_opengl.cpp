#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include <GL/gl3w.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "overlay_shared.h"
#include "vendor/kiero/minhook/include/MinHook.h"
#include "vendor/kiero/examples/imgui/imgui/imgui.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_win32.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_opengl2.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_opengl3.h"

// This module draws into an OpenGL game's current context. No RTSS process
// or RTSS memory layout is used. Protected games may refuse module loading.
using SwapFn = BOOL(WINAPI *)(HDC);
static SwapFn g_originalGdiSwap = nullptr;
static SwapFn g_originalWglSwap = nullptr;
static HWND g_gameWindow = nullptr;
static WNDPROC g_originalWndProc = nullptr;
static HANDLE g_stateMap = nullptr;
static const CorePulseOverlayState *g_stateView = nullptr;
static HANDLE g_actionMap = nullptr;
static CorePulseOverlayActions *g_actions = nullptr;
static std::atomic<bool> g_imguiReady{false};
static std::atomic<bool> g_panelPreviously{false};
static bool g_useGl2 = false;
static HGLRC g_renderContext = nullptr;
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
static double g_averageFrameMs = 0.0;
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
        g_stateMap = OpenFileMappingA(FILE_MAP_READ, FALSE, COREPULSE_OVERLAY_STATE);
        if (g_stateMap)
            g_stateView = (const CorePulseOverlayState *)MapViewOfFile(g_stateMap, FILE_MAP_READ, 0, 0, sizeof(CorePulseOverlayState));
    }
    if (!g_actions) {
        g_actionMap = OpenFileMappingA(FILE_MAP_WRITE | FILE_MAP_READ, FALSE, COREPULSE_OVERLAY_ACTIONS);
        if (g_actionMap)
            g_actions = (CorePulseOverlayActions *)MapViewOfFile(g_actionMap, FILE_MAP_WRITE | FILE_MAP_READ, 0, 0, sizeof(CorePulseOverlayActions));
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

static bool init_renderer(HDC dc) {
    if (g_imguiReady) {
        bool sameSurface = wglGetCurrentContext() == g_renderContext &&
                           WindowFromDC(dc) == g_gameWindow;
        if (!sameSurface && g_actions) InterlockedExchange(&g_actions->error, 6);
        return sameSurface;
    }
    ULONGLONG now = GetTickCount64();
    if (now < g_nextInitMs) return false;
    g_nextInitMs = now + 1000;
    if (ImGui::GetCurrentContext()) {
        if (g_useGl2) ImGui_ImplOpenGL2_Shutdown();
        else ImGui_ImplOpenGL3_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    g_gameWindow = nullptr;
    if (!wglGetCurrentContext()) return false;
    // gl3w.h aliases glGetString to a function pointer. That pointer is null
    // until gl3wInit; resolve the OpenGL 1.1 export directly for this check.
    HMODULE glModule = GetModuleHandleW(L"opengl32.dll");
    using GetStringFn = const GLubyte *(APIENTRY *)(GLenum);
    GetStringFn getString = glModule ?
        (GetStringFn)GetProcAddress(glModule, "glGetString") : nullptr;
    const char *version = getString ? (const char *)getString(GL_VERSION) : nullptr;
    if (!version) return false;
    int major = atoi(version);
    if (major == 0 && strncmp(version, "OpenGL ES ", 10) == 0)
        major = atoi(version + 10);
    g_useGl2 = major < 3;
    if (!g_useGl2 && gl3wInit() != 0) return false;
    g_gameWindow = WindowFromDC(dc);
    if (!g_gameWindow) return false;
    ImGui::CreateContext();
    ImGui::StyleColorsDark();
    panel_init_fonts();
    if (!ImGui_ImplWin32_Init(g_gameWindow) ||
        !(g_useGl2 ? ImGui_ImplOpenGL2_Init() : ImGui_ImplOpenGL3_Init())) return false;
    g_originalWndProc = (WNDPROC)SetWindowLongPtrW(g_gameWindow, GWLP_WNDPROC, (LONG_PTR)game_window_proc);
    g_imguiReady = g_originalWndProc != nullptr;
    if (g_imguiReady) g_renderContext = wglGetCurrentContext();
    return g_imguiReady;
}
static void render_before_swap(HDC dc) {
    CorePulseOverlayState snapshot = {};
    if (!read_snapshot(&snapshot)) {
        if (g_panelPreviously) {
            ClipCursor(&g_previousClip);
            g_panelPreviously = false;
        }
        return;
    }
    LARGE_INTEGER now = {}; QueryPerformanceCounter(&now);
    if (g_previousFrame.QuadPart && g_frequency.QuadPart) {
        double ms = (double)(now.QuadPart - g_previousFrame.QuadPart) * 1000.0 / g_frequency.QuadPart;
        if (ms > 0.1 && ms < 1000.0) {
            g_averageFrameMs = g_averageFrameMs ? g_averageFrameMs * 0.85 + ms * 0.15 : ms;
            InterlockedExchange(&g_actions->fpsMilli, (LONG)(1000000.0 / g_averageFrameMs));
        }
    }
    g_previousFrame = now;
    if (!(snapshot.flags & COREPULSE_OVERLAY_DRAW)) {
        if (g_panelPreviously) { ClipCursor(&g_previousClip); g_panelPreviously = false; }
        InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
        InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
        return;
    }
    if (!init_renderer(dc)) return;
    if (g_useGl2) ImGui_ImplOpenGL2_NewFrame();
    else ImGui_ImplOpenGL3_NewFrame();
    ImGui_ImplWin32_NewFrame();
    prepare_panel_mouse(snapshot);
    update_panel_mouse();
    ImGui::NewFrame();
    draw_overlay(snapshot);
    ImGui::EndFrame();
    ImGui::Render();
    if (g_useGl2) ImGui_ImplOpenGL2_RenderDrawData(ImGui::GetDrawData());
    else ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
    InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
    InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
}
static thread_local int g_swapDepth = 0;
static BOOL WINAPI hooked_gdi_swap(HDC dc) {
    if (g_swapDepth++ == 0) render_before_swap(dc);
    BOOL result = g_originalGdiSwap(dc);
    --g_swapDepth;
    return result;
}
static BOOL WINAPI hooked_wgl_swap(HDC dc) {
    if (g_swapDepth++ == 0) render_before_swap(dc);
    BOOL result = g_originalWglSwap(dc);
    --g_swapDepth;
    return result;
}
static DWORD WINAPI setup_hook(void *) {
    QueryPerformanceFrequency(&g_frequency);
    connect_memory();
    for (int i = 0; i < 240; ++i) {
        if (GetModuleHandleW(L"opengl32.dll")) break;
        Sleep(250);
    }
    HMODULE gdi = GetModuleHandleW(L"gdi32.dll");
    HMODULE gl = GetModuleHandleW(L"opengl32.dll");
    void *gdiSwap = gdi ? (void *)GetProcAddress(gdi, "SwapBuffers") : nullptr;
    void *wglSwap = gl ? (void *)GetProcAddress(gl, "wglSwapBuffers") : nullptr;
    if (MH_Initialize() != MH_OK && g_actions) InterlockedExchange(&g_actions->error, 3);
    bool okay = false;
    if (gdiSwap && MH_CreateHook(gdiSwap, (void *)hooked_gdi_swap, (void **)&g_originalGdiSwap) == MH_OK)
        okay |= MH_EnableHook(gdiSwap) == MH_OK;
    if (wglSwap && wglSwap != gdiSwap &&
        MH_CreateHook(wglSwap, (void *)hooked_wgl_swap, (void **)&g_originalWglSwap) == MH_OK)
        okay |= MH_EnableHook(wglSwap) == MH_OK;
    if (!okay && g_actions) InterlockedExchange(&g_actions->error, 1);
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
