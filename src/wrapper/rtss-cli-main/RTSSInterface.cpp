// RTSSProfileInterface.cpp : implementation file
//
// created by Unwinder
/////////////////////////////////////////////////////////////////////////////
//#include "stdafx.h"
#include "RTSSInterface.h"
#include "WinUser.h"

#include <shlwapi.h>
/////////////////////////////////////////////////////////////////////////////
CRTSSInterface::CRTSSInterface()
{
	m_hRTSSHooksDLL				= NULL;

	m_pFnEnumProfiles			= NULL;				
	m_pFnLoadProfile			= NULL;
	m_pFnSaveProfile			= NULL;
	m_pFnGetProfileProperty		= NULL;
	m_pFnSetProfileProperty		= NULL;
	m_pFnDeleteProfile			= NULL;
	m_pFnResetProfile			= NULL;
	m_pFnUpdateProfiles			= NULL;
}
/////////////////////////////////////////////////////////////////////////////
CRTSSInterface::~CRTSSInterface()
{
	Uninit();
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::Uninit()
{
	if (m_hRTSSHooksDLL)
		FreeLibrary(m_hRTSSHooksDLL);
	m_hRTSSHooksDLL				= NULL;

	m_pFnEnumProfiles			= NULL;				
	m_pFnLoadProfile			= NULL;
	m_pFnSaveProfile			= NULL;
	m_pFnGetProfileProperty		= NULL;
	m_pFnSetProfileProperty		= NULL;
	m_pFnDeleteProfile			= NULL;
	m_pFnResetProfile			= NULL;
	m_pFnUpdateProfiles			= NULL;
}
/////////////////////////////////////////////////////////////////////////////
BOOL CRTSSInterface::Init(LPCSTR lpInstallPath)
{
	Uninit();

	char szLibraryPath[MAX_PATH];
	strcpy_s(szLibraryPath, sizeof(szLibraryPath), lpInstallPath);
	//PathRemoveFileSpec(szLibraryPath);
	strcat_s(szLibraryPath, sizeof(szLibraryPath), "\\RTSSHooks64.dll");

	m_hRTSSHooksDLL				= LoadLibrary(szLibraryPath);

	if (m_hRTSSHooksDLL)
	{
		m_pFnEnumProfiles		= (PFNENUMPROFILES		)GetProcAddress(m_hRTSSHooksDLL, "EnumProfiles"			);				
		m_pFnLoadProfile		= (PFNLOADPROFILE		)GetProcAddress(m_hRTSSHooksDLL, "LoadProfile"			);
		m_pFnSaveProfile		= (PFNSAVEPROFILE		)GetProcAddress(m_hRTSSHooksDLL, "SaveProfile"			);
		m_pFnGetProfileProperty	= (PFNGETPROFILEPROPERTY)GetProcAddress(m_hRTSSHooksDLL, "GetProfileProperty"	);
		m_pFnSetProfileProperty	= (PFNSETPROFILEPROPERTY)GetProcAddress(m_hRTSSHooksDLL, "SetProfileProperty"	);
		m_pFnDeleteProfile		= (PFNDELETEPROFILE		)GetProcAddress(m_hRTSSHooksDLL, "DeleteProfile"		);
		m_pFnResetProfile		= (PFNRESETPROFILE		)GetProcAddress(m_hRTSSHooksDLL, "ResetProfile"			);
		m_pFnUpdateProfiles		= (PFNUPDATEPROFILES	)GetProcAddress(m_hRTSSHooksDLL, "UpdateProfiles"		);
		m_pFnSetFlags 			= (SETFLAGS				)GetProcAddress(m_hRTSSHooksDLL, "SetFlags"				);
		m_pFnGetFlags 			= (GETFLAGS				)GetProcAddress(m_hRTSSHooksDLL, "GetFlags"				);

		if (m_pFnEnumProfiles		&&
			m_pFnLoadProfile		&&
			m_pFnSaveProfile		&&
			m_pFnGetProfileProperty	&&
			m_pFnSetProfileProperty	&&
			m_pFnDeleteProfile		&&
			m_pFnResetProfile		&&
			m_pFnUpdateProfiles)
			return TRUE;

		Uninit();
	}

	return FALSE;
}
/////////////////////////////////////////////////////////////////////////////
BOOL CRTSSInterface::IsInitialized()
{
	return (m_hRTSSHooksDLL != NULL);
}
/////////////////////////////////////////////////////////////////////////////
DWORD CRTSSInterface::EnumProfiles(LPSTR lpProfilesList, DWORD dwProfilesListSize)
{
	if (m_pFnEnumProfiles)
		return m_pFnEnumProfiles(lpProfilesList, dwProfilesListSize);

	return 0;
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::LoadProfile(LPCSTR lpProfile)
{
	if (m_pFnLoadProfile)
		m_pFnLoadProfile(lpProfile);
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::SaveProfile(LPCSTR lpProfile)
{
	if (m_pFnSaveProfile)
		m_pFnSaveProfile(lpProfile);
}
/////////////////////////////////////////////////////////////////////////////
BOOL CRTSSInterface::GetProfileProperty(LPCSTR lpPropertyName, LPBYTE lpPropertyData, DWORD dwPropertySize)
{
	if (m_pFnGetProfileProperty)
		return m_pFnGetProfileProperty(lpPropertyName, lpPropertyData, dwPropertySize);

	return FALSE;
}
/////////////////////////////////////////////////////////////////////////////
BOOL CRTSSInterface::SetProfileProperty(LPCSTR lpPropertyName, LPBYTE lpPropertyData, DWORD dwPropertySize)
{
	if (m_pFnSetProfileProperty)
		return m_pFnSetProfileProperty(lpPropertyName, lpPropertyData, dwPropertySize);

	return FALSE;
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::DeleteProfile(LPCSTR lpProfile)
{
	if (m_pFnDeleteProfile)
		m_pFnDeleteProfile(lpProfile);
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::ResetProfile(LPCSTR lpProfile)
{
	if (m_pFnResetProfile)
		m_pFnResetProfile(lpProfile);
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::UpdateProfiles()
{
	if (m_pFnUpdateProfiles)
		m_pFnUpdateProfiles();
}
/////////////////////////////////////////////////////////////////////////////
DWORD CRTSSInterface::SetFlags(DWORD dwAND, DWORD dwXOR)
{
	if(m_pFnSetFlags)
		return m_pFnSetFlags(dwAND, dwXOR);

	return FALSE;
}
/////////////////////////////////////////////////////////////////////////////
DWORD CRTSSInterface::GetFlags()
{
	if(m_pFnGetFlags)
		return m_pFnGetFlags();

	return FALSE;
}
/////////////////////////////////////////////////////////////////////////////
void CRTSSInterface::PostMessage(UINT Msg, WPARAM wParam, LPARAM lParam)
{
	HWND hWnd = hWnd = ::FindWindow(NULL, "RTSS");
	if (!hWnd)
		hWnd = ::FindWindow(NULL, "RivaTuner Statistics Server");

	if (hWnd)
		::PostMessage(hWnd, Msg, wParam, lParam);
}