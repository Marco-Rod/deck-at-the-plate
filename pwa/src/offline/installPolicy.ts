export interface NavigatorWithStandalone extends Navigator {
  standalone?: boolean
}

export function isIosDevice(navigatorValue: Navigator): boolean {
  return (
    /iPad|iPhone|iPod/.test(navigatorValue.userAgent) ||
    (/Macintosh/.test(navigatorValue.userAgent) && navigatorValue.maxTouchPoints > 1)
  )
}

export function isIosSafari(navigatorValue: Navigator): boolean {
  return (
    isIosDevice(navigatorValue) &&
    /Safari/.test(navigatorValue.userAgent) &&
    !/CriOS|FxiOS|EdgiOS|OPiOS/.test(navigatorValue.userAgent)
  )
}

export function isStandaloneDisplay(
  navigatorValue: NavigatorWithStandalone,
  matchesStandalone: boolean,
): boolean {
  return matchesStandalone || navigatorValue.standalone === true
}

const SAFE_INSTALL_PATHS = new Set(['/auth', '/lobby', '/team', '/showcase'])

export function canSuggestInstall(pathname: string, activeGame: boolean): boolean {
  return !activeGame && SAFE_INSTALL_PATHS.has(pathname)
}
