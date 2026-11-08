#pragma once
#include "brand_marks.h"

// Match the Windows GDI host's Segoe UI family and font weights.  Text is
// rasterized at 48 px, then drawn at the monitor-dependent display size;
// loading only the 16 px regular face was visibly blurry at 1440p.
// No font files are shipped or copied: Windows provides them in Fonts.
static ImFont *g_cpFontRegular = nullptr;
static ImFont *g_cpFontSemibold = nullptr;
static ImFont *g_cpFontBold = nullptr;
static float g_cpTextScale = 1.0f;

static int g_cpMarkRects[CP_MARK_COUNT];

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
    // GDI's negative font height measures the em square; stb measures the full
    // ascent/descent. Match the actual Windows line metrics instead of drawing
    // the same nominal size visibly smaller inside games.
    HDC fontDC=CreateCompatibleDC(NULL);
    HFONT metricFont=CreateFontW(-48,0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,
        DEFAULT_CHARSET,OUT_DEFAULT_PRECIS,CLIP_DEFAULT_PRECIS,DEFAULT_QUALITY,DEFAULT_PITCH,L"Segoe UI");
    if(fontDC && metricFont) {
        HGDIOBJ old=SelectObject(fontDC,metricFont);TEXTMETRICW metrics={};
        if(GetTextMetricsW(fontDC,&metrics) && metrics.tmHeight>=48 && metrics.tmHeight<=80)
            g_cpTextScale=metrics.tmHeight/48.0f;
        SelectObject(fontDC,old);
    }
    if(metricFont)DeleteObject(metricFont);if(fontDC)DeleteDC(fontDC);
    for(int i=0;i<CP_MARK_COUNT;++i)
        g_cpMarkRects[i]=io.Fonts->AddCustomRectRegular(0x110000+i,CP_MARKS[i].width+2,CP_MARKS[i].height+2);
    io.Fonts->Build();
    unsigned char *pixels=nullptr;int width=0,height=0;
    io.Fonts->GetTexDataAsAlpha8(&pixels,&width,&height);
    for(int i=0;i<CP_MARK_COUNT && pixels;++i) {
        const ImFontAtlasCustomRect *r=io.Fonts->GetCustomRectByIndex(g_cpMarkRects[i]);
        const CorePulseBrandMask &mark=CP_MARKS[i];
        if(!r || !r->IsPacked())continue;
        for(int y=0;y<r->Height;++y)memset(pixels+(r->Y+y)*width+r->X,0,r->Width);
        for(int j=0;j<mark.count;++j) {
            const CorePulseBrandRun &run=mark.runs[j];
            memset(pixels+(r->Y+1+run.y)*width+r->X+1+run.x,run.alpha,run.width);
        }
    }
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
    size *= g_cpTextScale;
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
    const float width = panel_font(weight)->CalcTextSizeA(size*scale*g_cpTextScale, FLT_MAX, 0.0f, value).x;
    panel_text(draw, origin, right-width/scale, y, scale, size, color, value,
               -1.0f, -1.0f, weight);
}

// Logos share the same antialiased mask as GDI, uploaded once with the font atlas.
static void panel_mark(ImDrawList *draw,ImVec2 at,float scale,int index) {
    ImFontAtlas *atlas=ImGui::GetIO().Fonts;
    const ImFontAtlasCustomRect *r=atlas->GetCustomRectByIndex(g_cpMarkRects[index]);
    if(!r || !r->IsPacked() || !atlas->TexID)return;
    const CorePulseBrandMask &mark=CP_MARKS[index];
    float width=index<=CP_MARK_INTEL?32:28,height=width*mark.height/mark.width;
    ImVec2 a(at.x-width*scale/2,at.y-height*scale/2),b(a.x+width*scale,a.y+height*scale);
    ImVec2 uv0((r->X+1.0f)/atlas->TexWidth,(r->Y+1.0f)/atlas->TexHeight);
    ImVec2 uv1((r->X+1.0f+mark.width)/atlas->TexWidth,(r->Y+1.0f+mark.height)/atlas->TexHeight);
    draw->AddImage(atlas->TexID,a,b,uv0,uv1,IM_COL32_WHITE);
}

static void panel_elided(ImDrawList *draw,ImVec2 origin,float scale,float x,float y,float width,const char *text) {
    char value[256];snprintf(value,sizeof(value),"%s",text?text:"N/A");
    const float size=12*scale*g_cpTextScale;
    if(panel_font()->CalcTextSizeA(size,FLT_MAX,0,value).x>width*scale) {
        size_t count=strlen(value);
        while(count && panel_font()->CalcTextSizeA(size,FLT_MAX,0,value).x+panel_font()->CalcTextSizeA(size,FLT_MAX,0,"...").x>width*scale) {
            --count;while(count && (value[count]&0xC0)==0x80)--count;value[count]=0;
        }
        if(count+3<sizeof(value))strcat(value,"...");
    }
    panel_text(draw,origin,x,y,scale,12,IM_COL32(236,244,252,255),value,x,x+width);
}

