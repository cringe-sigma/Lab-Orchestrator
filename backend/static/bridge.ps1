
$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$p="gejiahao"
$t="你的TOKEN"

Write-Host "=== Bridge ===" -ForegroundColor Cyan

# 注册
$body = '{"token":"' + $t + '"}'
$r = Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
$bid = $r.board_id
Write-Host "board_id=$bid 已上线" -ForegroundColor Green

# === 命令轮询 (后台job) ===
$cmdJob = Start-Job -ScriptBlock {
    param($srv,$bid,$u,$b,$p)
    while($true){
        try{
            $cmds=Invoke-RestMethod -Uri "http://${srv}:8000/api/boards/$bid/pending-commands" -TimeoutSec 30
            foreach($x in $cmds.commands){
                $o=ssh -o StrictHostKeyChecking=no "$u@$b" $x.command 2>&1|Out-String
                Invoke-RestMethod -Uri "http://${srv}:8000/api/boards/$bid/command-result" -Method Post -Body (ConvertTo-Json @{cmd_id=$x.id;output=$o}) -ContentType "application/json"|Out-Null
            }
        }catch{}
        Start-Sleep -Seconds 2
    }
} -ArgumentList $s,$bid,$u,$b,$p

Write-Host "命令通道就绪。终端功能需新版bridge，暂用执行命令。" -ForegroundColor Yellow

# 等待命令job
Wait-Job $cmdJob | Out-Null
