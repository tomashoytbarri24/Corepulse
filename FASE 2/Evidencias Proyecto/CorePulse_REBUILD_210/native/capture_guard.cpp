// CorePulse ETW session lifecycle. Only our exact session names are managed.
#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <evntrace.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <vector>
#include <string>

struct Properties { EVENT_TRACE_PROPERTIES p; wchar_t name[1024]; };
static Properties properties() {
    Properties p = {}; p.p.Wnode.BufferSize = sizeof(p);
    p.p.LoggerNameOffset = offsetof(Properties,name); return p;
}

static DWORD parent_pid() {
    DWORD result = 0;
    HANDLE list = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
    if (list==INVALID_HANDLE_VALUE) return 0;
    PROCESSENTRY32W item = {}; item.dwSize = sizeof(item);
    if (Process32FirstW(list,&item)) do {
        if (item.th32ProcessID==GetCurrentProcessId()) { result=item.th32ParentProcessID; break; }
    } while (Process32NextW(list,&item));
    CloseHandle(list); return result;
}

static bool owner_dead(DWORD pid) {
    HANDLE process = OpenProcess(SYNCHRONIZE|PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
    if (!process) return GetLastError()==ERROR_INVALID_PARAMETER;
    bool dead = WaitForSingleObject(process,0)==WAIT_OBJECT_0;
    CloseHandle(process); return dead;
}

static DWORD session_owner(const wchar_t *name) {
    const wchar_t *prefix = L"CorePulseOverlay_";
    size_t length = wcslen(prefix);
    if (wcsncmp(name,prefix,length)!=0) return 0;
    wchar_t *end = nullptr;
    unsigned long value = wcstoul(name+length,&end,10);
    // REBUILD 199: «CorePulseOverlay_<pid>» o «CorePulseOverlay_<pid>_<n>».
    if (!value || !end) return 0;
    if (*end==L'_') {
        wchar_t *tail = nullptr;
        wcstoul(end+1,&tail,10);
        if (tail==end+1 || !tail || *tail) return 0;
    } else if (*end) return 0;
    return value;
}

static ULONG stop_owned_by(DWORD owner, bool onlyDead, unsigned *stopped) {
    std::vector<Properties> storage(256);
    std::vector<EVENT_TRACE_PROPERTIES*> pointers;
    for (auto &p:storage) { p=properties(); pointers.push_back(&p.p); }
    ULONG count = 0;
    ULONG result = QueryAllTracesW(pointers.data(),(ULONG)pointers.size(),&count);
    if (result!=ERROR_SUCCESS) return result;
    for (ULONG i=0; i<count && i<storage.size(); ++i) {
        auto &p = storage[i];
        if (p.p.LoggerNameOffset>=sizeof(p)) continue;
        const wchar_t *name = (const wchar_t*)((const BYTE*)&p+p.p.LoggerNameOffset);
        DWORD sessionOwner = session_owner(name);
        if (!sessionOwner) continue;
        if (onlyDead ? !owner_dead(sessionOwner) : sessionOwner!=owner) continue;
        Properties stopProperties = properties();
        if (ControlTraceW(0,name,&stopProperties.p,EVENT_TRACE_CONTROL_STOP)==ERROR_SUCCESS && stopped) ++*stopped;
    }
    return ERROR_SUCCESS;
}

int wmain(int argc,wchar_t **argv) {
    if (argc==3 && wcscmp(argv[1],L"--stop-owner")==0) {
        wchar_t *end = nullptr; DWORD pid = wcstoul(argv[2],&end,10);
        // A caller can stop only the session belonging to its own parent PID.
        if (!pid || !end || *end || pid!=parent_pid()) return 2;
        // Todas las sesiones de este CorePulse, con o sin sufijo de arranque.
        ULONG result = stop_owned_by(pid,false,nullptr);
        if (result!=ERROR_SUCCESS) {
            fprintf(stderr,"CorePulse capture stop WINERR=%lu\n",result); return 3;
        }
        return 0;
    }
    if (argc!=2 || wcscmp(argv[1],L"--cleanup-stale")) return 2;
    unsigned stopped = 0;
    ULONG result = stop_owned_by(0,true,&stopped);
    if (result!=ERROR_SUCCESS) {
        fprintf(stderr,"CorePulse capture query WINERR=%lu\n",result); return 4;
    }
    printf("CorePulse stale sessions stopped=%u\n",stopped);
    return 0;
}
