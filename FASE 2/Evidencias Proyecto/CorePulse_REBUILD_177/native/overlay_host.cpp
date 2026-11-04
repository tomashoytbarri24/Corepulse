// CorePulse Overlay Host: desktop/borderless renderer and mouse control.
// The exclusive-fullscreen renderer uses the same pipe protocol in a later module.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <dwmapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "brand_marks.h"
#include "overlay_layout.h"

#define WM_COREPULSE_UPDATE (WM_APP + 37)
#define MAX_PLANS 4

struct Plan { char guid[80]; char name[128]; int active; };
struct Snapshot {
    char mode[20];
    char corner[24];
    int compact;
    CorePulseDesign design;
    int frameCount; float frameMs[120];
    char captureStatus[80];
    char cpu[40], gpu[40], ram[40], fps[40];
    char cpuTemp[40], gpuTemp[40], status[220];
    char cpuName[96], gpuName[96], ramInfo[48], diskName[96];
    char diskInfo[48], diskPercent[24], cpuBrand[16], gpuBrand[16];
    COLORREF themeBase, themeDepth, themeAccent;
    COLORREF cpuColor, gpuColor;
    Plan plans[MAX_PLANS];
    int planCount;
};

static Snapshot g_state = {};
static CRITICAL_SECTION g_lock;
static HWND g_window = NULL;
static double g_scale = 1.0;
static int g_width = 352;
static int g_height = 114;
static int g_hoverTarget = -1;

static const int PANEL_WIDTH = 1440;
static const int PANEL_HEIGHT = 144;
static const int OSD_WIDTH = 382;
static const int OSD_COMPACT_HEIGHT = 106;
static const int OSD_FULL_HEIGHT = 130;

static void copy_text(char *dst, size_t capacity, const char *src) {
    if (!dst || capacity == 0) return;
    if (!src) src = "";
    strncpy_s(dst, capacity, src, _TRUNCATE);
}

