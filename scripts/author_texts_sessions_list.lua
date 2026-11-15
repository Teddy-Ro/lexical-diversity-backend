#!lua flags=no-writes
-- Pass session keys from redis-cli --scan as KEYS, not as ARGV.
local sessions = {}

for _, session_key in ipairs(KEYS) do
    if string.sub(session_key, 1, 21) ~= 'author_texts:session:' then
        return redis.error_reply('Only author_texts:session:<id> keys are allowed')
    end

    local user_id = redis.call('GET', session_key)
    if user_id then
        sessions[#sessions + 1] = cjson.encode({
            session_key = session_key,
            user_id = user_id,
            ttl_seconds = redis.call('TTL', session_key)
        })
    end
end

return '[' .. table.concat(sessions, ',') .. ']'
