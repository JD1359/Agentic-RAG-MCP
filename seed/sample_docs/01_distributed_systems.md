# Distributed Systems Fundamentals

## At-least-once vs exactly-once delivery

In any distributed messaging system, you have to choose a delivery semantic.
**At-most-once** delivery means messages can be lost but never duplicated.
**At-least-once** delivery means messages will be delivered one or more times -
duplicates are possible but messages are never lost. **Exactly-once** delivery
means each message is delivered exactly one time.

In practice, exactly-once delivery across an unreliable channel like SMTP or SMS
is impossible. The achievable contract is at-least-once delivery combined with
idempotency on the receiver side. The client supplies an idempotency key, and
the server uses that key to deduplicate retries.

## Dead-letter queues (DLQ)

A dead-letter queue holds messages that have failed processing beyond a
configured retry budget. Without a DLQ, a single bad payload can wedge a worker
pool indefinitely. With a DLQ, after N failed attempts the message moves to the
dead-letter stream for manual inspection, allowing the rest of the pipeline to
continue.

A typical configuration is 3 retry attempts with exponential backoff: 5 seconds,
25 seconds, 125 seconds. After the third failure the message is dead-lettered.

## Redis Streams and consumer groups

Redis Streams are an append-only log primitive in Redis. Unlike Redis Lists,
Streams support consumer groups: multiple consumers can read from the same
stream in parallel, with each message delivered to exactly one consumer in the
group. Consumer groups also track pending messages that have been delivered but
not acknowledged, enabling automatic claim of abandoned work.

This makes Redis Streams a better choice than List + LPOP for production work
queues.

## Per-channel rate limiting

A common mistake is to apply a single global rate limit across all output
channels. In a notification system sending email via SendGrid (~100 req/s) and
SMS via Twilio (~10 req/s), a global limit must be set to the most restrictive
channel, starving the faster ones. Per-channel rate limiting with separate
token buckets allows each channel to operate at its maximum throughput.

## Graceful shutdown

The correct sequence on SIGTERM is:
1. Stop accepting new requests (close the listener).
2. Drain in-flight work (allow workers to finish their current job).
3. Close database and queue connections.
4. Flush logs and metrics.
5. Exit.

Done incorrectly you lose in-flight messages on every deploy.
