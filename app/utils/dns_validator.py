"""
NOTE Generated via Cursor running on claude-3.7-sonnet. Supervised by Arvin Salehi.

DNS Validation Module

This module provides validation functions for DNS records, including:
- Hostname validation
- IP address validation
- Record type validation
- CNAME target validation
"""

import re
import ipaddress
from typing import Tuple, Optional

# Regular expressions for DNS validations
HOSTNAME_REGEX = re.compile(
    r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$'
)
IPV4_REGEX = re.compile(
    r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}$'
)

# Valid DNS record types for this implementation
VALID_RECORD_TYPES = ['A', 'CNAME']


def validate_hostname(hostname: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a hostname complies with DNS naming standards.
    
    Args:
        hostname: The hostname to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: Boolean indicating if the hostname is valid
        - error_message: Error message if invalid, None otherwise
    """
    if not hostname:
        return False, "Hostname cannot be empty"
    
    # Check for maximum hostname length (253 characters)
    if len(hostname) > 253:
        return False, "Hostname exceeds maximum length of 253 characters"
    
    # Check for double dots
    if '..' in hostname:
        return False, "Hostname cannot contain consecutive dots"
    
    # Check for starting/ending with dots
    if hostname.startswith('.') or hostname.endswith('.'):
        return False, "Hostname cannot start or end with a dot"
    
    # Check if any label exceeds 63 characters
    for label in hostname.split('.'):
        if len(label) > 63:
            return False, f"Label '{label}' exceeds maximum length of 63 characters"
        
        # Check for invalid characters in label
        if not all(c.isalnum() or c == '-' for c in label):
            return False, f"Label '{label}' contains invalid characters (only alphanumeric and hyphen allowed)"
        
        # Check for starting/ending with hyphen
        if label.startswith('-') or label.endswith('-'):
            return False, f"Label '{label}' cannot start or end with a hyphen"
    
    # Check for at least one dot (needs at least one subdomain)
    if '.' not in hostname:
        return False, "Hostname must include at least one dot separator (domain.tld)"
        
    # Check full format with regex
    if not HOSTNAME_REGEX.match(hostname):
        return False, "Hostname format is invalid"
    
    return True, None


def validate_ip_address(ip: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a string is a valid IPv4 address.
    
    Args:
        ip: The IP address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: Boolean indicating if the IP address is valid
        - error_message: Error message if invalid, None otherwise
    """
    if not ip:
        return False, "Invalid IP address: cannot be empty"
    
    # Check for IPv6 (not supported in this implementation)
    if ':' in ip:
        return False, "Invalid IP address: IPv6 addresses are not supported"
    
    # Validate with regex for basic format
    if not IPV4_REGEX.match(ip):
        return False, "Invalid IP address: Invalid IPv4 address format"
    
    # Validate with ipaddress module for comprehensive check
    try:
        ipaddress.IPv4Address(ip)
        return True, None
    except ValueError as e:
        return False, f"Invalid IP address: {str(e)}"


def validate_record_type(record_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a record type is supported.
    
    Args:
        record_type: The DNS record type to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: Boolean indicating if the record type is valid
        - error_message: Error message if invalid, None otherwise
    """
    if not record_type:
        return False, "Record type cannot be empty"
    
    # Convert to uppercase for case-insensitive comparison
    record_type = record_type.upper()
    
    if record_type not in VALID_RECORD_TYPES:
        valid_types = ', '.join(VALID_RECORD_TYPES)
        return False, f"Invalid record type: '{record_type}'. Supported types: {valid_types}"
    
    return True, None


def validate_dns_record(hostname: str, record_type: str, value: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a complete DNS record based on its type.
    
    Args:
        hostname: The hostname for the record
        record_type: The type of DNS record (e.g., 'A', 'CNAME')
        value: The value for the record
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: Boolean indicating if the record is valid
        - error_message: Error message if invalid, None otherwise
    """
    # Validate hostname
    hostname_valid, hostname_error = validate_hostname(hostname)
    if not hostname_valid:
        return False, hostname_error
    
    # Validate record type
    type_valid, type_error = validate_record_type(record_type)
    if not type_valid:
        return False, type_error
    
    # Get normalized record type
    record_type = record_type.upper()
    
    # Validate value based on record type
    if record_type == 'A':
        # A record: value must be a valid IP address
        value_valid, value_error = validate_ip_address(value)
        if not value_valid:
            return False, value_error
    elif record_type == 'CNAME':
        # CNAME record: value must be a valid hostname
        value_valid, value_error = validate_hostname(value)
        if not value_valid:
            return False, f"Invalid CNAME target: {value_error}"
    
    return True, None 