/** One store read of live:state and live:control, as GET (red team 6): a key of another type (a hash, a JSON document
 *  made in the Upstash console) makes the read fail, so the watch stops and /api/v1/live hides every post, where
 *  MGET would read it as missing and ignore the owner's stop, or forget what was posted. One command, as MGET was. */
export const READ_LUA = "return {redis.call('GET', KEYS[1]), redis.call('GET', KEYS[2])}";

/** The one write of live:state, made only while this run still holds live:lock (its token is the run's start time),
 *  and the lock released with it (red team 10). Returns 1 when written, 0 when another run holds the lock. */
export const WRITE_LUA = "if redis.call('GET', KEYS[1]) == ARGV[1] then redis.call('SET', KEYS[2], ARGV[2]); redis.call('DEL', KEYS[1]); return 1 end return 0";
