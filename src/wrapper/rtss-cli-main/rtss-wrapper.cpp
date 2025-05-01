// rtss-wrapper.cpp
#include "rtss-core.cpp"

extern "C" {

__declspec(dllexport) void set_property(const char* profile, const char* property, int value) {
    SetProperty(profile, property, value);
}

__declspec(dllexport) int get_property(const char* profile, const char* property) {
    return GetProperty(profile, property);
}

__declspec(dllexport) void set_flags(unsigned int andMask, unsigned int orMask) {
    SetFlags(andMask, orMask);
}

__declspec(dllexport) unsigned int get_flags() {
    return GetFlags();
}
}

// cl /LD rtss-wrapper.cpp /Fe:rtss.dll User32.lib Advapi32.lib