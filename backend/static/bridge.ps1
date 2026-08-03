$s="10.65.80.155"
$b="10.42.0.174"
$u="gjh"
$p="gejiahao"
$t="你的TOKEN"

$ErrorActionPreference="Stop"
Write-Host "=== Bridge ===" -ForegroundColor Cyan

# 注册
$body='{"token":"'+$t+'"}'
$r=Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"
$bid=$r.board_id
Write-Host "board_id=$bid" -ForegroundColor Green

# 命令通道 (后台)
Start-Job -ScriptBlock {
    param($srv,$bid,$u,$b)
    while($true){
        try{$cmds=Invoke-RestMethod -Uri "http://${srv}:8000/api/boards/$bid/pending-commands" -TimeoutSec 30
        foreach($x in $cmds.commands){$o=ssh -o StrictHostKeyChecking=no -o BatchMode=yes "$u@$b" $x.command 2>&1|Out-String
        Invoke-RestMethod -Uri "http://${srv}:8000/api/boards/$bid/command-result" -Method Post -Body (ConvertTo-Json @{cmd_id=$x.id;output=$o}) -ContentType "application/json"|Out-Null}}catch{};Start-Sleep -Seconds 2}
} -ArgumentList $s,$bid,$u,$b|Out-Null

# 终端通道: .NET原生WebSocket
Write-Host "终端连接中..." -ForegroundColor Yellow

try {
    $ws=[System.Net.WebSockets.ClientWebSocket]::new()
    $ct=[System.Threading.CancellationToken]::None
    $ws.Options.SetRequestHeader("X-Bridge-Register","1")
    $task=$ws.ConnectAsync("ws://${s}:8000/ws/bridge-terminal/$bid",$ct)
    while(!$task.IsCompleted){Start-Sleep -Milliseconds 50}
    if($ws.State -ne 'Open'){throw "WebSocket连接失败: $($ws.State)"}

    # 启动SSH
    $psi=New-Object Diagnostics.ProcessStartInfo
    $psi.FileName="ssh"
    $psi.Arguments="-tt -o StrictHostKeyChecking=no -o BatchMode=yes $u@$b"
    $psi.UseShellExecute=$false
    $psi.RedirectStandardInput=$true
    $psi.RedirectStandardOutput=$true
    $psi.RedirectStandardError=$true
    $proc=[Diagnostics.Process]::Start($psi)

    Write-Host "终端已连接！去网页点 [连接]" -ForegroundColor Green

    # SSH输出→WebSocket (后台)
    $outJob=Start-Job -ScriptBlock {
        param($p,$w,$c)
        $buf=[byte[]]::new(4096)
        $out=$p.StandardOutput.BaseStream
        while($true){
            try{$n=$out.Read($buf,0,4096);if($n -gt 0){
                $seg=[ArraySegment[byte]]::new($buf[0..($n-1)])
                $w.SendAsync($seg,[System.Net.WebSockets.WebSocketMessageType]::Text,$true,$c)|Out-Null
            }}catch{break}
        }
    } -ArgumentList $proc,$ws,$ct

    # WebSocket→SSH (主线程)
    $inBuf=[byte[]]::new(4096)
    while($ws.State -eq 'Open'){
        $seg=[ArraySegment[byte]]::new($inBuf)
        $task2=$ws.ReceiveAsync($seg,$ct)
        while(!$task2.IsCompleted){Start-Sleep -Milliseconds 50}
        if($task2.Result.Count -gt 0 -and $task2.Result.MessageType -eq 'Text'){
            $txt=[Text.Encoding]::UTF8.GetString($inBuf,0,$task2.Result.Count)
            $proc.StandardInput.Write($txt)
        }
    }
} catch {
    Write-Host "终端通道失败: $_" -ForegroundColor Red
}

$proc.Kill()
Write-Host "断开" -ForegroundColor Red
