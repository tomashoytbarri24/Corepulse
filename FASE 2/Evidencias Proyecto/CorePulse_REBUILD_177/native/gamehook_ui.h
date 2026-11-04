#pragma once
#include "brand_marks.h"

// Match the Windows GDI host's Segoe UI family and font weights.  Text is
// rasterized at 48 px, then drawn at the monitor-dependent display size;
// loading only the 16 px regular face was visibly blurry at 1440p.
// No font files are shipped or copied: Windows provides them in Fonts.
static ImFont *g_cpFontRegular = nullptr;
static ImFont *g_cpFontSemibold = nullptr;
static ImFont *g_cpFontBold = nullptr;

enum CorePulseFontWeight { CP_FONT_REGULAR, CP_FONT_SEMIBOLD, CP_FONT_BOLD };

static void panel_init_fonts() {
    ImGuiIO &io = ImGui::GetIO();
    char windowsDir[MAX_PATH] = {};
    const UINT length = GetWindowsDirectoryA(windowsDir, MAX_PATH);
    // The atlas always has a valid fallback, including on custom Windows
    // installations with missing fonts.
    ImFont *fallback = io.Fonts->AddFontDefault();
    g_cpFontRegular = fallback;
    g_cpFontSemibold = fallback;
    g_cpFontBold = fallback;
    if (length > 0 && length < MAX_PATH - 30) {
        char path[MAX_PATH] = {};
        snprintf(path, sizeof(path), "%s\\Fonts\\segoeui.ttf", windowsDir);
        if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) {
            if (ImFont *face = io.Fonts->AddFontFromFileTTF(path, 48.0f))
                g_cpFontRegular = face;
        }
        snprintf(path, sizeof(path), "%s\\Fonts\\seguisb.ttf", windowsDir);
        if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) {
            if (ImFont *face = io.Fonts->AddFontFromFileTTF(path, 48.0f))
                g_cpFontSemibold = face;
        }
        snprintf(path, sizeof(path), "%s\\Fonts\\segoeuib.ttf", windowsDir);
        if (GetFileAttributesA(path) != INVALID_FILE_ATTRIBUTES) {
            if (ImFont *face = io.Fonts->AddFontFromFileTTF(path, 48.0f))
                g_cpFontBold = face;
        }
    }
    if (g_cpFontSemibold == fallback) g_cpFontSemibold = g_cpFontRegular;
    if (g_cpFontBold == fallback) g_cpFontBold = g_cpFontSemibold;
    io.FontDefault = g_cpFontRegular;
}

static ImFont *panel_font(CorePulseFontWeight weight = CP_FONT_REGULAR) {
    ImFont *font = weight == CP_FONT_BOLD ? g_cpFontBold :
                   weight == CP_FONT_SEMIBOLD ? g_cpFontSemibold : g_cpFontRegular;
    return font ? font : ImGui::GetFont();
}

// Activate the software cursor and release game clipping before ImGui reads
// input on the very first panel frame.
static void prepare_panel_mouse(const CorePulseOverlayState &st) {
    const bool panel = (st.flags & COREPULSE_OVERLAY_PANEL) != 0;
    if (panel && !g_panelPreviously) {
        GetClipCursor(&g_previousClip);
        POINT point = {};
        GetCursorPos(&point);
        ScreenToClient(g_gameWindow, &point);
        InterlockedExchange(&g_virtualMouseX, point.x);
        InterlockedExchange(&g_virtualMouseY, point.y);
        InterlockedExchange(&g_rawMouseSeen, 0);
        InterlockedExchange(&g_rawLeftDown, 0);
        InterlockedExchange(&g_rawRightDown, 0);
        InterlockedExchange(&g_rawWheel, 0);
        InterlockedExchange(&g_mouseMessageTick, 0);
    }
    if (panel) ClipCursor(nullptr);
    if (!panel && g_panelPreviously) ClipCursor(&g_previousClip);
    g_panelPreviously = panel;
    ImGui::GetIO().MouseDrawCursor = panel;
}

