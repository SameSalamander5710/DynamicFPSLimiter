#define WIN32_LEAN_AND_MEAN 1
#include <iostream>
#include <vector>
#include <string>
#include <windows.h>

using namespace std;

#include "RTSSInterface.cpp"

CRTSSInterface rtss;

void Init()
{
    if (!rtss.IsInitialized())
    {
        HKEY hKey;
        if (ERROR_SUCCESS == RegOpenKey(HKEY_LOCAL_MACHINE, "Software\\WOW6432Node\\Unwinder\\RTSS", &hKey))
        {
            char buf[MAX_PATH];

            DWORD dwSize = MAX_PATH;
            DWORD dwType;

            if (ERROR_SUCCESS == RegQueryValueEx(hKey, "InstallDir", 0, &dwType, (LPBYTE)buf, &dwSize))
            {
                if (dwType == REG_SZ)
                {
                    rtss.Init(buf);
                }
            }

            RegCloseKey(hKey);
        }
    }
}

DWORD GetProfileProperty(LPCSTR lpProfile, LPCSTR lpProfileProperty)
{
    DWORD dwProperty = 0;
    if (rtss.IsInitialized())
    {
        rtss.LoadProfile(lpProfile);
        rtss.GetProfileProperty(lpProfileProperty, (LPBYTE)&dwProperty, sizeof(dwProperty));
    }

    return dwProperty;
}

void SetProfileProperty(LPCSTR lpProfile, LPCSTR lpProfileProperty, DWORD dwProperty)
{
    if (rtss.IsInitialized())
    {
        rtss.LoadProfile(lpProfile);
        rtss.SetProfileProperty(lpProfileProperty, (LPBYTE)&dwProperty, sizeof(dwProperty));
        rtss.SaveProfile(lpProfile);
        rtss.UpdateProfiles();
    }
}

void SetProperty(string profileStr, string propertyStr, int propValue)
{
    Init();
    LPCSTR profile = profileStr.c_str();
    LPCSTR property = propertyStr.c_str();
    DWORD value = (DWORD)propValue;
    SetProfileProperty(profile, property, value);
}

int GetProperty(string profileStr, string propertyStr)
{
    Init();
    LPCSTR profile = profileStr.c_str();
    LPCSTR property = propertyStr.c_str();
    DWORD value = 0;
    value = GetProfileProperty(profile, property);
    return (int)value;
}

DWORD SetFlags(DWORD dwAND, DWORD dwXOR)
{
    Init();
    DWORD dwResult = 0;
    dwResult = rtss.SetFlags(dwAND, dwXOR);
    rtss.PostMessage(WM_RTSS_UPDATESETTINGS, 0, 0);
    return dwResult;
}

DWORD GetFlags()
{
    Init();
    DWORD dwResult = 0;
    dwResult = rtss.GetFlags();
    return dwResult;
}