static void panel_card(ImDrawList *draw,ImVec2 origin,float scale,CorePulsePanelRect r,
                       const char *label,const char *value,const char *name,const char *detail,
                       const char *brand,unsigned int accent,unsigned int base) {
    auto at=[origin,scale](float x,float y){return ImVec2(origin.x+x*scale,origin.y+y*scale);};
    draw->AddRectFilled(at(r.x,r.y),at(r.x+r.w,r.y+r.h),panel_color(panel_mix(base,accent,7),250),8*scale);
    draw->AddRect(at(r.x,r.y),at(r.x+r.w,r.y+r.h),panel_color(panel_mix(base,0xC8DAEE,16),245),8*scale);
    draw->AddRectFilled(at(r.x+12,r.y+19),at(r.x+48,r.y+55),panel_color(panel_mix(base,accent,24)),5*scale);
    panel_mark(draw,at(r.x+30,r.y+37),scale,cp_mark_index(brand,label));
    panel_text(draw,origin,r.x+60,r.y+13,scale,12,panel_color(accent),label,-1,-1,CP_FONT_SEMIBOLD);
    panel_text_right(draw,origin,r.x+r.w-13,r.y+4,scale,22,panel_color(accent),value,CP_FONT_BOLD);
    panel_elided(draw,origin,scale,r.x+60,r.y+38,r.w-73,name);
    panel_text(draw,origin,r.x+14,r.y+71,scale,12,IM_COL32(170,188,207,255),detail,r.x+14,r.x+r.w-14);
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
    float panelScale = io.DisplaySize.x * 0.82f / (float)CP_PANEL_WIDTH;
    if (panelScale < 0.8f) panelScale = 0.8f;
    if (panelScale > 2.2f) panelScale = 2.2f;
    if ((io.DisplaySize.x-24.0f)/(float)CP_PANEL_WIDTH < panelScale)
        panelScale = (io.DisplaySize.x-24.0f)/(float)CP_PANEL_WIDTH;
    const float safePanelWidth = (float)CP_PANEL_WIDTH * panelScale;
    const float panelHeight = CP_PANEL_HEIGHT * panelScale;

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
        panel_card(draw,panelOrigin,panelScale,cp_panel_card(0),"CPU",st.cpu,st.cpuName,st.cpuTemp,st.cpuBrand,st.cpuRgb,base);
        panel_card(draw,panelOrigin,panelScale,cp_panel_card(1),"GPU",st.gpu,st.gpuName,st.gpuTemp,st.gpuBrand,st.gpuRgb,base);
        panel_card(draw,panelOrigin,panelScale,cp_panel_card(2),"RAM",st.ram,st.ramInfo,"","",0x37CBB8,base);
        panel_card(draw,panelOrigin,panelScale,cp_panel_card(3),"DISCO",st.diskPercent,st.diskName,st.diskInfo,"",0xA66BD6,base);
        panel_text(draw,panelOrigin,1056,7,panelScale,11,panel_color(muted),st.captureStatus[0]?st.captureStatus:"Perfiles de energía",1056,1394);
        for(int i=0;i<count;++i) {
            CorePulsePanelRect r=cp_panel_plan(i);
            ImVec2 a(panelOrigin.x+r.x*panelScale,panelOrigin.y+r.y*panelScale),b(a.x+r.w*panelScale,a.y+r.h*panelScale);
            draw->AddRectFilled(a,b,panel_color(panel_mix(base,st.plans[i].active?accent:muted,st.plans[i].active?27:10)),4.5f*panelScale);
            if(st.plans[i].active)draw->AddCircleFilled(ImVec2(a.x+10*panelScale,a.y+11*panelScale),2*panelScale,panel_color(accent));
            panel_text(draw,panelOrigin,r.x+(st.plans[i].active?18:10),r.y+5,panelScale,11,st.plans[i].active?white:panel_color(muted),st.plans[i].name,r.x+9,r.x+r.w-9);
            char id[32];snprintf(id,sizeof(id),"plan%d##quick",i);
            ImGui::SetCursorPos(ImVec2(r.x*panelScale,r.y*panelScale));
            if(ImGui::InvisibleButton(id,ImVec2(r.w*panelScale,r.h*panelScale)))send_action(100+i);
            if(ImGui::IsItemHovered())draw->AddRect(a,b,panel_color(accent),4.5f*panelScale);
        }
        if(!count)panel_text(draw,panelOrigin,1066,35,panelScale,11,panel_color(muted),"Cargando perfiles...");
        const unsigned int colors[CP_PANEL_ACTION_COUNT]={teal,cyan};
        const char *labels[CP_PANEL_ACTION_COUNT]={"RAM A FONDO","COREPULSE"};
        const char *ids[CP_PANEL_ACTION_COUNT]={"RAM##quick","OPEN##quick"};const int codes[CP_PANEL_ACTION_COUNT]={2,3};
        for(int i=0;i<CP_PANEL_ACTION_COUNT;++i) {
            CorePulsePanelRect r=cp_panel_action(i);
            ImVec2 a(panelOrigin.x+r.x*panelScale,panelOrigin.y+r.y*panelScale),b(a.x+r.w*panelScale,a.y+r.h*panelScale);
            draw->AddRectFilled(a,b,panel_color(panel_mix(base,colors[i],18)),4.5f*panelScale);
            panel_text(draw,panelOrigin,r.x+9,r.y+6,panelScale,11,panel_color(panel_mix(0xFFFFFF,colors[i],20)),labels[i],-1,-1,CP_FONT_SEMIBOLD);
            ImGui::SetCursorPos(ImVec2(r.x*panelScale,r.y*panelScale));
            if(ImGui::InvisibleButton(ids[i],ImVec2(r.w*panelScale,r.h*panelScale)))send_action(codes[i]);
            if(ImGui::IsItemHovered())draw->AddRect(a,b,panel_color(colors[i]),4.5f*panelScale);
        }
        CorePulsePanelRect close=cp_panel_close();
        panel_text(draw,panelOrigin,close.x+9,close.y+4,panelScale,14,panel_color(muted),"×");
        ImGui::SetCursorPos(ImVec2(close.x*panelScale,close.y*panelScale));
        if(ImGui::InvisibleButton("CLOSE##quick",ImVec2(close.w*panelScale,close.h*panelScale)))send_action(1);
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
