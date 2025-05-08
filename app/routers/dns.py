"""
Writer: Arvin Salehi
Auto Documented by claude-sonnet-3.7

DNS Router Module

This module implements the core DNS functionality of the service, providing endpoints
for managing DNS records (A and CNAME types). It handles record creation, querying,
resolution, and deletion with proper validation and error handling.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import List
from app.models.dns import DNSRecord
from app.db.connectors import get_dns_collection
from app.utils.dns_validator import validate_hostname, validate_record_type, validate_ip_address

router = APIRouter()

async def validate_hostname_param(hostname: str = Path(...)) -> str:
    """
    Validate the hostname path parameter.
    
    Args:
        hostname: The hostname to validate
        
    Returns:
        The validated hostname
        
    Raises:
        HTTPException: If the hostname is invalid
    """
    is_valid, error_message = validate_hostname(hostname)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"Invalid hostname: {error_message}")
    return hostname

async def validate_record_type_param(type: str = Query(...)) -> str:
    """
    Validate the record type query parameter.
    
    Args:
        type: The record type to validate
        
    Returns:
        The validated record type (uppercase)
        
    Raises:
        HTTPException: If the record type is invalid
    """
    is_valid, error_message = validate_record_type(type)
    if not is_valid:
        raise HTTPException(status_code=422, detail=error_message)
    return type.upper()

@router.post(
    "/api/dns",
    response_description="Add new DNS",
    response_model=DNSRecord,
    response_model_by_alias=False,
)
async def add_dns_record(record: DNSRecord) -> DNSRecord:
    """
    Add a new DNS record to the system.
    
    This endpoint handles the creation of new DNS records with the following rules:
    - Only A and CNAME record types are supported
    - CNAME records cannot coexist with other records
    - A records cannot be added if a CNAME exists
    - Duplicate A records are not allowed
    
    Args:
        record (DNSRecord): The DNS record to be added
        
    Returns:
        DNSRecord: The created DNS record
        
    Raises:
        HTTPException: 
            - 400: Invalid record type
            - 400: CNAME conflict
            - 409: Duplicate A record
    """
    hostname = record.hostname
    rtype = record.type.upper()
    value = record.value

    dns_collection = get_dns_collection()
    existing_records = await dns_collection.find({"hostname": hostname}).to_list(length=None)

    # CNAME rules
    if rtype == "CNAME":
        if existing_records:
            raise HTTPException(status_code=400, detail="CNAME cannot coexist with other records")
        record_dict = record.model_dump()
        result = await dns_collection.insert_one(record_dict)
        created_record = await dns_collection.find_one({"_id": result.inserted_id})
        return DNSRecord(**created_record)

    # A record rules
    for existing in existing_records:
        if existing.get("type") == "CNAME":
            raise HTTPException(status_code=400, detail="Cannot add A record when CNAME exists")
        if existing.get("type") == "A" and existing.get("value") == value:
            raise HTTPException(status_code=409, detail="Duplicate A record")
    
    record_dict = record.model_dump()
    result = await dns_collection.insert_one(record_dict)
    created_record = await dns_collection.find_one({"_id": result.inserted_id})
    
    return DNSRecord(**created_record)

@router.get(
    "/api/dns/{hostname}/records",
    response_description="Get hostname records",
    response_model=List
)
async def list_records(hostname: str = Depends(validate_hostname_param)) -> List:
    """
    List all DNS records for a specific hostname.
    
    Args:
        hostname (str): The hostname to query
        
    Returns:
        List: List of DNS records for the specified hostname
        
    Raises:
        HTTPException: 404 if hostname not found
    """
    collection = get_dns_collection()
    records = await collection.find({"hostname": hostname}).to_list(100) # In production we use skip and limit params
    
    if not records:
        raise HTTPException(404, "Hostname not found")
    
    # Convert ObjectId to str for JSON serialization
    # More info https://www.mongodb.com/developer/languages/python/python-quickstart-fastapi/
    for record in records:
        record["_id"] = str(record.get("_id"))
        
    return records

@router.get(
    "/api/dns/{hostname}",
    response_description="Resolve hostname",
    response_model=dict,
)
async def resolve_hostname(hostname: str = Depends(validate_hostname_param)) -> dict:
    """
    Resolve a hostname to its IP addresses.
    
    This endpoint handles DNS resolution with the following features:
    - Recursive CNAME resolution
    - Circular CNAME detection
    - Returns all A record values for the final resolution
    
    Args:
        hostname (str): The hostname to resolve
        
    Returns:
        dict: Contains the hostname and its resolved addresses
        
    Raises:
        HTTPException:
            - 400: Circular CNAME detected
            - 404: Hostname not found
    """
    collection = get_dns_collection()
    visited = set()
    
    async def resolve(name: str) -> List[str]:
        """
        Internal function to recursively resolve CNAME records.
        
        Args:
            name (str): The hostname to resolve
            
        Returns:
            List[str]: List of resolved IP addresses
            
        Raises:
            HTTPException: For circular references or not found cases
        """
        if name in visited:
            raise HTTPException(400, "Circular CNAME detected")
        visited.add(name)

        records = [r async for r in collection.find({"hostname": name})]

        if not records:
            raise HTTPException(404, f"{name} not found")

        cnames = [r for r in records if r.get("type") == "CNAME"]
        if cnames:
            return await resolve(cnames[0].get("value"))

        return [r.get("value") for r in records if r.get("type") == "A"]

    return {"hostname": hostname, "addresses": await resolve(hostname)}

@router.delete("/api/dns/{hostname}")
async def delete_dns_record(
    hostname: str = Depends(validate_hostname_param),
    type: str = Depends(validate_record_type_param),
    value: str = Query(...)
) -> dict:
    """
    Delete a specific DNS record.
    
    Args:
        hostname (str): The hostname of the record to delete
        type (str): The record type (A or CNAME)
        value (str): The record value
        
    Returns:
        dict: Status message indicating successful deletion
        
    Raises:
        HTTPException: 404 if record not found
    """
    # Validate the value based on record type
    if type == "A":
        is_valid, error_message = validate_ip_address(value)
        if not is_valid:
            raise HTTPException(status_code=422, detail=f"Invalid IP address: {error_message}")
    elif type == "CNAME":
        is_valid, error_message = validate_hostname(value)
        if not is_valid:
            raise HTTPException(status_code=422, detail=f"Invalid CNAME target: {error_message}")
            
    collection = get_dns_collection()
    result = await collection.delete_one({
        "hostname": hostname,
        "type": type,
        "value": value
    })
    if result.deleted_count:
        # logger.info(f"{value} deleted with success")
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="record not found")