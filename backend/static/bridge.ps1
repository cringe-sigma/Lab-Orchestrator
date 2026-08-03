$s="10.65.80.155"     # 服务器IP
$b="10.42.0.174"      # 板子IP
$u="gjh"              # SSH用户名
$p="gejiahao"         # SSH密码
$t="你的TOKEN"         # 网页上显示的Token

Write-Host "=== Lab Orchestrator Bridge ===" -ForegroundColor Cyan
Write-Host "板子: $u@$b" -ForegroundColor Yellow

$body = '{"token":"' + $t + '"}'
$r = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
Write-Host "已上线 board_id=$($r.board_id)" -ForegroundColor Green
Write-Host "去网页 http://${s}:5173 操作板子" -ForegroundColor Cyan
Write-Host "本窗口保持运行，不要关闭`n"

while($true){
    try {
        $cmds = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$($r.board_id)/pending-commands" -TimeoutSec 30
        foreach($x in $cmds.commands){
            Write-Host "执行: $($x.command)" -ForegroundColor Gray
            $o = ssh -o StrictHostKeyChecking=no "$u@$b" $x.command 2>&1 | Out-String
            $result = @{cmd_id=$x.id; output=$o} | ConvertTo-Json
            Invoke-RestMethod -Uri "http://${s}:8000/api/boards/$($r.board_id)/command-result" -Method Post -Body $result -ContentType "application/json" | Out-Null
            Write-Host "  完成" -ForegroundColor Green
        }
    } catch {}
    Start-Sleep -Seconds 2
}
