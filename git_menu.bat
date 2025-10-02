@echo off
:: אם הופעל מחלון שנפתח ע"י Explorer (double-click) בדרך כלל התהליך הוא cmd /c
:: נזהה זאת ע"י חיפוש '/c' ב-%CMDCMDLINE% ונפתח מחדש עם /k כדי שהחלון לא ייסגר מיד.
if /i not "%~1"=="internal" (
  echo %CMDCMDLINE% | find /i "/c" >nul 2>nul && (
    start "GitMenu" cmd /k call "%~f0" internal %*
    goto :eof
  )
)
@echo off
:: ==================================================
:: תפריט ניהול ריפו Git בעברית (עם שיפורי יציבות)
:: * מונע סגירה מידית (בודק ריפו / מציג שגיאות)
:: * debug: הפעלה עם פרמטר debug -> יוצר git_menu_debug.log
:: * קוד עמוד UTF-8 ואם נכשל מנסה 862 (עברית OEM)
:: ==================================================

setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0" 2>nul

:: --- קוד עמוד ---
chcp 65001 >nul 2>nul || chcp 862 >nul 2>nul

:: --- מצב דיבאג ---
set DEBUG_MODE=0
if /i "%~1"=="debug" set DEBUG_MODE=1
if %DEBUG_MODE%==1 (echo [DEBUG] מצב דיבאג פעיל > git_menu_debug.log)

call :dbg "התחלה"

:: --- בדיקת האם בתוך ריפו ---
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo לא זוהה ריפו Git בתיקייה הזו.
  echo ודא שאתה בתוך התיקייה של הפרויקט (יש .git).
  echo.
  pause
  goto graceful_exit
)

:: --- בדיקת קיום Git ---
git --version >nul 2>nul || (
  echo --------------------------------------------------
  echo   Git לא זמין (PATH חסר). התקן Git או פתח Git Bash
  echo   יציאה...
  echo --------------------------------------------------
  pause
  goto graceful_exit
)

:: --- פונקציית לוג לדיבאג ---
:dbg
if %DEBUG_MODE%==1 echo [%DATE% %TIME%] %~1>>git_menu_debug.log
goto :eof

set MENU_WIDTH=78

:: פונקציה להדפסת קו
:line
for /l %%# in (1,1,%MENU_WIDTH%) do <nul set /p =-
echo.
goto :eof

:: פונקציה הדפסה מיושרת פחות או יותר לימין (חישוב אורך בסיסי)
:rprint
set "_t=%~1"
set "_len=0"
for /l %%A in (0,1,512) do (
  if not "!_t:~%%A,1!"=="" (set /a _len+=1) else goto _after_len
)
:_after_len
set /a _spaces=%MENU_WIDTH% - _len - 2
set "_pad="
for /l %%S in (1,1,!_spaces!) do set "_pad=!_pad! "
echo !_pad!!_t!
goto :eof

:: הצגת שם ברנץ נוכחי
for /f "tokens=*" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set CURRENT_BRANCH=%%B

