$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$p="gejiahao"
$t="你的TOKEN"

Write-Host "=== Bridge ===" -ForegroundColor Cyan
Write-Host "板子: $u@$b" -ForegroundColor Yellow

# 生成 plink 免密码命令
$plink = "echo $p | plink -pw $p -ssh -batch $u@$b"
if (-not (Get-Command plink 2>$null)) {
    # plink not found, try ssh with sshpass, or use key
    $plink = "sshpass -p $p ssh -o StrictHostKeyChecking=no $u@$b"
    if (-not (Get-Command sshpass 2>$null)) {
        Write-Host "警告: plink/sshpass 未安装，尝试用密钥" -ForegroundColor Yellow
        $plink = "ssh -o StrictHostKeyChecking=no -o BatchMode=yes $u@$b"
    }
}

$body = '{"token":"' + $t + '"}'
$r = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
Write-Host "已上线 board_id=$($r.board_id)" -ForegroundColor Green
Write-Host "去网页 http://${s}:5173 操作" -ForegroundColor Cyan
Write-Host ""

while($true){
    try {
        $cmds = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$($r.board_id)/pending-commands" -TimeoutSec 30
        foreach($x in $cmds.commands){
            Write-Host "> $($x.command)" -ForegroundColor Gray
            $o = Invoke-Expression "$plink `"$($x.command)`"" 2>&1 | Out-String
            $result = @{cmd_id=$x.id; output=$o} | ConvertTo-Json
            Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$($r.board_id)/command-result" -Method Post -Body $result -ContentType "application/json" | Out-Null
        }
    } catch {}
    Start-Sleep -Seconds 2
}