static COLORREF parse_color(const char *value, COLORREF fallback) {
    if (!value || strlen(value) != 6) return fallback;
    char *end = NULL;
    unsigned long rgb = strtoul(value, &end, 16);
    if (!end || *end) return fallback;
    return RGB((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255);
}

static void utf8_text(HDC dc, int x, int y, const char *value) {
    if (!value) return;
    int needed = MultiByteToWideChar(CP_UTF8, 0, value, -1, NULL, 0);
    if (needed <= 0 || needed > 512) return;
    wchar_t wide[512];
    if (MultiByteToWideChar(CP_UTF8, 0, value, -1, wide, 512) > 0)
        TextOutW(dc, x * g_scale, y * g_scale, wide, needed - 1);
}

static void utf8_text_box(HDC dc, int x, int y, int width, const char *value) {
    if (!value) return;
    int needed = MultiByteToWideChar(CP_UTF8, 0, value, -1, NULL, 0);
    if (needed <= 0 || needed > 512) return;
    wchar_t wide[512];
    if (MultiByteToWideChar(CP_UTF8, 0, value, -1, wide, 512) <= 0) return;
    RECT box = {(int)(x*g_scale), (int)(y*g_scale),
                (int)((x+width)*g_scale), (int)((y+23)*g_scale)};
    DrawTextW(dc, wide, needed - 1, &box,
              DT_SINGLELINE | DT_VCENTER | DT_END_ELLIPSIS | DT_NOPREFIX);
}

static void utf8_text_right(HDC dc, int x, int y, int width, const char *value) {
    if (!value) return;
    int needed = MultiByteToWideChar(CP_UTF8, 0, value, -1, NULL, 0);
    if (needed <= 0 || needed > 512) return;
    wchar_t wide[512];
    if (MultiByteToWideChar(CP_UTF8, 0, value, -1, wide, 512) <= 0) return;
    RECT box = {(int)(x*g_scale), (int)(y*g_scale),
                (int)((x+width)*g_scale), (int)((y+28)*g_scale)};
    DrawTextW(dc, wide, needed - 1, &box,
              DT_SINGLELINE | DT_VCENTER | DT_RIGHT | DT_END_ELLIPSIS | DT_NOPREFIX);
}

static void utf8_text_wrap(HDC dc, int x, int y, int width, int height, const char *value) {
    if (!value) return;
    int needed = MultiByteToWideChar(CP_UTF8, 0, value, -1, NULL, 0);
    if (needed <= 0 || needed > 512) return;
    wchar_t wide[512];
    if (MultiByteToWideChar(CP_UTF8, 0, value, -1, wide, 512) <= 0) return;
    RECT box = {(int)(x*g_scale), (int)(y*g_scale),
                (int)((x+width)*g_scale), (int)((y+height)*g_scale)};
    DrawTextW(dc, wide, needed-1, &box, DT_WORDBREAK | DT_NOPREFIX);
}

static HFONT make_font(int pixels, int weight) {
    return CreateFontW(-pixels * g_scale, 0, 0, 0, weight, FALSE, FALSE, FALSE,
                       DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                       CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Segoe UI");
}

static void fill_round(HDC dc, int x1, int y1, int x2, int y2, int radius, COLORREF color) {
    HBRUSH brush = CreateSolidBrush(color);
    HGDIOBJ old = SelectObject(dc, brush);
    HPEN pen = CreatePen(PS_SOLID, 1, color);
    HGDIOBJ oldPen = SelectObject(dc, pen);
    RoundRect(dc, x1*g_scale, y1*g_scale, x2*g_scale, y2*g_scale,
              radius*g_scale, radius*g_scale);
    SelectObject(dc, oldPen);
    SelectObject(dc, old);
    DeleteObject(pen);
    DeleteObject(brush);
}

static void line(HDC dc, int x1, int y1, int x2, int y2, COLORREF color) {
    HPEN pen = CreatePen(PS_SOLID, g_scale, color);
    HGDIOBJ old = SelectObject(dc, pen);
    MoveToEx(dc, x1*g_scale, y1*g_scale, NULL);
    LineTo(dc, x2*g_scale, y2*g_scale);
    SelectObject(dc, old);
    DeleteObject(pen);
}

static COLORREF tint(COLORREF base, COLORREF accent, int percent) {
    return RGB((GetRValue(base)*(100-percent)+GetRValue(accent)*percent)/100,
               (GetGValue(base)*(100-percent)+GetGValue(accent)*percent)/100,
               (GetBValue(base)*(100-percent)+GetBValue(accent)*percent)/100);
}

static void gradient_round(HDC dc, int x1, int y1, int x2, int y2, int radius,
                           COLORREF from, COLORREF to) {
    HRGN clip = CreateRoundRectRgn((int)(x1*g_scale), (int)(y1*g_scale),
                                  (int)(x2*g_scale)+1, (int)(y2*g_scale)+1,
                                  (int)(radius*g_scale), (int)(radius*g_scale));
    SelectClipRgn(dc, clip);
    TRIVERTEX vertices[2] = {};
    vertices[0].x = (LONG)(x1*g_scale); vertices[0].y = (LONG)(y1*g_scale);
    vertices[0].Red = GetRValue(from) << 8; vertices[0].Green = GetGValue(from) << 8;
    vertices[0].Blue = GetBValue(from) << 8;
    vertices[1].x = (LONG)(x2*g_scale); vertices[1].y = (LONG)(y2*g_scale);
    vertices[1].Red = GetRValue(to) << 8; vertices[1].Green = GetGValue(to) << 8;
    vertices[1].Blue = GetBValue(to) << 8;
    GRADIENT_RECT area = {0, 1};
    GradientFill(dc, vertices, 2, &area, 1, GRADIENT_FILL_RECT_H);
    SelectClipRgn(dc, NULL);
    DeleteObject(clip);
}

static int percent_value(const char *value) {
    if (!value || *value < '0' || *value > '9') return -1;
    int number = atoi(value);
    return number < 0 ? 0 : number > 100 ? 100 : number;
}

static void metric_bar(HDC dc, int x, int y, int width, const char *value,
                       COLORREF accent, COLORREF base) {
    fill_round(dc, x, y, x+width, y+4, 4, tint(base, RGB(112,132,154), 35));
    const int amount = percent_value(value);
    if (amount > 0) {
        const int filled = width * amount / 100;
        fill_round(dc, x, y, x+(filled < 4 ? 4 : filled), y+4, 4, accent);
    }
}

static int panel_hit(int x, int y, int planCount) {
    if (x >= 1404 && x <= 1432 && y >= 6 && y <= 32) return 0;
    if (x >= 1056 && x <= 1172 && y >= 99 && y <= 127) return 1;
    if (x >= 1180 && x <= 1296 && y >= 99 && y <= 127) return 3;
    if (x >= 1304 && x <= 1428 && y >= 99 && y <= 127) return 2;
    for (int i=0; i<planCount; ++i) {
        int left = 1056 + (i%2)*184, top = 35 + (i/2)*28;
        if (x >= left && x <= left+176 && y >= top && y <= top+25) return 10+i;
    }
    return -1;
}

static void gdi_brand_mark(HDC dc, int x, int y, int width, int height,
                           const CorePulseBrandRun *runs, int count,
                           int sourceWidth, int sourceHeight) {
    HBRUSH brush = CreateSolidBrush(RGB(255,255,255));
    for (int i = 0; i < count; ++i) {
        const CorePulseBrandRun &run = runs[i];
        RECT rect = {
            (int)((x + width * (double)run.x / sourceWidth) * g_scale),
            (int)((y + height * (double)run.y / sourceHeight) * g_scale),
            (int)((x + width * (double)(run.x + run.width) / sourceWidth) * g_scale + 0.99),
            (int)((y + height * (double)(run.y + 1) / sourceHeight) * g_scale + 0.99)
        };
        FillRect(dc, &rect, brush);
    }
    DeleteObject(brush);
}

static void hardware_badge(HDC dc, int x, int y, COLORREF accent, const char *brand,
                           const char *kind) {
    fill_round(dc, x, y, x+44, y+44, 11, accent);
    HFONT badge = make_font(12, FW_BOLD);
    HGDIOBJ old = SelectObject(dc, badge);
    SetTextColor(dc, RGB(255,255,255));
    if (brand && _stricmp(brand, "INTEL") == 0) {
        utf8_text(dc, x+5, y+14, "intel");
    } else if (brand && _stricmp(brand, "AMD") == 0) {
        gdi_brand_mark(dc, x+6, y+19, 32, 8,
                       COREPULSE_AMD_RUNS, COREPULSE_AMD_COUNT,
                       COREPULSE_AMD_WIDTH, COREPULSE_AMD_HEIGHT);
    } else if (brand && _stricmp(brand, "NVIDIA") == 0) {
        gdi_brand_mark(dc, x+7, y+7, 30, 30,
                       COREPULSE_NVIDIA_RUNS, COREPULSE_NVIDIA_COUNT,
                       COREPULSE_NVIDIA_WIDTH, COREPULSE_NVIDIA_HEIGHT);
    } else if (kind && _stricmp(kind, "RAM") == 0) {
        fill_round(dc, x+8, y+13, x+36, y+29, 4, RGB(255,255,255));
        for (int i=0; i<4; ++i) line(dc, x+12+i*6, y+16, x+12+i*6, y+25, accent);
        for (int i=0; i<4; ++i) line(dc, x+12+i*6, y+29, x+12+i*6, y+33, RGB(255,255,255));
    } else {
        fill_round(dc, x+10, y+9, x+34, y+35, 4, RGB(255,255,255));
        fill_round(dc, x+14, y+14, x+30, y+30, 8, accent);
        fill_round(dc, x+20, y+20, x+24, y+24, 3, RGB(255,255,255));
    }
    SelectObject(dc, old); DeleteObject(badge);
}

static void hardware_card(HDC dc, int x, int y, int width, const char *title,
                          const char *value, const char *name, const char *detail,
                          const char *brand, COLORREF accent, COLORREF base) {
    fill_round(dc, x, y, x+width, y+112, 20, tint(base, accent, 44));
    gradient_round(dc, x+1, y+1, x+width-1, y+111, 19,
                   tint(base, accent, 18), tint(base, accent, 8));
    line(dc, x+18, y+2, x+width-18, y+2, tint(base, accent, 47));
    hardware_badge(dc, x+12, y+17, accent, brand, title);
    HFONT label = make_font(14, FW_BOLD);
    HFONT number = make_font(24, FW_BOLD);
    HFONT small = make_font(12, FW_NORMAL);
    HGDIOBJ old = SelectObject(dc, label);
    SetTextColor(dc, accent); utf8_text(dc, x+66, y+14, title);
    SelectObject(dc, number); utf8_text_right(dc, x+width-91, y+7, 79, value);
    SelectObject(dc, small);
    SetTextColor(dc, RGB(236,244,252)); utf8_text_wrap(dc, x+66, y+42, width-78, 31, name);
    SetTextColor(dc, RGB(170,188,207)); utf8_text_box(dc, x+15, y+74, width-30, detail);
    metric_bar(dc, x+15, y+98, width-30, value, accent, base);
    SelectObject(dc, old); DeleteObject(label); DeleteObject(number); DeleteObject(small);
}

static void paint_snapshot(HDC dc, const Snapshot &st) {
    const COLORREF white = RGB(241, 248, 255);
    const COLORREF muted = RGB(170, 188, 207);
    const COLORREF cyan = RGB(39, 182, 240);
    const COLORREF teal = RGB(55, 203, 184);
    const int panel = _stricmp(st.mode, "PANEL") == 0;
    const int surfaceHeight = panel ? PANEL_HEIGHT :
                              cp_osd_height(st.compact,st.design.frametime);
    const int surfaceWidth = panel ? PANEL_WIDTH : OSD_WIDTH;
    const COLORREF base = st.themeBase ? st.themeBase : RGB(15,24,40);
    const COLORREF depth = st.themeDepth ? st.themeDepth : RGB(27,16,37);
    const COLORREF accent = st.themeAccent ? st.themeAccent : cyan;
    SetBkMode(dc, TRANSPARENT);
    if (!panel) {
        gradient_round(dc, 0, 0, surfaceWidth, surfaceHeight, 20,
                       tint(base, accent, 12), tint(depth, base, 65));
    }
    HFONT title = make_font(18, FW_BOLD);
    HFONT body = make_font(14, FW_SEMIBOLD);
    HFONT small = make_font(11, FW_NORMAL);
    HGDIOBJ previous = SelectObject(dc, title);
    if (panel) {
        hardware_card(dc, 12, 16, 276, "CPU", st.cpu, st.cpuName, st.cpuTemp,
                      st.cpuBrand, st.cpuColor, base);
        hardware_card(dc, 296, 16, 276, "GPU", st.gpu, st.gpuName, st.gpuTemp,
                      st.gpuBrand, st.gpuColor, base);
        hardware_card(dc, 580, 16, 190, "RAM", st.ram, st.ramInfo, "Memoria física",
                      "", teal, base);
        hardware_card(dc, 778, 16, 270, "DISCO", st.diskPercent,
                      st.diskName, st.diskInfo, "", RGB(166,107,214), base);
        SelectObject(dc, body);
        fill_round(dc, 1052, 4, 1436, 32, 9, tint(base, accent, 16));
        SetTextColor(dc, white); utf8_text_box(dc,1056,8,340,st.captureStatus[0]?st.captureStatus:"Perfiles de energía");
        for (int i = 0; i < st.planCount; ++i) {
            int px = 1056 + (i%2)*184, py = 35 + (i/2)*28;
            const bool hover = g_hoverTarget == 10+i;
            COLORREF edge = st.plans[i].active || hover ? tint(base, accent, 62) : tint(base, muted, 30);
            fill_round(dc, px, py, px+176, py+25, 9, edge);
            fill_round(dc, px+1, py+1, px+175, py+24, 8,
                       st.plans[i].active || hover ? tint(base, accent, hover ? 39 : 30) : tint(base, muted, 12));
            if (st.plans[i].active) fill_round(dc, px+8, py+10, px+13, py+15, 4, accent);
            SelectObject(dc, small);
            SetTextColor(dc, st.plans[i].active ? white : muted);
            utf8_text_box(dc, px+(st.plans[i].active ? 19 : 10), py+2,
                          st.plans[i].active ? 148 : 157, st.plans[i].name);
        }
        if (!st.planCount) { SetTextColor(dc, muted); utf8_text(dc, 1066, 48, "Cargando perfiles..."); }
        const int actionX[3]={1056,1180,1304},actionW[3]={116,116,124},hover[3]={1,3,2};
        const COLORREF colors[3]={teal,accent,cyan};
        const char *labels[3]={"RAM A FONDO","REGISTRAR","COREPULSE"};
        HFONT actionFont=make_font(12,FW_SEMIBOLD);SelectObject(dc,actionFont);
        for(int i=0;i<3;++i){
            fill_round(dc,actionX[i],99,actionX[i]+actionW[i],127,10,tint(base,colors[i],g_hoverTarget==hover[i]?76:60));
            fill_round(dc,actionX[i]+1,100,actionX[i]+actionW[i]-1,126,9,tint(base,colors[i],g_hoverTarget==hover[i]?38:26));
            SetTextColor(dc,tint(RGB(255,255,255),colors[i],23));utf8_text(dc,actionX[i]+10,106,labels[i]);
        }
        SelectObject(dc,body);DeleteObject(actionFont);
        fill_round(dc, 1404, 6, 1432, 32, 9, tint(base, muted, g_hoverTarget == 0 ? 43 : 23));
        SetTextColor(dc, white); utf8_text(dc, 1413, 8, "×");
        SelectObject(dc, previous);
        DeleteObject(title); DeleteObject(body); DeleteObject(small);
        return;
    }
    const CorePulseDesign d=cp_safe_design(st.design);
    SetTextColor(dc,white); utf8_text(dc,14,9,"Core");
    SetTextColor(dc,cyan); utf8_text(dc,53,9,"Pulse");
    SelectObject(dc,small); SetTextColor(dc,teal);
    utf8_text_box(dc,132,9,236,st.captureStatus[0]?st.captureStatus:"EN JUEGO");
    const char *labels[5]={"FPS","CPU","GPU","RAM","DISCO"};
    const char *values[5]={st.fps,st.cpu,st.gpu,st.ram,st.diskPercent};
    const char *detail[5]={"",st.cpuTemp,st.gpuTemp,"",""};
    const COLORREF colors[5]={cyan,st.cpuColor,st.gpuColor,teal,RGB(166,107,214)};
    const double tileW=(354-(d.metricCount-1)*d.gap)/(double)d.metricCount;
    const int tileH=st.compact?52:70;
    for(int i=0;i<d.metricCount;++i){
        const int key=d.metricOrder[i],bx=(int)(14+i*(tileW+d.gap));
        fill_round(dc,bx,40,(int)(bx+tileW),40+tileH,10,tint(base,colors[key],12));
        SelectObject(dc,small); SetTextColor(dc,colors[key]); utf8_text(dc,bx+8,47,labels[key]);
        HFONT number=make_font(key==0?22:16,FW_BOLD);
        SelectObject(dc,number); SetTextColor(dc,white); utf8_text_box(dc,bx+8,60,(int)tileW-13,values[key]);
        SelectObject(dc,small); DeleteObject(number);
        if(!st.compact){ SetTextColor(dc,muted); utf8_text_box(dc,bx+8,86,(int)tileW-12,detail[key]); }
    }
    if(d.frametime){
        const int top=40+tileH+12, graphTop=top+19,graphH=44;
        float maximum=50; const int n=cp_clamp(st.frameCount,0,120);
        for(int i=0;i<n;++i)if(st.frameMs[i]>maximum)maximum=st.frameMs[i];
        char label[48];
        if(n)snprintf(label,sizeof(label),"Frametime  %.1f ms",st.frameMs[n-1]);
        else snprintf(label,sizeof(label),"Frametime  N/A");
        SelectObject(dc,small); SetTextColor(dc,muted); utf8_text(dc,14,top,label);
        for(int i=1;i<=2;++i){
            const int y=graphTop+graphH-(int)(16.667f*i/maximum*graphH);
            line(dc,14,y,368,y,tint(base,muted,22));
        }
        for(int i=1;i<n;++i)
            line(dc,14+(i-1)*354/(n-1),graphTop+graphH-(int)(st.frameMs[i-1]/maximum*graphH),
                    14+i*354/(n-1),graphTop+graphH-(int)(st.frameMs[i]/maximum*graphH),cyan);
        if(n<2)utf8_text(dc,14,graphTop+12,"Sin fotogramas ETW recientes");
    }
    SelectObject(dc, previous);
    DeleteObject(title); DeleteObject(body); DeleteObject(small);
}

static void position_window(HWND hwnd) {
    Snapshot copy;
    EnterCriticalSection(&g_lock); copy = g_state; LeaveCriticalSection(&g_lock);
    POINT point; GetCursorPos(&point);
    HWND foreground = GetForegroundWindow();
    HMONITOR monitor = foreground
        ? MonitorFromWindow(foreground, MONITOR_DEFAULTTONEAREST)
        : MonitorFromPoint(point, MONITOR_DEFAULTTONEAREST);
    MONITORINFO info = {}; info.cbSize = sizeof(info);
    GetMonitorInfoW(monitor, &info);
    typedef HRESULT (WINAPI *GetDpiForMonitorFn)(HMONITOR, int, UINT *, UINT *);
    HMODULE shcore = LoadLibraryW(L"shcore.dll");
    if (shcore) {
        GetDpiForMonitorFn getDpi = (GetDpiForMonitorFn)GetProcAddress(shcore, "GetDpiForMonitor");
        UINT xDpi = 96, yDpi = 96;
        if (getDpi && SUCCEEDED(getDpi(monitor, 0, &xDpi, &yDpi)))
            g_scale = xDpi > 0 ? (double)xDpi / 96.0 : 1.0;
        FreeLibrary(shcore);
    }
    const bool panel = _stricmp(copy.mode, "PANEL") == 0;
    const double monitorWidth = (double)(info.rcMonitor.right - info.rcMonitor.left);
    if (panel) {
        // Keep the controls readable at 1440p/4K even when Windows reports
        // 100% DPI or the game uses a resolution different from the desktop.
        g_scale = monitorWidth * 0.82 / PANEL_WIDTH;
        if (g_scale < 0.8) g_scale = 0.8;
        if (g_scale > 2.2) g_scale = 2.2;
        double fit = (monitorWidth - 24) / PANEL_WIDTH;
        if (fit > 0 && fit < g_scale) g_scale = fit;
    } else {
        g_scale=cp_osd_scale((float)monitorWidth,(float)(info.rcMonitor.bottom-info.rcMonitor.top),copy.design,copy.compact);
    }
    g_height=(int)((panel?PANEL_HEIGHT:cp_osd_height(copy.compact,copy.design.frametime))*g_scale);
    g_width=(int)((panel?PANEL_WIDTH:OSD_WIDTH)*g_scale);
    int x=panel ? info.rcMonitor.left+(int)((monitorWidth-g_width)/2) :
        info.rcMonitor.left+(int)cp_osd_position((float)monitorWidth,(float)g_width,(float)g_scale,copy.design.x);
    int y=panel ? info.rcMonitor.top+(int)(16*g_scale) :
        info.rcMonitor.top+(int)cp_osd_position((float)(info.rcMonitor.bottom-info.rcMonitor.top),
                                              (float)g_height,(float)g_scale,copy.design.y);
    SetLayeredWindowAttributes(hwnd,0,panel?242:(BYTE)(255*copy.design.opacity/100),LWA_ALPHA);
    RECT current = {};
    if (!GetWindowRect(hwnd, &current) || current.left != x || current.top != y ||
        current.right - current.left != g_width || current.bottom - current.top != g_height)
        SetWindowPos(hwnd, HWND_TOPMOST, x, y, g_width, g_height, SWP_NOACTIVATE);
}

static void region_chip(HRGN shape, int x1, int y1, int x2, int y2, int radius) {
    HRGN chip = CreateRoundRectRgn((int)(x1*g_scale), (int)(y1*g_scale),
                                   (int)(x2*g_scale)+1, (int)(y2*g_scale)+1,
                                   (int)(radius*g_scale), (int)(radius*g_scale));
    if (chip) {
        CombineRgn(shape, shape, chip, RGN_OR);
        DeleteObject(chip);
    }
}

// A disjoint window region keeps the game visible between the cards and
// controls. It also prevents the invisible gaps from occupying screen space.
static HRGN panel_region(int planCount) {
    HRGN shape = CreateRectRgn(0, 0, 0, 0);
    if (!shape) return NULL;
    region_chip(shape, 12, 16, 288, 128, 17);
    region_chip(shape, 296, 16, 572, 128, 17);
    region_chip(shape, 580, 16, 770, 128, 17);
    region_chip(shape, 778, 16, 1048, 128, 17);
    region_chip(shape, 1052, 4, 1436, 32, 9);
    for (int i = 0; i < planCount && i < MAX_PLANS; ++i) {
        const int x = 1056 + (i%2)*184, y = 35 + (i/2)*28;
        region_chip(shape, x, y, x+176, y+25, 9);
    }
    if (!planCount) region_chip(shape, 1056, 35, 1232, 62, 9);
    region_chip(shape,1056,99,1172,127,10);
    region_chip(shape,1180,99,1296,127,10);
    region_chip(shape,1304,99,1428,127,10);
    return shape;
}

static void update_window(HWND hwnd) {
    static bool shapeReady = false;
    static int shapedPanel = -1;
    static int shapedPlans = -1;
    Snapshot copy;
    EnterCriticalSection(&g_lock); copy = g_state; LeaveCriticalSection(&g_lock);
    if (_stricmp(copy.mode, "HIDDEN") == 0) {
        g_hoverTarget = -1;
        if (IsWindowVisible(hwnd)) ShowWindow(hwnd, SW_HIDE);
        return;
    }
    int panel = _stricmp(copy.mode, "PANEL") == 0;
    if (!panel) g_hoverTarget = -1;
    LONG_PTR style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE);
    LONG_PTR desired = panel ? style & ~WS_EX_TRANSPARENT : style | WS_EX_TRANSPARENT;
    if (desired != style) SetWindowLongPtrW(hwnd, GWL_EXSTYLE, desired);
    int oldWidth = g_width, oldHeight = g_height;
    position_window(hwnd);
    if (!shapeReady || oldWidth != g_width || oldHeight != g_height ||
        shapedPanel != panel || (panel && shapedPlans != copy.planCount)) {
        HRGN shape = panel ? panel_region(copy.planCount) :
            CreateRoundRectRgn(0, 0, g_width + 1, g_height + 1,
                               (int)(20*g_scale), (int)(20*g_scale));
        if (shape) {
            if (SetWindowRgn(hwnd, shape, TRUE)) {
                shapeReady = true;
                shapedPanel = panel;
                shapedPlans = copy.planCount;
            } else DeleteObject(shape);
        }
    }
    if (!IsWindowVisible(hwnd)) ShowWindow(hwnd, SW_SHOWNOACTIVATE);
    InvalidateRect(hwnd, NULL, FALSE);
}

static LRESULT CALLBACK window_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_MOUSEACTIVATE: return MA_NOACTIVATE;
    case WM_COREPULSE_UPDATE: update_window(hwnd); return 0;
    case WM_MOUSEMOVE: {
        Snapshot copy;
        EnterCriticalSection(&g_lock); copy = g_state; LeaveCriticalSection(&g_lock);
        if (_stricmp(copy.mode, "PANEL") != 0) return 0;
        TRACKMOUSEEVENT tracking = {sizeof(tracking), TME_LEAVE, hwnd, 0};
        TrackMouseEvent(&tracking);
        const int x = (short)LOWORD(lp) / g_scale, y = (short)HIWORD(lp) / g_scale;
        const int target = panel_hit(x, y, copy.planCount);
        if (target != g_hoverTarget) { g_hoverTarget = target; InvalidateRect(hwnd, NULL, FALSE); }
        return 0;
    }
    case WM_MOUSELEAVE:
        if (g_hoverTarget != -1) { g_hoverTarget = -1; InvalidateRect(hwnd, NULL, FALSE); }
        return 0;
    case WM_SETCURSOR:
        if (LOWORD(lp) == HTCLIENT && g_hoverTarget >= 0) {
            SetCursor(LoadCursor(NULL, IDC_HAND)); return TRUE;
        }
        return DefWindowProcW(hwnd, msg, wp, lp);
    case WM_LBUTTONUP: {
        Snapshot copy;
        EnterCriticalSection(&g_lock); copy = g_state; LeaveCriticalSection(&g_lock);
        if (_stricmp(copy.mode, "PANEL") != 0) return 0;
        int x = (short)LOWORD(lp) / g_scale;
        int y = (short)HIWORD(lp) / g_scale;
        const int target = panel_hit(x, y, copy.planCount);
        if (target == 0) { puts("CLOSE"); fflush(stdout); return 0; }
        if (target == 1) {
            puts("RAM"); fflush(stdout); return 0;
        }
        if (target == 2) {
            puts("OPEN"); fflush(stdout); return 0;
        }
        if(target==3){puts("RECORD");fflush(stdout);return 0;}
        if (target >= 10 && target < 10+copy.planCount) {
            printf("APPLY\t%s\n", copy.plans[target-10].guid); fflush(stdout); return 0;
        }
        return 0;
    }
    case WM_PAINT: {
        PAINTSTRUCT ps; HDC dc = BeginPaint(hwnd, &ps);
        HDC memory = CreateCompatibleDC(dc);
        HBITMAP bitmap = CreateCompatibleBitmap(dc, g_width, g_height);
        HGDIOBJ old = SelectObject(memory, bitmap);
        Snapshot copy;
        EnterCriticalSection(&g_lock); copy = g_state; LeaveCriticalSection(&g_lock);
        paint_snapshot(memory, copy);
        BitBlt(dc, 0, 0, g_width, g_height, memory, 0, 0, SRCCOPY);
        SelectObject(memory, old); DeleteObject(bitmap); DeleteDC(memory);
        EndPaint(hwnd, &ps); return 0;
    }
    case WM_CLOSE: DestroyWindow(hwnd); return 0;
    case WM_DESTROY: PostQuitMessage(0); return 0;
    default: return DefWindowProcW(hwnd, msg, wp, lp);
    }
}

