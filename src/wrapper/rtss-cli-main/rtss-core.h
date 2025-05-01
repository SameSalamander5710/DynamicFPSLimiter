
#include <string>
#include <windows.h>

void SetProperty(std::string profileStr, std::string propertyStr, int propValue);
int GetProperty(std::string profileStr, std::string propertyStr);
DWORD SetFlags(DWORD dwAND, DWORD dwXOR);
DWORD GetFlags();