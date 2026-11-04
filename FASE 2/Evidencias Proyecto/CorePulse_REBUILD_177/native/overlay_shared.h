#pragma once
#include <windows.h>
#include <stdint.h>
#include "overlay_layout.h"

// Versioned, local-session IPC between the Python controller and the game renderer.
#define COREPULSE_OVERLAY_MAGIC 0x43504F34u
#define COREPULSE_OVERLAY_STATE "Local\\CorePulseOverlayStateV4"
#define COREPULSE_OVERLAY_ACTIONS "Local\\CorePulseOverlayActionsV4"
#define COREPULSE_OVERLAY_ENABLED 1u
#define COREPULSE_OVERLAY_PANEL 2u
#define COREPULSE_OVERLAY_TEMPS 4u
#define COREPULSE_OVERLAY_COMPACT 8u
#define COREPULSE_OVERLAY_DRAW 16u // fullscreen: render inside the game

#pragma pack(push, 1)
struct CorePulsePlan {
    char guid[64];
    char name[64];
    int32_t active;
};
struct CorePulseOverlayState {
    int32_t seqBegin;
    uint32_t magic;
    uint32_t targetPid;
    uint32_t flags;
    uint64_t tickMs;
    int32_t corner;
    char cpu[32];
    char gpu[32];
    char ram[32];
    char fps[32];
    char cpuTemp[32];
    char gpuTemp[32];
    uint32_t cpuRgb;
    uint32_t gpuRgb;
    char cpuName[96];
    char gpuName[96];
    char ramInfo[48];
    char diskName[96];
    char diskInfo[48];
    char diskPercent[16];
    char cpuBrand[16];
    char gpuBrand[16];
    uint32_t themeBase;
    uint32_t themeDepth;
    uint32_t themeAccent;
    int32_t planCount;
    CorePulsePlan plans[4];
    CorePulseDesign design;
    int32_t frameCount;
    float frameMs[120];
    char captureStatus[80];
    int32_t seqEnd;
};
#pragma pack(pop)
#ifdef __cplusplus
static_assert(sizeof(CorePulseOverlayState) == 1820, "CorePulse overlay IPC layout changed");
#endif
struct CorePulseOverlayActions {
    volatile LONG code; // 1 = close, 2 = RAM, 3 = open CorePulse, 100-103 = plan index
    volatile LONG hookedPid;
    volatile LONG error;
    volatile LONG fpsMilli; // FPS * 1000, from the in-game Present hook
    volatile LONG frameTick; // GetTickCount64 low 32 bits
    volatile LONG fpsSource; // 1 = Present/SwapBuffers, 2 = D3D9 EndScene estimate
};
