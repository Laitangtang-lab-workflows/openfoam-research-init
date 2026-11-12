# -*- coding: utf-8 -*-
# 副本巡检（通用引擎，openfoam-research-init skill 随身分发）：
#   Win 正本 vs WSL vs 集群 三方代码 hash 对比（正本纪律的审计工具）。
# 用法：pwsh -File replica_audit.ps1 -Config <project.json>
#   项目差异全在 config（json）：layer_root、works_prefix、code_dir、pub_dir、lang、
#   wsl_distro、wsl_find、cluster_ssh、cluster_probe、cluster_find、ignore —— 引擎零机器路径。
# 输出：同名漂移（以 Win 为正）、运行侧独有（= 待回传项）、汇总。
# 退出码：0 = 全部一致；1 = 存在漂移或独有；2 = WSL/集群不可达（只巡了可达侧）。
# 约定：含中文的 .ps1 必须 UTF-8 带 BOM 保存（PowerShell 中文脚本铁律）。

param(
    [Parameter(Mandatory = $true)]
    [string]$Config
)
$ErrorActionPreference = 'Continue'

# ---- 装载 config ----
$cfg = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json   # UTF8 读取自动去 BOM
$cfgDir = Split-Path -Parent (Resolve-Path $Config)
$ROOT = (Join-Path $cfgDir $cfg.layer_root) | Resolve-Path      # 方向层根
$WORKS = if ($cfg.works_prefix) { $cfg.works_prefix } else { '工作' }
$CODE = if ($cfg.code_dir) { $cfg.code_dir } else { '代码' }
$PUBD = if ($cfg.pub_dir) { $cfg.pub_dir } else { '公共库' }
$WSL_DISTRO = $cfg.wsl_distro
$WSL_FIND = $cfg.wsl_find
$CLUSTER_PROBE = $cfg.cluster_probe
$CLUSTER_FIND = $cfg.cluster_find
if ($cfg.cluster_ssh) { $CLUSTER_SSH = $cfg.cluster_ssh } else { $CLUSTER_SSH = 'cluster' }
$IGNORE = @($cfg.ignore)
$LANG = if ($cfg.lang -eq 'en') { 'en' } else { 'zh' }   # config 键 lang：zh（缺省）/ en
function L([string]$zh, [string]$en) { if ($script:LANG -eq 'en') { $en } else { $zh } }

# Win 正本全集：自动发现 <工作前缀>*\<code_dir> + 方向层公共库（新增工作零登记）
$WIN_DIRS = @(Get-ChildItem $ROOT -Directory -Filter ($WORKS + '*') |
              ForEach-Object { Join-Path $_.FullName $CODE } |
              Where-Object { Test-Path $_ })
$WIN_DIRS += Join-Path $ROOT $PUBD

# ---- 收集三方 (basename -> hash 集合) ----
function Get-WinIndex {
    $idx = @{}
    foreach ($d in $WIN_DIRS) {
        if (-not (Test-Path $d)) { continue }
        Get-ChildItem -Recurse -File $d | Where-Object {
            $_.Extension -in '.py', '.sh' -and $_.FullName -notmatch '__pycache__'
        } | ForEach-Object {
            $bn = $_.Name
            if ($IGNORE -contains $bn) { continue }
            if (-not $idx.ContainsKey($bn)) { $idx[$bn] = @() }
            $idx[$bn] += (Get-FileHash $_.FullName -Algorithm MD5).Hash.Substring(0, 8).ToLower()
        }
    }
    return $idx
}

function Get-RemoteIndex([string]$Label, [string]$BashCmd) {
    # 返回 @{ Index = hashtable; Reachable = bool }
    $raw = wsl -d $WSL_DISTRO -e bash -lc $BashCmd 2>$null
    if (-not $raw) {
        Write-Host ("[!] {0} {1}" -f $Label, (L "不可达或无匹配文件，跳过该侧" "unreachable or no matching files, side skipped")) -ForegroundColor Yellow
        return @{ Index = @{}; Reachable = $false }
    }
    $idx = @{}
    foreach ($ln in $raw) {
        if ($ln -match '^([0-9a-f]{32})\s+(.+)$') {
            $bn = [IO.Path]::GetFileName($Matches[2])
            if ($IGNORE -contains $bn) { continue }
            if (-not $idx.ContainsKey($bn)) { $idx[$bn] = @() }
            $idx[$bn] += $Matches[1].Substring(0, 8).ToLower()
        }
    }
    return @{ Index = $idx; Reachable = $true }
}

