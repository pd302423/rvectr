param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CaptureArguments)
$ErrorActionPreference = 'Stop'
$distribution = if ($env:RVECTR_WSL_DISTRO) { $env:RVECTR_WSL_DISTRO } else { 'Ubuntu' }
$linuxHome = (& wsl.exe -d $distribution -- printenv HOME).Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxHome.StartsWith('/')) { throw 'Cannot resolve the WSL home directory' }
$argumentList = @('-d',$distribution,'--cd',"$linuxHome/projects/rvectr",'--',"$linuxHome/.local/bin/uv",'run','--frozen','--extra','cuda','--extra','pose','rvectr')
& wsl.exe @argumentList @CaptureArguments
exit $LASTEXITCODE
