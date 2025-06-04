
NEXT STEPS
    P2P TECH
        make the "secret data" legit!
    OTHER
        - File integrity & resume: No hashing, no chunk checksums, no resume support if the transfer is interrupted.
        - Scalability: Single-threaded FastAPI with in-memory dicts cannot handle many clients or large files efficiently.
    UI
        - make a website
        - make file attachement possible

POST PRODUCTION
    SEQURITY:
        - Dynamic key generation: No cryptographically secure random keys are generated for peers.
        - Real security: The connection_key is hardcoded to "test_key", with no TLS or encryption. + The server and client use plain HTTP; no SSL/TLS configuration.
        - Authentication/authorization: Anyone knowing IDs and reservation IDs can fetch secrets. UNDERSTAND WHAT THAT MEANS
    ERROR HANDL:
        - Error handling & retries: Minimal checks; if UPnP and STUN both fail, or the peer is unreachable, the code may crash.