static DWORD WINAPI input_loop(void *) {
    char line[4096];
    while (fgets(line, sizeof(line), stdin)) {
        char *context = NULL;
        char *cmd = strtok_s(line, "\t\r\n", &context);
        if (!cmd) continue;
        if (_stricmp(cmd, "QUIT") == 0) { PostMessageW(g_window, WM_CLOSE, 0, 0); break; }
        EnterCriticalSection(&g_lock);
        if (_stricmp(cmd, "MODE") == 0) {
            copy_text(g_state.mode, sizeof(g_state.mode), strtok_s(NULL, "\t\r\n", &context));
        } else if (_stricmp(cmd, "METRICS") == 0) {
            copy_text(g_state.cpu, sizeof(g_state.cpu), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.gpu, sizeof(g_state.gpu), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.ram, sizeof(g_state.ram), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.fps, sizeof(g_state.fps), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.cpuTemp, sizeof(g_state.cpuTemp), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.gpuTemp, sizeof(g_state.gpuTemp), strtok_s(NULL, "\t\r\n", &context));
            g_state.cpuColor = parse_color(strtok_s(NULL, "\t\r\n", &context), RGB(39,182,240));
            g_state.gpuColor = parse_color(strtok_s(NULL, "\t\r\n", &context), RGB(166,107,214));
            copy_text(g_state.status, sizeof(g_state.status), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.cpuName, sizeof(g_state.cpuName), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.gpuName, sizeof(g_state.gpuName), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.ramInfo, sizeof(g_state.ramInfo), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.diskName, sizeof(g_state.diskName), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.diskInfo, sizeof(g_state.diskInfo), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.diskPercent, sizeof(g_state.diskPercent), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.cpuBrand, sizeof(g_state.cpuBrand), strtok_s(NULL, "\t\r\n", &context));
            copy_text(g_state.gpuBrand, sizeof(g_state.gpuBrand), strtok_s(NULL, "\t\r\n", &context));
            g_state.themeBase = parse_color(strtok_s(NULL, "\t\r\n", &context), RGB(15,24,40));
            g_state.themeDepth = parse_color(strtok_s(NULL, "\t\r\n", &context), RGB(27,16,37));
            g_state.themeAccent = parse_color(strtok_s(NULL, "\t\r\n", &context), RGB(40,182,234));
        } else if (_stricmp(cmd, "CORNER") == 0) {
            copy_text(g_state.corner, sizeof(g_state.corner), strtok_s(NULL, "\t\r\n", &context));
        } else if (_stricmp(cmd, "OPTIONS") == 0) {
            char *compact = strtok_s(NULL, "\t\r\n", &context);
            g_state.compact = compact && atoi(compact) != 0;
        } else if (_stricmp(cmd,"DESIGN")==0) {
            CorePulseDesign d=cp_default_design();
            int *fields[5]={&d.scale,&d.opacity,&d.gap,&d.x,&d.y};
            for(int i=0;i<5;++i){ char *v=strtok_s(NULL,"\t\r\n",&context); if(v)*fields[i]=atoi(v); }
            char *order=strtok_s(NULL,"\t\r\n",&context),*orderContext=NULL;
            d.metricCount=0;
            if(order)for(char *part=strtok_s(order,",",&orderContext);part&&d.metricCount<5;part=strtok_s(NULL,",",&orderContext))
                d.metricOrder[d.metricCount++]=atoi(part);
            char *graph=strtok_s(NULL,"\t\r\n",&context); d.frametime=graph?atoi(graph):1;
            g_state.design=cp_safe_design(d);
        } else if (_stricmp(cmd,"FRAMES")==0) {
            char *items=strtok_s(NULL,"\t\r\n",&context),*parts=NULL;
            g_state.frameCount=0;
            if(items)for(char *v=strtok_s(items,",",&parts);v&&g_state.frameCount<120;v=strtok_s(NULL,",",&parts)){
                float ms=(float)atof(v); if(ms>0&&ms<10000)g_state.frameMs[g_state.frameCount++]=ms;
            }
        } else if (_stricmp(cmd,"CAPTURE")==0) {
            char *value=strtok_s(NULL,"\t\r\n",&context);
            copy_text(g_state.captureStatus,sizeof(g_state.captureStatus),value&&*value!=' '?value:"");
        } else if (_stricmp(cmd, "CLEARPLANS") == 0) {
            g_state.planCount = 0;
        } else if (_stricmp(cmd, "PLAN") == 0 && g_state.planCount < MAX_PLANS) {
            Plan *p = &g_state.plans[g_state.planCount++];
            copy_text(p->guid, sizeof(p->guid), strtok_s(NULL, "\t\r\n", &context));
            copy_text(p->name, sizeof(p->name), strtok_s(NULL, "\t\r\n", &context));
            p->active = atoi(strtok_s(NULL, "\t\r\n", &context) ?: "0");
        }
        LeaveCriticalSection(&g_lock);
        if (_stricmp(cmd, "MODE") == 0 || _stricmp(cmd, "CORNER") == 0)
            PostMessageW(g_window, WM_COREPULSE_UPDATE, 0, 0);
    }
    PostMessageW(g_window, WM_CLOSE, 0, 0);
    return 0;
}

