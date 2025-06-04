SecretData = {
    "peer_id": "...",                # Unique peer identifier
    "public_key": "...",             # Peer’s public key (base64)
    "local_endpoint": "ip:port",     # Local address
    "public_endpoint": "ext_ip:port",# STUN/UPnP result
    "ice_candidates": [...],         # Optional, for WebRTC
    "offer_sdp": "...",              # Optional, for WebRTC
    "connection_key": "...",         # Secure random key
    "signature": "...",              # Signature of the above fields
}