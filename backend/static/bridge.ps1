$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$t="YOUR_TOKEN"

Write-Host "=== Bridge ===" -ForegroundColor Cyan
Write-Host "Server: $s  Board: $u@$b"

# Auto setup SSH key if missing
$keyPath = "$env:USERPROFILE\.ssh\id_ed25519"
if(-not (Test-Path $keyPath)){
    Write-Host "Setting up SSH key..." -ForegroundColor Yellow
    ssh-keygen -t ed25519 -f $keyPath -N '""' -q 2>&1 | Out-Null
    Write-Host "Copying key to $u@$b (enter password once):" -ForegroundColor Yellow
    Get-Content "$keyPath.pub" | ssh -o StrictHostKeyChecking=no "$u@$b" "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    Write-Host "SSH key installed" -ForegroundColor Green
} else {
    Write-Host "SSH key found" -ForegroundColor Green
}

# Register
$body = '{"token":"'+$t+'"}'
$r = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
$bid = $r.board_id
Write-Host "Registered: board_id=$bid" -ForegroundColor Green
Write-Host "Open http://${s}:5173 to use the board" -ForegroundColor Cyan

# SSH ControlMaster
$socket = "/tmp/ssh-mux-$bid"
Write-Host "Starting SSH session..." -ForegroundColor Yellow
ssh -M -S $socket -o StrictHostKeyChecking=no -o ConnectTimeout=5 -fN "$u@$b" 2>&1 | Out-Null
Write-Host "SSH ready" -ForegroundColor Green

# Command loop with working directory tracking
$cwd = "~"
while($true){
    try{
        $cmds = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/pending-commands" -TimeoutSec 30
        foreach($x in $cmds.commands){
            $cmd = $x.command
            Write-Host "${cwd}$ $cmd" -ForegroundColor Gray

            # Ensure master is alive
            $test = ssh -S $socket -o StrictHostKeyChecking=no -o ConnectTimeout=3 "$u@$b" "echo OK" 2>&1 | Out-String
            if($test -notmatch "OK"){
                Write-Host "SSH disconnected, reconnecting..." -ForegroundColor Yellow
                ssh -M -S $socket -o StrictHostKeyChecking=no -o ConnectTimeout=5 -fN "$u@$b" 2>&1 | Out-Null
                Start-Sleep -Seconds 1
            }

            # Handle cd: update cwd
            if($cmd -match '^\s*cd\s+(.+)'){
                $target = $matches[1].Trim()
                $newdir = ssh -S $socket -o StrictHostKeyChecking=no "$u@$b" "cd ${cwd} 2>/dev/null; cd ${target} 2>/dev/null && pwd" 2>&1 | Out-String
                $newdir = $newdir.Trim()
                if($newdir -and $newdir -notmatch '^\$'){
                    $cwd = $newdir
                    $o = ""
                } else {
                    $o = "cd: ${target}: No such directory"
                }
            } else {
                # Run in current directory
                $o = ssh -S $socket -o StrictHostKeyChecking=no "$u@$b" "cd ${cwd} 2>/dev/null; ${cmd}" 2>&1 | Out-String
            }

            $result = @{cmd_id=$x.id; output=$o} | ConvertTo-Json
            Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/command-result" -Method Post -Body $result -ContentType "application/json" | Out-Null
        }
    }catch{}
    Start-Sleep -Milliseconds 200
}