:menu
cls
call :dbg "מציג תפריט"
for /f "tokens=*" %%B in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set CURRENT_BRANCH=%%B
if not defined CURRENT_BRANCH set CURRENT_BRANCH=?
call :line
call :rprint "תפריט ניהול ריפו (Git) — ענף: %CURRENT_BRANCH%"
call :line
call :rprint "1. סטטוס (git status -s)"
call :rprint "2. משיכת שינויים (git pull --ff-only)"
call :rprint "3. העלאת שינויים (Add + Commit + Push)"
call :rprint "4. הצגת לוג אחרון (15)"
call :rprint "5. יצירת ענף חדש"
call :rprint "6. מעבר לענף קיים"
call :rprint "7. Stash שמירת שינויים"
call :rprint "8. Stash החלת אחרון"
call :rprint "9. Diff סטטיסטי (git diff --stat)"
call :rprint "10. סנכרון מלא (Pull ואז Push)"
call :rprint "11. ניקוי קבצים לא במעקב (Clean)"
call :rprint "12. הצגת קבצים שהשתנו (Name-Status)"
call :rprint "13. עדכון שם משתמש/אימייל ל-Commit"
call :rprint "0. יציאה"
call :line
set "CH="
set /p CH="בחר מספר ולחץ Enter: "
if not defined CH goto menu
call :dbg "בחירה=%CH%"
if "%CH%"=="1" goto do_status
if "%CH%"=="2" goto do_pull
if "%CH%"=="3" goto do_push
if "%CH%"=="4" goto do_log
if "%CH%"=="5" goto do_new_branch
if "%CH%"=="6" goto do_switch
if "%CH%"=="7" goto do_stash
if "%CH%"=="8" goto do_stash_apply
if "%CH%"=="9" goto do_diff
if "%CH%"=="10" goto do_sync
if "%CH%"=="11" goto do_clean
if "%CH%"=="12" goto do_changed
if "%CH%"=="13" goto do_usercfg
if "%CH%"=="0" goto end
echo בחירה לא תקינה. נסה שוב.
timeout /t 1 >nul
goto menu

:do_status
echo.
echo === STATUS ===
git status -s
echo.
pause
goto menu

:do_pull
echo.
echo === PULL ===
git pull --ff-only
echo.
pause
goto menu

:do_push
echo.
echo === ADD + COMMIT + PUSH ===
git status -s
echo.
set /p CMSG="הכנס הודעת קומיט (או השאר ריק לביטול): "
if "%CMSG%"=="" (echo בוטל. & pause & goto menu)
git add -A
git commit -m "%CMSG%"
if errorlevel 1 (echo שגיאה בקומיט או אין מה לקומט.& pause & goto menu)
git push
echo.
pause
goto menu

:do_log
echo.
echo === LOG (15 אחרונים) ===
git log --oneline -n 15
echo.
pause
goto menu

:do_new_branch
set /p NB="שם ענף חדש: "
if "%NB%"=="" (echo בוטל.& pause & goto menu)
git checkout -b "%NB%"
set CURRENT_BRANCH=%NB%
echo נוצר ועבר לענף %NB%
pause
goto menu

:do_switch
set /p SB="שם ענף לעבור אליו: "
if "%SB%"=="" (echo בוטל.& pause & goto menu)
git checkout "%SB%"
if errorlevel 1 (echo כישלון מעבר ענף.& pause & goto menu)
set CURRENT_BRANCH=%SB%
echo עבר לענף %SB%
pause
goto menu

:do_stash
echo מבצע Stash לשינויים...
git stash push -u -m "menu-auto"
pause
goto menu

:do_stash_apply
echo החלת אחרון Stash...
git stash apply
pause
goto menu

:do_diff
echo.
echo === DIFF (STAT) ===
git diff --stat
echo.
pause
goto menu

:do_sync
echo === FULL SYNC (Pull ואז Push) ===
git pull --ff-only
git push
pause
goto menu

:do_clean
echo.
echo אזהרה: פעולה זו תנקה קבצים לא במעקב.
echo שלב א (תצוגת מה יימחק):
git clean -fd -n
set /p OK="להמשיך למחיקה בפועל? (y/N): "
if /i not "%OK%"=="y" (echo בוטל.& pause & goto menu)
git clean -fd
echo בוצע.
pause
goto menu

:do_changed
echo.
echo === קבצים שהשתנו (Name-Status) ===
git diff --name-status
echo.
pause
goto menu

:do_usercfg
echo.
set /p GNAME="שם משתמש (Git user.name, ריק לדילוג): "
if not "%GNAME%"=="" git config user.name "%GNAME%"
set /p GMAIL="אימייל (Git user.email, ריק לדילוג): "
if not "%GMAIL%"=="" git config user.email "%GMAIL%"
echo הגדרות נוכחיות:
git config user.name
git config user.email
pause
goto menu

:end
echo יציאה...
timeout /t 1 >nul
goto graceful_exit

:graceful_exit
call :dbg "סיום"
endlocal
exit /b 0