# ---- 对比 ----
function Compare-Side([string]$Side, $remote, $win, $winByHash) {
    $drift = 0; $orphan = 0; $same = 0; $renamed = 0
    foreach ($bn in $remote.Keys) {
        if ($win.ContainsKey($bn)) {
            $r = @($remote[$bn]); $w = @($win[$bn])
            $rs = ($r | Sort-Object -Unique) -join ','   # 集合语义：多副本数量差不算漂移；
            $ws = ($w | Sort-Object -Unique) -join ','   # 先 join 成串再 -eq（优先级陷阱）
            if ($rs -eq $ws) { $same++ }
            else {
                $drift++
                Write-Host ((L "[漂移]" "[drift]") + (" {0}   {1}: {2}  Win: {3}" -f $bn, $Side, ($r -join ','), ($w -join ','))) -ForegroundColor Red
            }
        } else {
            # basename 对不上 → hash 反查兜底：内容与 Win 某文件一致 = 改名部署
            $hit = $null
            foreach ($h in @($remote[$bn])) { if ($winByHash.ContainsKey($h)) { $hit = $winByHash[$h]; break } }
            if ($hit) {
                $renamed++
                Write-Host ((L "[改名部署]" "[renamed-deploy]") + (" {0}  =  Win: {1}" -f $bn, $hit)) -ForegroundColor DarkGray
            } else {
                $orphan++
                Write-Host ((L "[待回传]" "[pending-copy-back]") + (" {0}   " -f $bn) + (L "仅存在于" "exists only on") + (" {0}" -f $Side)) -ForegroundColor Magenta
            }
        }
    }
    Write-Host ((L "  {0}: 一致 {1} | 漂移 {2} | 改名部署 {3} | 待回传 {4}" "  {0}: same {1} | drift {2} | renamed {3} | pending-copy-back {4}") -f $Side, $same, $drift, $renamed, $orphan)
    return @{ Drift = $drift; Orphan = $orphan }
}

# ---- 主流程 ----
Write-Host (L "=== 副本巡检（Win 正本 vs WSL vs 集群；引擎 = openfoam-research-init skill）===" "=== Replica audit (Win canonical vs WSL vs cluster; engine = openfoam-research-init skill) ===")
Write-Host ((L "正本目录: " "Canonical directories: ") + (($WIN_DIRS | ForEach-Object { $_ }) -join ' ; '))

$win = Get-WinIndex
# hash → basename 反查表（识别改名部署）
$winByHash = @{}
foreach ($d in $WIN_DIRS) {
    if (-not (Test-Path $d)) { continue }
    Get-ChildItem -Recurse -File $d | Where-Object {
        $_.Extension -in '.py', '.sh' -and $_.FullName -notmatch '__pycache__'
    } | ForEach-Object {
        if ($IGNORE -contains $_.Name) { continue }
        $winByHash[(Get-FileHash $_.FullName -Algorithm MD5).Hash.Substring(0, 8).ToLower()] = $_.Name
    }
}
Write-Host ((L "Win 正本: {0} 个唯一文件名" "Win canonical: {0} unique filenames") -f $win.Count)

$wsl = Get-RemoteIndex 'WSL' $WSL_FIND
$clusterRaw = wsl -d $WSL_DISTRO -e bash -lc $CLUSTER_PROBE 2>$null
$clusterReachable = $clusterRaw -match '__REACHABLE__'
$cluster = if ($clusterReachable) { Get-RemoteIndex (L '集群' 'cluster') ("ssh -o ConnectTimeout=10 -o BatchMode=yes " + $CLUSTER_SSH + " '" + $CLUSTER_FIND + "'") } else { Write-Host (L '[!] 集群不可达（私钥到期或网络），跳过' '[!] cluster unreachable (key expired or network), skipped') -ForegroundColor Yellow; @{ Index = @{}; Reachable = $false } }

$r1 = Compare-Side 'WSL' $wsl.Index $win $winByHash
$r2 = Compare-Side (L '集群' 'cluster') $cluster.Index $win $winByHash

$total = $r1.Drift + $r1.Orphan + $r2.Drift + $r2.Orphan
$unreachable = (-not $wsl.Reachable) -or (-not $clusterReachable)
Write-Host ""
if ($unreachable -and $total -eq 0) { Write-Host (L '汇总: 可达侧全部一致（有侧不可达）' 'Summary: reachable sides all consistent (some side unreachable)'); exit 2 }
if ($total -eq 0) { Write-Host (L '汇总: 三方全部一致 ✔' 'Summary: all three sides consistent ✔'); exit 0 }
Write-Host ((L "汇总: 漂移+待回传 共 {0} 项——漂移以 Win 为正（下行覆盖），待回传项收工前回传归档" "Summary: {0} drift/pending items — drift resolves in favor of Win (downstream overwrite); copy pending items back before closing") -f $total)
exit 1
