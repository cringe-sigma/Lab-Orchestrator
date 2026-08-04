$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$t="YOUR_TOKEN"

$ErrorActionPreference="Continue"
Write-Host "=== Bridge ===" -ForegroundColor Cyan

# SSH key
$k="$env:USERPROFILE\.ssh\id_ed25519"
if(-not(Test-Path $k)){ssh-keygen -t ed25519 -f $k -N '""' -q 2>&1|Out-Null;Get-Content "$k.pub"|ssh -o StrictHostKeyChecking=no "$u@$b" "mkdir -p ~/.ssh;cat>>~/.ssh/authorized_keys;chmod 600 ~/.ssh/authorized_keys"}

# Register
$r=Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body ('{"token":"'+$t+'"}') -ContentType "application/json"
$bid=$r.board_id
Write-Host "board_id=$bid" -ForegroundColor Green

$cwd="~"
while($true){
    $cmds=Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/pending-commands" -TimeoutSec 30 -ErrorAction SilentlyContinue
    if($cmds.commands){
        foreach($x in $cmds.commands){
            $cmd=$x.command
            Write-Host "${cwd}$ $cmd" -ForegroundColor Gray

            if($cmd -match '^\s*cd\s+(.+)'){
                $tgt=$matches[1]
                $d=ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$u@$b" "cd ${cwd};cd ${tgt} 2>/dev/null&&pwd" 2>&1|Out-String
                $d=$d.Trim()
                if($d -and $d -notmatch '^\$'){$cwd=$d;$o=""}else{$o="cd: ${tgt}: No such directory"}
            }else{
                $o=ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$u@$b" "cd ${cwd};${cmd}" 2>&1|Out-String
            }

            $o += "`n${cwd}$ "
            Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/command-result" -Method Post -Body (ConvertTo-Json @{cmd_id=$x.id;output=$o}) -ContentType "application/json" -ErrorAction SilentlyContinue | Out-Null
        }
    }
    Start-Sleep -Milliseconds 200
}
