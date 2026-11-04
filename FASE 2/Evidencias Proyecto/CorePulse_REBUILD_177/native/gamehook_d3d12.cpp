#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <atomic>
#include <d3d12.h>
#include <dxgi1_4.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "overlay_shared.h"
#include "vendor/kiero/kiero.h"
#include "vendor/kiero/examples/imgui/imgui/imgui.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_win32.h"
#include "vendor/kiero/examples/imgui/imgui/examples/imgui_impl_dx12.h"

// This module draws inside a Direct3D 12 game's own swap chain. No RTSS process
// or RTSS memory layout is used. Protected games may refuse module loading.
using PresentFn = HRESULT(__stdcall *)(IDXGISwapChain *, UINT, UINT);
using Present1Fn = HRESULT(__stdcall *)(IDXGISwapChain1 *, UINT, UINT, const DXGI_PRESENT_PARAMETERS *);
using ExecuteFn = void(__stdcall *)(ID3D12CommandQueue *, UINT, ID3D12CommandList *const *);
static PresentFn g_originalPresent = nullptr;
static Present1Fn g_originalPresent1 = nullptr;
static thread_local bool g_insidePresent1 = false;
static ExecuteFn g_originalExecute = nullptr;
static ID3D12CommandQueue *g_queue = nullptr;
static ID3D12Device *g_device = nullptr;
static IDXGISwapChain *g_swapchain = nullptr;
static ID3D12DescriptorHeap *g_rtvHeap = nullptr;
static ID3D12DescriptorHeap *g_srvHeap = nullptr;
static ID3D12GraphicsCommandList *g_commands = nullptr;
static ID3D12Fence *g_fence = nullptr;
static HANDLE g_fenceEvent = nullptr;
static UINT64 g_nextFence = 0;
static UINT g_rtvStride = 0;
static UINT g_bufferCount = 0;
static DXGI_FORMAT g_format = DXGI_FORMAT_UNKNOWN;
static const UINT MAX_BUFFERS = 16;
struct Frame { ID3D12CommandAllocator *allocator; UINT64 fence; };
static Frame g_frames[MAX_BUFFERS] = {};
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

