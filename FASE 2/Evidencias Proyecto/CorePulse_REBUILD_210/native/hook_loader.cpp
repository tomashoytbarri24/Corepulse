#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

static LPTHREAD_START_ROUTINE remote_load_library(DWORD pid) {
    HMODULE kernel = GetModuleHandleW(L"kernel32.dll");
    FARPROC localFunction = kernel ? GetProcAddress(kernel, "LoadLibraryW") : nullptr;
    if (!localFunction) return nullptr;
    HMODULE localOwner = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                            (LPCWSTR)localFunction, &localOwner)) return nullptr;
    wchar_t ownerPath[MAX_PATH] = {};
    if (!GetModuleFileNameW(localOwner, ownerPath, MAX_PATH)) return nullptr;
    const wchar_t *ownerName = wcsrchr(ownerPath, L'\\');
    ownerName = ownerName ? ownerName + 1 : ownerPath;
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) return nullptr;
    MODULEENTRY32W entry = {};
    entry.dwSize = sizeof(entry);
    LPTHREAD_START_ROUTINE remoteFunction = nullptr;
    if (Module32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szModule, ownerName) == 0) {
                uintptr_t offset = (uintptr_t)localFunction - (uintptr_t)localOwner;
                remoteFunction = (LPTHREAD_START_ROUTINE)((uintptr_t)entry.modBaseAddr + offset);
                break;
            }
        } while (Module32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return remoteFunction;
}

static bool remote_module_loaded(DWORD pid, const wchar_t *path) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (snapshot == INVALID_HANDLE_VALUE) return false;
    MODULEENTRY32W entry = {};
    entry.dwSize = sizeof(entry);
    bool loaded = false;
    if (Module32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szExePath, path) == 0) {
                loaded = true;
                break;
            }
        } while (Module32NextW(snapshot, &entry));
    }
    CloseHandle(snapshot);
    return loaded;
}

// Loads the CorePulse renderer only into the PID explicitly selected by the
// controller. It never scans processes, changes game files, or bypasses protection.
int wmain(int argc, wchar_t **argv) {
    if (argc != 3) return 2;
    wchar_t *end = nullptr;
    unsigned long pid = wcstoul(argv[1], &end, 10);
    if (!pid || !end || *end || pid == GetCurrentProcessId()) return 3;
    DWORD length = GetFullPathNameW(argv[2], 0, nullptr, nullptr);
    if (!length || length > 32767) return 4;
    wchar_t *path = (wchar_t *)calloc(length + 1, sizeof(wchar_t));
    if (!path) return 5;
    if (!GetFullPathNameW(argv[2], length + 1, path, nullptr) ||
        GetFileAttributesW(path) == INVALID_FILE_ATTRIBUTES) {
        free(path); return 6;
    }
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_CREATE_THREAD |
                                 PROCESS_VM_OPERATION | PROCESS_VM_WRITE, FALSE, pid);
    if (!process) {
        fprintf(stderr, "WINERR=%lu\n", GetLastError());
        free(path); return 7;
    }
    BOOL targetWow64 = FALSE, ownWow64 = FALSE;
    IsWow64Process(process, &targetWow64);
    IsWow64Process(GetCurrentProcess(), &ownWow64);
    if (targetWow64 != ownWow64) { CloseHandle(process); free(path); return 8; }
    SIZE_T bytes = (wcslen(path) + 1) * sizeof(wchar_t);
    void *remote = VirtualAllocEx(process, nullptr, bytes, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
    if (!remote) {
        fprintf(stderr, "WINERR=%lu\n", GetLastError());
        CloseHandle(process); free(path); return 9;
    }
    SIZE_T written = 0;
    if (!WriteProcessMemory(process, remote, path, bytes, &written) || written != bytes) {
        fprintf(stderr, "WINERR=%lu\n", GetLastError());
        VirtualFreeEx(process, remote, 0, MEM_RELEASE); CloseHandle(process); free(path); return 10;
    }
    LPTHREAD_START_ROUTINE loadLibrary = remote_load_library(pid);
    if (!loadLibrary) {
        VirtualFreeEx(process, remote, 0, MEM_RELEASE); CloseHandle(process); free(path); return 11;
    }
    HANDLE thread = CreateRemoteThread(process, nullptr, 0,
                                      loadLibrary, remote, 0, nullptr);
    if (!thread) {
        fprintf(stderr, "WINERR=%lu\n", GetLastError());
        VirtualFreeEx(process, remote, 0, MEM_RELEASE); CloseHandle(process); free(path); return 12;
    }
    DWORD wait = WaitForSingleObject(thread, 8000);
    DWORD loaded = 0;
    if (wait == WAIT_OBJECT_0) GetExitCodeThread(thread, &loaded);
    bool found = wait == WAIT_OBJECT_0 && remote_module_loaded(pid, path);
    CloseHandle(thread);
    if (wait == WAIT_OBJECT_0) VirtualFreeEx(process, remote, 0, MEM_RELEASE);
    CloseHandle(process);
    free(path);
    // The thread return value is a 32-bit view of LoadLibraryW's HMODULE on
    // x64, so zero is inconclusive. A nonzero value proves the load succeeded;
    // the module snapshot covers the zero-low-DWORD case.
    return wait != WAIT_OBJECT_0 ? 13 : (found || loaded != 0) ? 0 : 14;
}
