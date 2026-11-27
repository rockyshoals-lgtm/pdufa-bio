/** One store read of live:state and live:control, as GET (red team 6): a key of another type (a hash, a JSON document
 *  made in the Upstash console) makes the read fail, so the watch stops and /api/v1/live hides every post, where
 *  MGET would read it as missing and ignore the owner's stop, or forget what was posted. One command, as MGET was. */
export const READ_LUA = "return {redis.call('GET', KEYS[1]), redis.call('GET', KEYS[2])}";