int main(void) {
    InitializeCriticalSection(&g_lock);
    copy_text(g_state.mode, sizeof(g_state.mode), "HIDDEN");
    copy_text(g_state.corner, sizeof(g_state.corner), "top-right");
    g_state.compact = 1;
    g_state.design=cp_default_design();
    copy_text(g_state.cpu, sizeof(g_state.cpu), "N/A");
    copy_text(g_state.gpu, sizeof(g_state.gpu), "N/A");
    copy_text(g_state.ram, sizeof(g_state.ram), "N/A");
    copy_text(g_state.fps, sizeof(g_state.fps), "N/A");
    g_state.cpuColor = RGB(39,182,240); g_state.gpuColor = RGB(166,107,214);
    HMODULE user = GetModuleHandleW(L"user32.dll");
    typedef BOOL (WINAPI *SetDpiContextFn)(HANDLE);
    SetDpiContextFn setDpi = (SetDpiContextFn)GetProcAddress(user, "SetProcessDpiAwarenessContext");
    if (setDpi) setDpi((HANDLE)-4);
    WNDCLASSW wc = {}; wc.lpfnWndProc = window_proc; wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = L"CorePulseOverlayHost"; wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    if (!RegisterClassW(&wc)) return 2;
    g_window = CreateWindowExW(WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED,
                               wc.lpszClassName, L"CorePulse Overlay", WS_POPUP,
                               0, 0, 1, 1, NULL, NULL, wc.hInstance, NULL);
    if (!g_window) return 3;
    // Windows 11 adds its own light frame even to some borderless surfaces.
    const COLORREF noBorder = 0xFFFFFFFE; // DWMWA_COLOR_NONE
    const int ownCorners = 1; // DWMWCP_DONOTROUND; our region owns the shape.
    DwmSetWindowAttribute(g_window, 34, &noBorder, sizeof(noBorder));
    DwmSetWindowAttribute(g_window, 33, &ownCorners, sizeof(ownCorners));
    SetLayeredWindowAttributes(g_window, 0, 242, LWA_ALPHA);
    HANDLE reader = CreateThread(NULL, 0, input_loop, NULL, 0, NULL);
    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    if (reader) CloseHandle(reader);
    DeleteCriticalSection(&g_lock);
    return 0;
}


