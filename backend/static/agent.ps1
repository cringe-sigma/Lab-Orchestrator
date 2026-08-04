$s="0.0.0.0"
$port=9999
$b="10.42.0.174"
$u="gjh"
$t="YOUR_TOKEN"

Write-Host "=== Agent ===" -ForegroundColor Cyan
Write-Host "Board: $u@$b  Port: $port"

# SSH key setup
$keyPath="$env:USERPROFILE\.ssh\id_ed25519"
if(-not(Test-Path $keyPath)){
    Write-Host "Setting up SSH key (enter password once)..." -ForegroundColor Yellow
    ssh-keygen -t ed25519 -f $keyPath -N '""' -q 2>&1|Out-Null
    Get-Content "$keyPath.pub"|ssh -o StrictHostKeyChecking=no "$u@$b" "mkdir -p ~/.ssh;cat>>~/.ssh/authorized_keys;chmod 600 ~/.ssh/authorized_keys"
}

# Register with server
$body='{"token":"'+$t+'","agent_port":'+$port+'}'
Invoke-RestMethod -Uri "http://${s}:8000/api/boards/register-agent" -Method Post -Body $body -ContentType "application/json"|Out-Null
Write-Host "Registered. Waiting for commands on port $port..." -ForegroundColor Green

# Simple HTTP server that runs SSH commands
$listener=[System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://+:$port/")
$listener.Start()

$cwd="~"
while($true){
    $ctx=$listener.GetContext()
    $req=$ctx.Request
    $resp=$ctx.Response

    if($req.HttpMethod -eq "POST" -and $req.Url.AbsolutePath -eq "/exec"){
        $reader=[System.IO.StreamReader]::new($req.InputStream)
        $body=$reader.ReadToEnd()
        $reader.Close()
        $cmd=$body

        if($cmd -match '^cd\s+(.+)"?$'){
            $target=$matches[1]
            $newdir=ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$u@$b" "cd $cwd 2>/dev/null;cd $target 2>/dev/null&&pwd" 2>&1|Out-String
            $newdir=$newdir.Trim()
            if($newdir -and $newdir -notmatch '^\$'){$cwd=$newdir;$output=""}else{$output="cd: $target: No such directory`n"}
        }else{
            $output=ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$u@$b" "cd $cwd 2>/dev/null;$cmd" 2>&1|Out-String
        }

        $resp.ContentType="text/plain"
        $bytes=[Text.Encoding]::UTF8.GetBytes($output+$cwd+"`n")
        $resp.OutputStream.Write($bytes,0,$bytes.Length)
    }
    $resp.Close()
}
