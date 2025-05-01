#define WIN32_LEAN_AND_MEAN 1
#include <iostream>
#include <vector>
#include <string>
#include <windows.h>
#include <algorithm>
#include <cctype>
#include "rtss-core.cpp"

using namespace std;

string toLowerCase(string in)
{
    string out = in;
    transform(out.begin(), out.end(), out.begin(),
                   [](unsigned char c)
                   { return tolower(c); });
    return out;
}

string lc(string in)
{
    return toLowerCase(in);
}

void printHelp() {
            cout << endl;
            cout << "   \033[1mCOMMANDS\033[0m" << endl;
            cout << "   property:set            set a profile property" << endl;
            cout << "   property:get            print a profile property" << endl;
            cout << "   overlay:set             set overlay visibility" << endl;
            cout << "   overlay:get             return overlay visibility" << endl;
            cout << "   overlay:toggle          toggle overlay state" << endl;
            cout << "   limiter:set             set if limiter is active" << endl;
            cout << "   limiter:get             print value of limiter status" << endl;
            cout << "   limiter:toggle          toggle limiter status" << endl;
            cout << "   limit:set               set framerate limit for global profile" << endl;
            cout << "   limit:offset            offset framerate limit for global profile" << endl;
            cout << "   limit:get               print framerate limit for global profile" << endl;
            cout << endl;
            cout << endl;
            cout << "   \033[1mUSAGE\033[0m" << endl;
            cout << "   property:set <profile> <property> <value>" << endl << endl;
            cout << "       <profile>           string, such as \"App.exe\" or \"Global\" (without quotes)" << endl;
            cout << "       <property>          string, such as \"FramerateLimit\" or \"AppDetectionLevel\" (without quotes)" << endl;
            cout << "       <value>             integer to assign as the new value" << endl;
            cout << endl;
            cout << "   property:get <profile> <property>" << endl << endl;
            cout << "       <profile>           string, such as \"App.exe\" or \"Global\" (without quotes)" << endl;
            cout << "       <property>          string, such as \"FramerateLimit\" or \"AppDetectionLevel\" (without quotes)" << endl;
            cout << endl;
            cout << "   overlay:set <value>     0 or 1" << endl;
            cout << "   limiter:set <value>     0 or 1" << endl;
            cout << "   limit:set <value>       integer to set the framerate limit to" << endl;
            cout << "   limit:offset <value>    integer to offset the framerate limit with" << endl;
            cout << endl;
}

int insufficient()
{
    cout << "Insufficient arguments" << endl;
    printHelp();
    return 0;
}

int main(int argc, char **argv)
{
    const vector<string> args(argv, argv + argc);

    if (args.size() < 2) {
        printHelp();
        return 0;
    }

    string action = lc(args[1]);
    if (lc("property:set") == action)
    {
        if (args.size() < 5)
            return insufficient();

        string profile = args[2];
        string property = args[3];
        string value = args[4];

        if (toLowerCase(profile) == "global")
            profile = "";

        SetProperty(profile, property, stoi(value));
        cout << "OK" << endl;
    }
    else if (lc("property:get") == action)
    {
        if (args.size() < 4)
            return insufficient();
        string profile = args[2];
        string property = args[3];

        if (toLowerCase(profile) == "global")
            profile = "";

        DWORD value = GetProperty(profile.c_str(), property.c_str());
        cout << value << endl;
    }
    else if (lc("overlay:set") == action)
    {
        if (args.size() < 3)
            return insufficient();
        string value = args[2];
        SetFlags(~RTSSHOOKSFLAG_OSD_VISIBLE, stoi(value));
        cout << "OK" << endl;
    }
    else if (lc("overlay:get") == action)
    {
        DWORD flags = GetFlags();
        cout << to_string(flags & RTSSHOOKSFLAG_OSD_VISIBLE ? 1 : 0) << endl;
    }
    else if (lc("overlay:toggle") == action)
    {
        SetFlags(0xFFFFFFFF, RTSSHOOKSFLAG_OSD_VISIBLE);
        DWORD flags = GetFlags();
        cout << to_string(flags & RTSSHOOKSFLAG_OSD_VISIBLE ? 1 : 0) << endl;
    }
    else if (lc("limiter:set") == action)
    {
        if (args.size() < 3)
            return insufficient();

        int value = stoi(args[2]);
        if (value == 0)
        {
            SetFlags(~RTSSHOOKSFLAG_LIMITER_DISABLED, RTSSHOOKSFLAG_LIMITER_DISABLED);
        }
        else
        {
            SetFlags(~RTSSHOOKSFLAG_LIMITER_DISABLED, 0);
        }
        cout << "OK" << endl;
    }
    else if (lc("limiter:get") == action)
    {
        DWORD flags = GetFlags();
        cout << to_string(flags & RTSSHOOKSFLAG_LIMITER_DISABLED ? 0 : 1) << endl;
    }
    else if (lc("limiter:toggle") == action)
    {
        SetFlags(0xFFFFFFFF, RTSSHOOKSFLAG_LIMITER_DISABLED);
        DWORD flags = GetFlags();
        cout << to_string(flags & RTSSHOOKSFLAG_LIMITER_DISABLED ? 0 : 1) << endl;
    }
    else if (lc("limit:set") == action)
    {
        if (args.size() < 3)
            return insufficient();

        int value = stoi(args[2]);
        SetProperty("", "FramerateLimit", value);
        cout << "OK" << endl;
    }
    else if (lc("limit:offset") == action)
    {
        if (args.size() < 3)
            return insufficient();

        int offset = stoi(args[2]);
        int value = GetProperty("", "FramerateLimit");
        SetProperty("", "FramerateLimit", value + offset);
        cout << "OK" << endl;
    }
    else if (lc("limit:get") == action)
    {
        DWORD value = GetProperty("", "FramerateLimit");
        cout << value << endl;
    }
    else if (lc("flags:get") == action)
    {
        DWORD flags = GetFlags();
        cout << flags << endl;
    } else {
        printHelp();
    }
    return 0;
}