static bool cleanup_renderer() {
    if (g_fence && g_nextFence && g_fence->GetCompletedValue() < g_nextFence) {
        if (!g_fenceEvent || FAILED(g_fence->SetEventOnCompletion(g_nextFence, g_fenceEvent)) ||
            WaitForSingleObject(g_fenceEvent, 100) != WAIT_OBJECT_0) return false;
    }
    g_imguiReady = false;
    if (g_panelPreviously) {
        ClipCursor(&g_previousClip);
        g_panelPreviously = false;
    }
    if (g_gameWindow && g_originalWndProc &&
        (WNDPROC)GetWindowLongPtrW(g_gameWindow, GWLP_WNDPROC) == game_window_proc)
        SetWindowLongPtrW(g_gameWindow, GWLP_WNDPROC, (LONG_PTR)g_originalWndProc);
    g_originalWndProc = nullptr;
    if (ImGui::GetCurrentContext()) {
        ImGui_ImplDX12_Shutdown();
        ImGui_ImplWin32_Shutdown();
        ImGui::DestroyContext();
    }
    if (g_commands) { g_commands->Release(); g_commands = nullptr; }
    for (Frame &frame : g_frames) {
        if (frame.allocator) frame.allocator->Release();
        frame = {};
    }
    if (g_srvHeap) { g_srvHeap->Release(); g_srvHeap = nullptr; }
    if (g_rtvHeap) { g_rtvHeap->Release(); g_rtvHeap = nullptr; }
    if (g_fence) { g_fence->Release(); g_fence = nullptr; }
    if (g_fenceEvent) { CloseHandle(g_fenceEvent); g_fenceEvent = nullptr; }
    if (g_device) { g_device->Release(); g_device = nullptr; }
    g_swapchain = nullptr;
    g_gameWindow = nullptr;
    g_bufferCount = 0;
    g_format = DXGI_FORMAT_UNKNOWN;
    g_nextFence = 0;
    return true;
}
static bool init_renderer(IDXGISwapChain *swapchain) {
    if (g_imguiReady) {
        DXGI_SWAP_CHAIN_DESC current = {};
        if (swapchain == g_swapchain && SUCCEEDED(swapchain->GetDesc(&current)) &&
            current.BufferCount == g_bufferCount && current.BufferDesc.Format == g_format)
            return true;
        if (!cleanup_renderer()) return false;
    } else if (g_device || g_rtvHeap || g_srvHeap || g_commands ||
               g_fence || g_fenceEvent || ImGui::GetCurrentContext()) {
        // A failed first initialization can leave partial GPU resources behind.
        if (!cleanup_renderer()) return false;
    }
    ULONGLONG now = GetTickCount64();
    if (now < g_nextInitMs) return false;
    g_nextInitMs = now + 1000;
    DXGI_SWAP_CHAIN_DESC desc = {};
    if (!g_queue || FAILED(swapchain->GetDesc(&desc)) || !desc.OutputWindow ||
        desc.BufferCount == 0 || desc.BufferCount > MAX_BUFFERS) return false;
    if (FAILED(swapchain->GetDevice(__uuidof(ID3D12Device), (void **)&g_device))) return false;
    ID3D12Device *queueDevice = nullptr;
    if (FAILED(g_queue->GetDevice(__uuidof(ID3D12Device), (void **)&queueDevice))) {
        g_device->Release(); g_device = nullptr; return false;
    }
    bool sameDevice = queueDevice == g_device;
    queueDevice->Release();
    if (!sameDevice) {
        if (g_actions) InterlockedExchange(&g_actions->error, 4);
        g_device->Release(); g_device = nullptr; return false;
    }
    g_swapchain = swapchain;
    g_bufferCount = desc.BufferCount;
    g_format = desc.BufferDesc.Format;
    g_gameWindow = desc.OutputWindow;
    D3D12_DESCRIPTOR_HEAP_DESC hd = {};
    hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
    hd.NumDescriptors = g_bufferCount;
    if (FAILED(g_device->CreateDescriptorHeap(&hd, __uuidof(ID3D12DescriptorHeap), (void **)&g_rtvHeap))) return false;
    g_rtvStride = g_device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
    hd = {};
    hd.Type = D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV;
    hd.NumDescriptors = 1;
    hd.Flags = D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE;
    if (FAILED(g_device->CreateDescriptorHeap(&hd, __uuidof(ID3D12DescriptorHeap), (void **)&g_srvHeap))) return false;
    for (UINT i = 0; i < g_bufferCount; ++i)
        if (FAILED(g_device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,
                        __uuidof(ID3D12CommandAllocator), (void **)&g_frames[i].allocator))) return false;
    if (FAILED(g_device->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT,
                  g_frames[0].allocator, nullptr,
                  __uuidof(ID3D12GraphicsCommandList), (void **)&g_commands))) return false;
    g_commands->Close();
    if (FAILED(g_device->CreateFence(0, D3D12_FENCE_FLAG_NONE, __uuidof(ID3D12Fence), (void **)&g_fence))) return false;
    g_fenceEvent = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (!g_fenceEvent) return false;
    ImGui::CreateContext();
    ImGui::StyleColorsDark();
    panel_init_fonts();
    if (!ImGui_ImplWin32_Init(g_gameWindow) ||
        !ImGui_ImplDX12_Init(g_device, (int)g_bufferCount, g_format, g_srvHeap,
                             g_srvHeap->GetCPUDescriptorHandleForHeapStart(),
                             g_srvHeap->GetGPUDescriptorHandleForHeapStart())) return false;
    g_originalWndProc = (WNDPROC)SetWindowLongPtrW(g_gameWindow, GWLP_WNDPROC, (LONG_PTR)game_window_proc);
    g_imguiReady = g_originalWndProc != nullptr;
    return g_imguiReady;
}
static void __stdcall hooked_execute(ID3D12CommandQueue *queue, UINT count, ID3D12CommandList *const *lists) {
    if (queue && !g_queue) {
        D3D12_COMMAND_QUEUE_DESC desc = queue->GetDesc();
        if (desc.Type == D3D12_COMMAND_LIST_TYPE_DIRECT) {
            queue->AddRef();
            if (InterlockedCompareExchangePointer((PVOID volatile *)&g_queue, queue, nullptr) != nullptr)
                queue->Release();
        }
    }
    g_originalExecute(queue, count, lists);
}
static void draw_to_swapchain(IDXGISwapChain *swapchain, const CorePulseOverlayState &snapshot) {
    if (!init_renderer(swapchain)) return;
    IDXGISwapChain3 *swap3 = nullptr;
    if (FAILED(swapchain->QueryInterface(__uuidof(IDXGISwapChain3), (void **)&swap3))) return;
    UINT index = swap3->GetCurrentBackBufferIndex();
    swap3->Release();
    if (index >= g_bufferCount) return;
    Frame &frame = g_frames[index];
    if (frame.fence && g_fence->GetCompletedValue() < frame.fence) {
        if (FAILED(g_fence->SetEventOnCompletion(frame.fence, g_fenceEvent)) ||
            WaitForSingleObject(g_fenceEvent, 100) != WAIT_OBJECT_0) return;
    }
    if (FAILED(frame.allocator->Reset()) || FAILED(g_commands->Reset(frame.allocator, nullptr))) return;
    ID3D12Resource *buffer = nullptr;
    if (FAILED(swapchain->GetBuffer(index, __uuidof(ID3D12Resource), (void **)&buffer))) {
        g_commands->Close(); return;
    }
    ImGui_ImplDX12_NewFrame();
    ImGui_ImplWin32_NewFrame();
    prepare_panel_mouse(snapshot);
    update_panel_mouse();
    ImGui::NewFrame();
    draw_overlay(snapshot);
    ImGui::EndFrame();
    ImGui::Render();
    D3D12_RESOURCE_BARRIER barrier = {};
    barrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource = buffer;
    barrier.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    barrier.Transition.StateBefore = D3D12_RESOURCE_STATE_PRESENT;
    barrier.Transition.StateAfter = D3D12_RESOURCE_STATE_RENDER_TARGET;
    g_commands->ResourceBarrier(1, &barrier);
    D3D12_CPU_DESCRIPTOR_HANDLE rtv = g_rtvHeap->GetCPUDescriptorHandleForHeapStart();
    rtv.ptr += (SIZE_T)index * g_rtvStride;
    g_device->CreateRenderTargetView(buffer, nullptr, rtv);
    g_commands->OMSetRenderTargets(1, &rtv, FALSE, nullptr);
    ID3D12DescriptorHeap *heaps[] = {g_srvHeap};
    g_commands->SetDescriptorHeaps(1, heaps);
    ImGui_ImplDX12_RenderDrawData(ImGui::GetDrawData(), g_commands);
    barrier.Transition.StateBefore = D3D12_RESOURCE_STATE_RENDER_TARGET;
    barrier.Transition.StateAfter = D3D12_RESOURCE_STATE_PRESENT;
    g_commands->ResourceBarrier(1, &barrier);
    buffer->Release();
    if (FAILED(g_commands->Close())) return;
    ID3D12CommandList *lists[] = {g_commands};
    g_queue->ExecuteCommandLists(1, lists);
    UINT64 next = ++g_nextFence;
    if (SUCCEEDED(g_queue->Signal(g_fence, next))) {
        frame.fence = next;
        InterlockedExchange(&g_actions->hookedPid, (LONG)GetCurrentProcessId());
        InterlockedExchange(&g_actions->frameTick, (LONG)(DWORD)GetTickCount64());
    }
}
static void on_present(IDXGISwapChain *swapchain) {
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
    if (!g_queue) return;
    draw_to_swapchain(swapchain, snapshot);
}
static void stabilize_swapchain(IDXGISwapChain *swapchain);
static HRESULT __stdcall hooked_present(IDXGISwapChain *swapchain, UINT syncInterval, UINT flags) {
    if (!g_insidePresent1) on_present(swapchain);
    HRESULT result = g_originalPresent(swapchain, syncInterval, flags);
    stabilize_swapchain(swapchain);
    return result;
}
static HRESULT __stdcall hooked_present1(IDXGISwapChain1 *swapchain, UINT syncInterval,
                                         UINT flags, const DXGI_PRESENT_PARAMETERS *parameters) {
    on_present(swapchain);
    g_insidePresent1 = true;
    HRESULT result = g_originalPresent1(swapchain, syncInterval, flags, parameters);
    g_insidePresent1 = false;
    stabilize_swapchain(swapchain);
    return result;
}
static void stabilize_swapchain(IDXGISwapChain *swapchain) {
    if (!swapchain) return;
    void **original = *(void ***)swapchain;
    if (original[8] == (void *)hooked_present) return;
    // DXGI may restore an inline Present patch after its first presentation.
    // Keep this single swapchain routed to CorePulse without touching other
    // COM objects or changing the shared DXGI vtable.
    static volatile LONG allocated = 0;
    if (InterlockedIncrement(&allocated) > 32) return;
    const SIZE_T entries = 48; // covers the IDXGISwapChain4 interface slots
    void **copy = (void **)VirtualAlloc(nullptr, entries * sizeof(void *),
                                         MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!copy) return;
    memcpy(copy, original, entries * sizeof(void *));
    copy[8] = (void *)hooked_present;
    if (g_originalPresent1) copy[22] = (void *)hooked_present1;
    if (InterlockedCompareExchangePointer((PVOID volatile *)swapchain, copy, original) != original)
        VirtualFree(copy, 0, MEM_RELEASE);
}
static DWORD WINAPI setup_hook(void *) {
    QueryPerformanceFrequency(&g_frequency);
    connect_memory();
    for (int i = 0; i < 240; ++i) {
        if (GetModuleHandleW(L"d3d12.dll") && GetModuleHandleW(L"dxgi.dll")) break;
        Sleep(250);
    }
    if (kiero::init(kiero::RenderType::D3D12) == kiero::Status::Success) {
        bool okay = kiero::bind(54, (void **)&g_originalExecute, (void *)hooked_execute) == kiero::Status::Success;
        okay &= kiero::bind(140, (void **)&g_originalPresent, (void *)hooked_present) == kiero::Status::Success;
        if (kiero::getMethodsTable()[150])
            kiero::bind(150, (void **)&g_originalPresent1, (void *)hooked_present1);
        if (!okay && g_actions) InterlockedExchange(&g_actions->error, 1);
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
