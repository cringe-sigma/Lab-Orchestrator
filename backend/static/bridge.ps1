$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$t="YOUR_TOKEN"

Write-Host "=== Bridge ===" -ForegroundColor Cyan
Write-Host "Server: $s  Board: $u@$b"

# Check sshpass
$hasPass = $null -ne (Get-Command sshpass -ErrorAction SilentlyContinue)
if(-not $hasPass){ Write-Host "sshpass not found. Install: apt install sshpass" -ForegroundColor Yellow }

# Register
$body = '{"token":"'+$t+'"}'
$r = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
$bid = $r.board_id
Write-Host "Registered: board_id=$bid" -ForegroundColor Green
Write-Host "Open http://${s}:5173 to use the board" -ForegroundColor Cyan

# SSH ControlMaster for persistent connection
$socket = "/tmp/ssh-mux-$bid"
Write-Host "Starting SSH master connection..." -ForegroundColor Yellow
if($hasPass){
    sshpass -p $p ssh -M -S $socket -o StrictHostKeyChecking=no -o ConnectTimeout=5 -fN "$u@$b" 2>&1 | Out-Null
} else {
    ssh -M -S $socket -o StrictHostKeyChecking=no -o ConnectTimeout=5 -fN "$u@$b" 2>&1 | Out-Null
}
Write-Host "SSH master ready" -ForegroundColor Green

# Command loop
while($true){
    try{
        $cmds = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/pending-commands" -TimeoutSec 30
        foreach($x in $cmds.commands){
            Write-Host "> $($x.command)" -ForegroundColor Gray
            if($hasPass){
                $o = sshpass -p $p ssh -S $socket -o StrictHostKeyChecking=no "$u@$b" $x.command 2>&1 | Out-String
            } else {
                $o = ssh -S $socket -o StrictHostKeyChecking=no "$u@$b" $x.command 2>&1 | Out-String
            }
            $result = @{cmd_id=$x.id; output=$o} | ConvertTo-Json
            Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$bid/command-result" -Method Post -Body $result -ContentType "application/json" | Out-Null
        }
    }catch{}
    Start-Sleep -Milliseconds 200
}
