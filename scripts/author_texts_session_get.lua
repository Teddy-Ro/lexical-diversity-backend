#!lua flags=no-writes
-- KEYS[1]: author_texts:session:<session ID from cookie>.
if #KEYS ~= 1 or string.sub(KEYS[1], 1, 21) ~= 'author_texts:session:' then
    return redis.error_reply('Pass one author_texts:session:<id> key')
end

local session_key = KEYS[1]
local user_id = redis.call('GET', session_key)

return cjson.encode({
    session_key = session_key,
    user_id = user_id or cjson.null,
    ttl_seconds = redis.call('TTL', session_key)
})