// Shared presentation for every in-game graphics backend. Kept in one place so
// D3D9/10/11/12 and OpenGL have the same layout and mouse targets.
static float g_cpOsdAlpha = 1.0f;
static ImU32 panel_color(unsigned int rgb, int alpha = 255) {
    alpha = (int)(alpha*g_cpOsdAlpha);
    return IM_COL32((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, alpha);
}

static unsigned int panel_mix(unsigned int a, unsigned int b, int percent) {
    unsigned int r = (((a >> 16)&255)*(100-percent) + ((b >> 16)&255)*percent)/100;
    unsigned int g = (((a >> 8)&255)*(100-percent) + ((b >> 8)&255)*percent)/100;
    unsigned int blue = ((a&255)*(100-percent) + (b&255)*percent)/100;
    return (r << 16) | (g << 8) | blue;
}

static void panel_text(ImDrawList *draw, ImVec2 origin, float x, float y, float scale,
                       float size, ImU32 color, const char *value,
                       float clipLeft = -1.0f, float clipRight = -1.0f,
                       CorePulseFontWeight weight = CP_FONT_REGULAR) {
    if (!value) return;
    ImVec2 at(origin.x + x*scale, origin.y + y*scale);
    if (clipRight > clipLeft) {
        ImVec4 clip(origin.x + clipLeft*scale, at.y,
                    origin.x + clipRight*scale, at.y + size*scale + 3.0f);
        draw->AddText(panel_font(weight), size*scale, at, color, value, nullptr, 0.0f, &clip);
    } else {
        draw->AddText(panel_font(weight), size*scale, at, color, value);
    }
}

static void panel_text_right(ImDrawList *draw, ImVec2 origin, float right, float y,
                             float scale, float size, ImU32 color, const char *value,
                             CorePulseFontWeight weight = CP_FONT_BOLD) {
    if (!value) return;
    const float width = panel_font(weight)->CalcTextSizeA(size*scale, FLT_MAX, 0.0f, value).x;
    panel_text(draw, origin, right-width/scale, y, scale, size, color, value,
               -1.0f, -1.0f, weight);
}

static int panel_percent(const char *value) {
    if (!value || *value < '0' || *value > '9') return -1;
    int number = atoi(value);
    return number < 0 ? 0 : number > 100 ? 100 : number;
}

static void panel_progress(ImDrawList *draw, ImVec2 origin, float scale,
                           float x, float y, float width, const char *value,
                           unsigned int accent, unsigned int base) {
    ImVec2 start(origin.x+x*scale, origin.y+y*scale);
    ImVec2 end(origin.x+(x+width)*scale, origin.y+(y+4)*scale);
    draw->AddRectFilled(start, end, panel_color(panel_mix(base, 0x70849A, 35)), 3*scale);
    const int amount = panel_percent(value);
    if (amount > 0) {
        const float filled = width*amount/100.0f < 4 ? 4 : width*amount/100.0f;
        draw->AddRectFilled(start, ImVec2(origin.x+(x+filled)*scale, end.y),
                            panel_color(accent), 3*scale);
    }
}

// These masks are sampled from the exact AMD/NVIDIA paths used by Resumen.
static void panel_brand_mark(ImDrawList *draw, ImVec2 origin, float scale,
                             float x, float y, float width, float height,
                             const CorePulseBrandRun *runs, int count,
                             int sourceWidth, int sourceHeight) {
    const float sx = width * scale / sourceWidth;
    const float sy = height * scale / sourceHeight;
    for (int i = 0; i < count; ++i) {
        const CorePulseBrandRun &run = runs[i];
        const float left = origin.x + x*scale + run.x*sx;
        const float top = origin.y + y*scale + run.y*sy;
        draw->AddRectFilled(ImVec2(left, top),
                            ImVec2(left + run.width*sx + 0.15f,
                                   top + sy + 0.15f), IM_COL32_WHITE);
    }
}

// RAM and disk pictograms mirror the Segoe/GDI host, without depending on
// Unicode glyphs absent from the in-game font atlas.
static void panel_device_mark(ImDrawList *draw, ImVec2 badge, float scale,
                              const char *label, unsigned int accent) {
    const ImU32 white = IM_COL32_WHITE;
    const ImU32 ink = panel_color(accent);
    auto at = [badge, scale](float x, float y) {
        return ImVec2(badge.x + x*scale, badge.y + y*scale);
    };
    if (strcmp(label, "RAM") == 0) {
        draw->AddRectFilled(at(8,13), at(36,29), white, 3*scale);
        for (int i=0; i<4; ++i) {
            float x = 12.0f + i*6.0f;
            draw->AddLine(at(x,16), at(x,25), ink, 2*scale);
            draw->AddLine(at(x,29), at(x,33), white, 2*scale);
        }
    } else {
        draw->AddRectFilled(at(10,9), at(34,35), white, 4*scale);
        draw->AddRectFilled(at(14,14), at(30,30), ink, 8*scale);
        draw->AddRectFilled(at(20,20), at(24,24), white, 2*scale);
    }
}

static void panel_card(ImDrawList *draw, ImVec2 origin, float scale, float x, float width,
                       const char *label, const char *value, const char *name,
                       const char *detail, const char *brand, unsigned int accent,
                       unsigned int base) {
    const float y = 16.0f;
    const ImVec2 a(origin.x+x*scale, origin.y+y*scale);
    const ImVec2 b(origin.x+(x+width)*scale, origin.y+(y+112)*scale);
    draw->AddRectFilled(a, b, panel_color(panel_mix(base, accent, 44), 250), 20*scale);
    draw->AddRectFilled(ImVec2(a.x+scale,a.y+scale), ImVec2(b.x-scale,b.y-scale),
                        panel_color(panel_mix(base, accent, 13), 250), 19*scale);
    draw->AddLine(ImVec2(a.x+18*scale, a.y+2*scale),
                  ImVec2(b.x-18*scale, a.y+2*scale),
                  panel_color(panel_mix(base, accent, 47), 180), scale);
    ImVec2 badgeA(origin.x+(x+12)*scale, origin.y+(y+17)*scale);
    ImVec2 badgeB(origin.x+(x+56)*scale, origin.y+(y+61)*scale);
    draw->AddRectFilled(badgeA, badgeB, panel_color(accent), 11*scale);
    if (brand && _stricmp(brand, "AMD") == 0) {
        panel_brand_mark(draw, origin, scale, x+18, y+34, 32, 8,
                         COREPULSE_AMD_RUNS, COREPULSE_AMD_COUNT,
                         COREPULSE_AMD_WIDTH, COREPULSE_AMD_HEIGHT);
    } else if (brand && _stricmp(brand, "INTEL") == 0) {
        panel_text(draw, origin, x+18, y+31, scale, 12, IM_COL32_WHITE,
                   "intel", -1.0f, -1.0f, CP_FONT_BOLD);
    } else if (brand && _stricmp(brand, "NVIDIA") == 0) {
        panel_brand_mark(draw, origin, scale, x+19, y+24, 30, 30,
                         COREPULSE_NVIDIA_RUNS, COREPULSE_NVIDIA_COUNT,
                         COREPULSE_NVIDIA_WIDTH, COREPULSE_NVIDIA_HEIGHT);
    } else {
        panel_device_mark(draw, badgeA, scale, label, accent);
    }
    panel_text(draw, origin, x+66, y+13, scale, 14, panel_color(accent), label,
               -1.0f, -1.0f, CP_FONT_BOLD);
    panel_text_right(draw, origin, x+width-13, y+8, scale, 24,
                     panel_color(accent), value, CP_FONT_BOLD);
    ImVec2 nameAt(origin.x+(x+66)*scale, origin.y+(y+42)*scale);
    ImVec4 clip(nameAt.x, nameAt.y, origin.x+(x+width-12)*scale,
                origin.y+(y+72)*scale);
    draw->AddText(panel_font(), 12*scale, nameAt, IM_COL32(236,244,252,255),
                  name ? name : "N/A", nullptr, (width-78)*scale, &clip);
    panel_text(draw, origin, x+15, y+74, scale, 12, IM_COL32(170,188,207,255),
               detail, x+15, x+width-15);
    panel_progress(draw, origin, scale, x+15, y+98, width-30, value, accent, base);
}

static void draw_overlay(const CorePulseOverlayState &st) {
    ImGuiIO &io = ImGui::GetIO();
    const bool panel = (st.flags & COREPULSE_OVERLAY_PANEL) != 0;

    g_cpOsdAlpha = 1.0f;
    const unsigned int base = st.themeBase ? st.themeBase : 0x0F1828;
    const unsigned int depth = st.themeDepth ? st.themeDepth : 0x1B1025;
    const unsigned int accent = st.themeAccent ? st.themeAccent : 0x28B6EA;
    const unsigned int cyan = 0x27B6F0;
    const unsigned int teal = 0x37CBB8;
    const unsigned int muted = 0xAABCCF;
    const ImU32 white = IM_COL32(241,248,255,255);
    const ImGuiWindowFlags baseFlags = ImGuiWindowFlags_NoDecoration | ImGuiWindowFlags_NoMove |
        ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoFocusOnAppearing;
    const int count = st.planCount < 0 ? 0 : st.planCount > 4 ? 4 : st.planCount;
    float panelScale = io.DisplaySize.x * 0.82f / 1440.0f;
    if (panelScale < 0.8f) panelScale = 0.8f;
    if (panelScale > 2.2f) panelScale = 2.2f;
    if ((io.DisplaySize.x-24.0f)/1440.0f < panelScale)
        panelScale = (io.DisplaySize.x-24.0f)/1440.0f;
    const float safePanelWidth = 1440.0f * panelScale;
    const float panelHeight = 144.0f * panelScale;

    if (panel) {
        ImGui::SetNextWindowPos(ImVec2((io.DisplaySize.x - safePanelWidth) * 0.5f, 16.0f*panelScale), ImGuiCond_Always);
        ImGui::SetNextWindowSize(ImVec2(safePanelWidth, panelHeight), ImGuiCond_Always);
        ImGui::SetNextWindowBgAlpha(0.0f);
        ImGui::PushStyleColor(ImGuiCol_WindowBg, IM_COL32(0,0,0,0));
        ImGui::PushStyleColor(ImGuiCol_Border, rgb_color(panel_mix(base, accent, 48)));
        ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding, 24.0f*panelScale);
        ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
        ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0,0));
        ImGui::Begin("CorePulse##panel", nullptr, baseFlags);
        ImVec2 panelOrigin = ImGui::GetWindowPos();
        ImDrawList *draw = ImGui::GetWindowDrawList();
        panel_card(draw, panelOrigin, panelScale, 12, 276, "CPU", st.cpu, st.cpuName,
                   st.cpuTemp, st.cpuBrand, st.cpuRgb, base);
        panel_card(draw, panelOrigin, panelScale, 296, 276, "GPU", st.gpu, st.gpuName,
                   st.gpuTemp, st.gpuBrand, st.gpuRgb, base);
        panel_card(draw, panelOrigin, panelScale, 580, 190, "RAM", st.ram, st.ramInfo,
                   "Memoria física", "", 0x37CBB8, base);
        panel_card(draw, panelOrigin, panelScale, 778, 270, "DISCO", st.diskPercent,
                   st.diskName, st.diskInfo, "", 0xA66BD6, base);
        draw->AddRectFilled(ImVec2(panelOrigin.x+1052*panelScale, panelOrigin.y+4*panelScale),
                            ImVec2(panelOrigin.x+1436*panelScale, panelOrigin.y+32*panelScale),
                            panel_color(panel_mix(base, accent, 16), 245), 9*panelScale);
        panel_text(draw, panelOrigin, 1056, 11, panelScale, 14,
                   white, st.captureStatus[0]?st.captureStatus:"Perfiles de energía", 1056, 1400, CP_FONT_SEMIBOLD);
        for (int i = 0; i < count; ++i) {
            float px = 1056.0f+(i%2)*184.0f, py = 35.0f+(i/2)*28.0f;
            ImVec2 a(panelOrigin.x+px*panelScale, panelOrigin.y+py*panelScale);
            ImVec2 b(panelOrigin.x+(px+176)*panelScale, panelOrigin.y+(py+25)*panelScale);
            draw->AddRectFilled(a, b,
                                panel_color(panel_mix(base, st.plans[i].active ? accent : muted,
                                                      st.plans[i].active ? 30 : 12)), 9*panelScale);
            draw->AddRect(a, b,
                          panel_color(panel_mix(base, st.plans[i].active ? accent : muted,
                                                st.plans[i].active ? 62 : 30)), 9*panelScale);
            if (st.plans[i].active)
                draw->AddCircleFilled(ImVec2(a.x+10*panelScale, a.y+12*panelScale),
                                      2.5f*panelScale, panel_color(accent));
            panel_text(draw, panelOrigin, px+(st.plans[i].active ? 19 : 10), py+6,
                       panelScale, 12, st.plans[i].active ? white : panel_color(muted),
                       st.plans[i].name, px+9, px+167, CP_FONT_REGULAR);
            char id[32]; snprintf(id, sizeof(id), "plan%d##quick", i);
            ImGui::SetCursorPos(ImVec2(px*panelScale, py*panelScale));
            if (ImGui::InvisibleButton(id, ImVec2(176*panelScale, 25*panelScale)))
                send_action(100+i);
            if (ImGui::IsItemHovered())
                draw->AddRect(a, b, panel_color(accent), 9*panelScale, 0, 2*panelScale);
        }
        if (!count) panel_text(draw, panelOrigin, 1066, 48, panelScale, 12,
                               panel_color(muted), "Cargando perfiles...");
        const int actionX[3] = {1056, 1180, 1304};
        const int actionWidth[3] = {116, 116, 124};
        const unsigned int actionColor[3] = {teal, accent, cyan};
        const char *actionLabel[3] = {"RAM A FONDO", "REGISTRAR", "COREPULSE"};
        for (int i=0; i<3; ++i) {
            const int x = actionX[i];
            ImVec2 a(panelOrigin.x+x*panelScale, panelOrigin.y+99*panelScale);
            ImVec2 b(panelOrigin.x+(x+actionWidth[i])*panelScale, panelOrigin.y+127*panelScale);
            draw->AddRectFilled(a, b, panel_color(panel_mix(base, actionColor[i], 26)), 10*panelScale);
            draw->AddRect(a, b, panel_color(panel_mix(base, actionColor[i], 60)), 10*panelScale);
            panel_text(draw, panelOrigin, x+10, 106, panelScale, 12,
                       panel_color(panel_mix(0xFFFFFF, actionColor[i], 23)), actionLabel[i],
                       -1.0f, -1.0f, CP_FONT_SEMIBOLD);
        }
        draw->AddRectFilled(ImVec2(panelOrigin.x+1404*panelScale, panelOrigin.y+6*panelScale),
                            ImVec2(panelOrigin.x+1432*panelScale, panelOrigin.y+32*panelScale),
                            panel_color(panel_mix(base, muted, 23)), 9*panelScale);
        panel_text(draw, panelOrigin, 1412, 8, panelScale, 17, white, "×");
        const char *ids[3]={"RAM##quick","RECORD##quick","OPEN##quick"};
        const int codes[3]={2,4,3};
        for(int i=0;i<3;++i){
            ImGui::SetCursorPos(ImVec2(actionX[i]*panelScale,99*panelScale));
            if(ImGui::InvisibleButton(ids[i],ImVec2(actionWidth[i]*panelScale,28*panelScale)))send_action(codes[i]);
            if(ImGui::IsItemHovered())draw->AddRect(
                ImVec2(panelOrigin.x+actionX[i]*panelScale,panelOrigin.y+99*panelScale),
                ImVec2(panelOrigin.x+(actionX[i]+actionWidth[i])*panelScale,panelOrigin.y+127*panelScale),
                panel_color(actionColor[i]),10*panelScale,0,2*panelScale);
        }
        ImGui::SetCursorPos(ImVec2(1404*panelScale,6*panelScale));
        if (ImGui::InvisibleButton("CLOSE##quick", ImVec2(28*panelScale,26*panelScale))) send_action(1);
        if (ImGui::IsItemHovered())
            draw->AddRect(ImVec2(panelOrigin.x+1404*panelScale,panelOrigin.y+6*panelScale),
                          ImVec2(panelOrigin.x+1432*panelScale,panelOrigin.y+32*panelScale),
                          panel_color(muted), 9*panelScale, 0, 2*panelScale);
        ImGui::End();
        ImGui::PopStyleVar(3);
        ImGui::PopStyleColor(2);
        // The quick panel replaces the compact OSD until Shift+F2 closes it,
        // matching the external host and avoiding two surfaces on screen.
        return;
    }

    const bool compact = (st.flags & COREPULSE_OVERLAY_COMPACT) != 0;
    const CorePulseDesign d = cp_safe_design(st.design);
    const float sc = cp_osd_scale(io.DisplaySize.x,io.DisplaySize.y,d,compact);
    const float osdWidth=382*sc, osdHeight=cp_osd_height(compact,d.frametime)*sc;
    const float x=cp_osd_position(io.DisplaySize.x,osdWidth,sc,d.x);
    const float y=cp_osd_position(io.DisplaySize.y,osdHeight,sc,d.y);
    g_cpOsdAlpha=d.opacity/100.0f;
    ImGui::SetNextWindowPos(ImVec2(x,y),ImGuiCond_Always);
    ImGui::SetNextWindowSize(ImVec2(osdWidth,osdHeight),ImGuiCond_Always);
    ImGui::SetNextWindowBgAlpha(g_cpOsdAlpha);
    ImGui::PushStyleColor(ImGuiCol_WindowBg,rgb_color(panel_mix(base,depth,24)));
    ImGui::PushStyleColor(ImGuiCol_Border,IM_COL32(0,0,0,0));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,18*sc);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,0.0f);
    ImGui::Begin("CorePulse##osd",nullptr,baseFlags|ImGuiWindowFlags_NoInputs);
    const ImVec2 origin=ImGui::GetWindowPos();
    ImDrawList *draw=ImGui::GetWindowDrawList();
    const ImU32 text=panel_color(0xF1F8FF);
    panel_text(draw,origin,14,9,sc,17,text,"Core",-1,-1,CP_FONT_BOLD);
    panel_text(draw,origin,53,9,sc,17,panel_color(cyan),"Pulse",-1,-1,CP_FONT_BOLD);
    panel_text(draw,origin,132,13,sc,10,panel_color(teal),
               st.captureStatus[0]?st.captureStatus:"EN JUEGO",132,368);
    const char *labels[5]={"FPS","CPU","GPU","RAM","DISCO"};
    const char *values[5]={st.fps,st.cpu,st.gpu,st.ram,st.diskPercent};
    const char *detail[5]={"",st.cpuTemp,st.gpuTemp,"",""};
    const unsigned int colors[5]={cyan,st.cpuRgb,st.gpuRgb,teal,0xA66BD6};
    const float tileW=(354-(d.metricCount-1)*d.gap)/(float)d.metricCount;
    const float tileH=compact?52:70;
    for(int i=0;i<d.metricCount;++i){
        const int key=d.metricOrder[i]; const float bx=14+i*(tileW+d.gap);
        const ImVec2 a(origin.x+bx*sc,origin.y+40*sc);
        const ImVec2 b(origin.x+(bx+tileW)*sc,origin.y+(40+tileH)*sc);
        draw->AddRectFilled(a,b,panel_color(panel_mix(base,colors[key],12)),10*sc);
        panel_text(draw,origin,bx+8,47,sc,10,panel_color(colors[key]),labels[key]);
        panel_text(draw,origin,bx+8,62,sc,key==0?22:16,text,values[key],bx+8,bx+tileW-5,CP_FONT_BOLD);
        if(!compact && (st.flags&COREPULSE_OVERLAY_TEMPS))
            panel_text(draw,origin,bx+8,90,sc,10,panel_color(muted),detail[key],bx+8,bx+tileW-4);
    }
    if(d.frametime){
        const float top=40+tileH+12;
        float maximum=50;
        const int n=cp_clamp(st.frameCount,0,120);
        for(int i=0;i<n;++i) if(st.frameMs[i]>maximum) maximum=st.frameMs[i];
        char last[48];
        if(n)snprintf(last,sizeof(last),"Frametime  %.1f ms",st.frameMs[n-1]);
        else snprintf(last,sizeof(last),"Frametime  N/A");
        panel_text(draw,origin,14,top,sc,10,panel_color(muted),last);
        const float graphTop=top+19, graphH=44;
        for(int i=1;i<=2;++i){
            float gy=graphTop+graphH-(16.667f*i/maximum)*graphH;
            draw->AddLine(ImVec2(origin.x+14*sc,origin.y+gy*sc),ImVec2(origin.x+368*sc,origin.y+gy*sc),
                          panel_color(panel_mix(base,muted,22)),sc);
        }
        for(int i=1;i<n;++i){
            draw->AddLine(ImVec2(origin.x+(14+(i-1)*354.0f/(n-1))*sc,
                                origin.y+(graphTop+graphH-st.frameMs[i-1]/maximum*graphH)*sc),
                          ImVec2(origin.x+(14+i*354.0f/(n-1))*sc,
                                origin.y+(graphTop+graphH-st.frameMs[i]/maximum*graphH)*sc),
                          panel_color(cyan),1.5f*sc);
        }
        if(n<2)panel_text(draw,origin,14,graphTop+12,sc,10,panel_color(muted),"Sin fotogramas ETW recientes");
    }
    ImGui::End();
    ImGui::PopStyleVar(2); ImGui::PopStyleColor(2);
    g_cpOsdAlpha=1.0f;
}
