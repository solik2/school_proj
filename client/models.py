from typing import List, Optional
from pydantic import BaseModel, constr, IPvAnyAddress, Field

class ICECandidate(BaseModel):
    """ICE candidate information"""
    foundation: str
    component: int
    protocol: str = Field(..., regex="^(udp|tcp)$")
    priority: int
    ip: IPvAnyAddress
    port: int = Field(..., ge=1, le=65535)
    type: str = Field(..., regex="^(host|srflx|prflx|relay)$")

class SecretInfo(BaseModel):
    """Connection secret information"""
    local_endpoint: constr(regex=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$")
    public_endpoint: constr(regex=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$")
    public_ip: IPvAnyAddress
    tcp_port: int = Field(..., ge=1, le=65535)
    connection_key: str = Field(..., min_length=8)
    ice_candidates: Optional[List[ICECandidate]] = []
    offer_sdp: Optional[str] = Field(None, max_length=65535)

class ApprovalRequest(BaseModel):
    """Request to approve connection with secret info"""
    secret_info: SecretInfo