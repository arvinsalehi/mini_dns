"""
Writer: Arvin Salehi
Auto Documented by claude-sonnet-3.7

DNS Record Model Module.

This module defines the data models used for DNS record management.
It uses Pydantic for data validation and serialization.
"""

from typing import Annotated, Optional, Any, Dict
from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator
from app.utils.dns_validator import validate_hostname, validate_ip_address, validate_record_type

# Custom type for MongoDB ObjectId handling
# Converts ObjectId to string for JSON serialization
PyObjectId = Annotated[str, BeforeValidator(str)] 

class DNSRecord(BaseModel):
    """
    DNS Record Model
    
    This model represents a DNS record in the system with the following fields:
    - id: Optional MongoDB ObjectId (converted to string)
    - hostname: The domain name
    - type: Record type (A or CNAME)
    - value: Record value (IP address for A records, target hostname for CNAME)
    
    Attributes:
        id (Optional[str]): Unique identifier for the record
        hostname (str): Domain name (e.g., "example.com")
        type (str): Record type, must be either "A" or "CNAME"
        value (str): Record value (IP address or CNAME target)
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    hostname: str = Field(..., example="example.com")
    type: str = Field(..., example="A or CNAME")  
    value: str = Field(..., example="192.168.1.1")
    
    # @claude-sonnet-3.7
    @field_validator('hostname')
    @classmethod
    def validate_dns_hostname(cls, v: str) -> str:
        """Validate the hostname field"""
        is_valid, error_message = validate_hostname(v)
        if not is_valid:
            raise ValueError(error_message)
        return v
    
    # @claude-sonnet-3.7
    @field_validator('type')
    @classmethod
    def validate_dns_record_type(cls, v: str) -> str:
        """Validate the record type field"""
        is_valid, error_message = validate_record_type(v)
        if not is_valid:
            raise ValueError(error_message)
        return v.upper() 
    
    # Conditional validation for value based on type
    # @claude-sonnet-3.7
    @model_validator(mode='after')
    def validate_record_value(self) -> 'DNSRecord':
        """Validate the value field based on record type"""
        record_type = self.type.upper()
        value = self.value
        
        if record_type == 'A':
            # A record: value must be a valid IP address
            is_valid, error_message = validate_ip_address(value)
            if not is_valid:
                raise ValueError(f"Invalid A record value: {error_message}")
        elif record_type == 'CNAME':
            # CNAME record: value must be a valid hostname
            is_valid, error_message = validate_hostname(value)
            if not is_valid:
                raise ValueError(f"Invalid CNAME target: {error_message}")
        
        return self
    
    class Config:
        """
        Pydantic model configuration
        
        Attributes:
            from_attributes: Enable ORM mode
            populate_by_name: Allow population by field name
        """
        from_attributes = True
        populate_by_name = True