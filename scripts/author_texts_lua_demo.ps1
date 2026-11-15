param(
    [string]$BaseUrl = 'http://127.0.0.1:8000',
    [string]$Username = 'researcher_1',
    [string]$Password = 'author_texts_demo'
)

$ErrorActionPreference = 'Stop'
$baseUri = [Uri]$BaseUrl
if (-not $baseUri.IsLoopback) { throw 'This demonstration only uses a local API.' }
$dockerContainer = 'author_texts-redis'
$webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$body = @{ username = $Username; password = $Password } | ConvertTo-Json -Compress
$loggedIn = $false

function Invoke-AuthorTextsRedis {
    param([string[]]$RedisArguments)
    $result = & docker exec $dockerContainer redis-cli --raw @RedisArguments
    if ($LASTEXITCODE -ne 0) { throw 'Redis command failed.' }
    return ($result -join "`n")
}

try {
    $login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/author_texts_users/login" `
        -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($body)) -WebSession $webSession
    $loggedIn = $true
    $cookie = $webSession.Cookies.GetCookies([Uri]"$BaseUrl/api")['author_texts_session']
    if (-not $cookie) { throw 'The login response did not create a session cookie.' }
    $key = 'author_texts:session:' + $cookie.Value
    $missingKey = 'author_texts:session:lua_missing_' + [Guid]::NewGuid().ToString('N')
    foreach ($name in @('author_texts_session_get.lua', 'author_texts_sessions_list.lua')) {
        & docker cp (Join-Path $PSScriptRoot $name) "${dockerContainer}:/tmp/$name"
        if ($LASTEXITCODE -ne 0) { throw 'Could not copy the Lua script into Redis.' }
    }

    Write-Host 'AUTHOR TEXTS: Redis Lua read demonstration'
    Write-Host ('API login succeeded; user_id = ' + $login.author_texts_user_id)
    $beforeValue = Invoke-AuthorTextsRedis -RedisArguments @('GET', $key)
    $beforeTtl = [int](Invoke-AuthorTextsRedis -RedisArguments @('TTL', $key))

    Write-Host "`nredis-cli --eval /tmp/author_texts_session_get.lua <session-key>"
    $singleJson = Invoke-AuthorTextsRedis -RedisArguments @('--eval', '/tmp/author_texts_session_get.lua', $key)
    $single = $singleJson | ConvertFrom-Json
    $single | ConvertTo-Json
    if ($single.user_id -ne [string]$login.author_texts_user_id -or $single.ttl_seconds -le 0) {
        throw 'Lua did not return the active API session.'
    }

    Write-Host "`nredis-cli --eval /tmp/author_texts_sessions_list.lua <session-key> <missing-key>"
    $listJson = Invoke-AuthorTextsRedis -RedisArguments @('--eval', '/tmp/author_texts_sessions_list.lua', $key, $missingKey)
    Write-Host $listJson
    $sessions = @($listJson | ConvertFrom-Json)
    if ($sessions.Count -ne 1 -or $sessions[0].user_id -ne $single.user_id) {
        throw 'Lua session list does not match the single-session result.'
    }

    $afterValue = Invoke-AuthorTextsRedis -RedisArguments @('GET', $key)
    $afterTtl = [int](Invoke-AuthorTextsRedis -RedisArguments @('TTL', $key))
    if ($afterValue -ne $beforeValue -or $afterTtl -gt $beforeTtl -or $afterTtl -le 0) {
        throw 'Read-only session verification failed.'
    }
    Write-Host "`nPASS: user_id is unchanged; TTL was not extended."

    Write-Host "`nredis-cli --eval /tmp/author_texts_session_get.lua <missing-key>"
    $missingJson = Invoke-AuthorTextsRedis -RedisArguments @('--eval', '/tmp/author_texts_session_get.lua', $missingKey)
    $missing = $missingJson | ConvertFrom-Json
    $missing | ConvertTo-Json
    if ($null -ne $missing.user_id -or $missing.ttl_seconds -ne -2) {
        throw 'Missing-session verification failed.'
    }
    Write-Host "`nPASS: both Lua scripts executed against Redis."
} finally {
    if ($loggedIn) {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/author_texts_users/logout" -WebSession $webSession | Out-Null
        Write-Host 'Demo session was revoked through logout.'
    }
}
