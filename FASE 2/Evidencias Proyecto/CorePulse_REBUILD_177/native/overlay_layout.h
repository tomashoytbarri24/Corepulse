#pragma once
#include <stdint.h>

// Shared logical geometry for desktop GDI and every in-game API.
struct CorePulseDesign {
    int32_t scale, opacity, gap, x, y;
    int32_t metricCount, metricOrder[5], frametime;
};
static CorePulseDesign cp_default_design() {
    CorePulseDesign d = {100,94,8,1000,0,4,{0,1,2,3,4},1}; return d;
}
static int cp_clamp(int value, int low, int high) {
    return value < low ? low : value > high ? high : value;
}
static CorePulseDesign cp_safe_design(CorePulseDesign d) {
    d.scale=cp_clamp(d.scale,60,160); d.opacity=cp_clamp(d.opacity,25,100);
    d.gap=cp_clamp(d.gap,0,24); d.x=cp_clamp(d.x,0,1000); d.y=cp_clamp(d.y,0,1000);
    d.metricCount=cp_clamp(d.metricCount,1,5);
    for(int i=0;i<d.metricCount;++i) d.metricOrder[i]=cp_clamp(d.metricOrder[i],0,4);
    d.frametime=!!d.frametime; return d;
}
static int cp_osd_height(bool compact, bool graph) {
    return 40+(compact?52:70)+12+(graph?76:0);
}
static float cp_osd_scale(float width,float height,CorePulseDesign d,bool compact) {
    float scale=width*.25f/382;
    if(scale<.8f)scale=.8f; if(scale>2.2f)scale=2.2f;
    scale*=d.scale/100.0f;
    const float fitX=(width-24)/382;
    const float fitY=(height-24)/cp_osd_height(compact,d.frametime);
    if(scale>fitX)scale=fitX; if(scale>fitY)scale=fitY;
    return scale>0?scale:.1f;
}
static float cp_osd_position(float available,float size,float scale,int position) {
    float margin=22*scale;
    if(margin>(available-size)/2)margin=(available-size)/2;
    if(margin<0)margin=0;
    return margin+(available-size-2*margin)*cp_clamp(position,0,1000)/1000.0f;
}
