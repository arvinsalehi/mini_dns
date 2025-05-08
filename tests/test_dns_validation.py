"""
NOTE Generated via Cursor running on claude-3.7-sonnet. Supervised by Arvin Salehi.

Tests for DNS record validation.

This module tests the validation rules for DNS records, focusing on:
1. Hostname format validation
2. IP address format validation for A records
3. CNAME target format validation
"""

import pytest
from app.utils.dns_validator import (
    validate_hostname,
    validate_ip_address,
    validate_record_type,
    validate_dns_record,
    VALID_RECORD_TYPES
)
from app.models.dns import DNSRecord
from pydantic import ValidationError


def test_valid_hostname_formats():
    """Test valid hostname formats."""
    valid_hostnames = [
        "example.com",
        "sub.example.com",
        "sub-domain.example.com",
        "123.example.com",
        "xn--80akhbyknj4f.com",  # IDN/Punycode
    ]
    
    for hostname in valid_hostnames:
        is_valid, error_message = validate_hostname(hostname)
        assert is_valid, f"Expected '{hostname}' to be valid, but got error: {error_message}"


def test_invalid_hostname_formats():
    """Test invalid hostname formats."""
    invalid_hostnames = [
        "",  # Empty
        "example",  # No TLD
        "example..com",  # Double dot
        "-example.com",  # Starting with hyphen
        "example-.com",  # Ending with hyphen
        "exam@ple.com",  # Invalid character
        "exam ple.com",  # Space
        "exam_ple.com",  # Underscore (technically invalid for DNS)
        "a" * 64 + ".com",  # Label too long (>63 chars)
        ".example.com",  # Starting with dot
        "example.com.",  # Ending with dot (technically valid but not in our implementation)
    ]
    
    for hostname in invalid_hostnames:
        is_valid, error_message = validate_hostname(hostname)
        assert not is_valid, f"Expected '{hostname}' to be invalid"
        assert error_message, "Expected an error message for invalid hostname"


def test_valid_ip_address_formats():
    """Test valid IP address formats for A records."""
    valid_ips = [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "8.8.8.8",
        "255.255.255.255",
        "0.0.0.0",
    ]
    
    for ip in valid_ips:
        is_valid, error_message = validate_ip_address(ip)
        assert is_valid, f"Expected '{ip}' to be valid, but got error: {error_message}"


def test_invalid_ip_address_formats():
    """Test invalid IP address formats for A records."""
    invalid_ips = [
        "",  # Empty
        "256.168.1.1",  # Octet > 255
        "192.168.1",  # Missing octet
        "192.168.1.1.1",  # Too many octets
        "192.168.1.a",  # Non-numeric
        "192.168.01.1",  # Leading zero (technically valid but often rejected)
        "192.168.1",  # Missing octet
        "::1",  # IPv6 (not supported in this implementation)
        "2001:db8::1",  # IPv6 (not supported in this implementation)
    ]
    
    for ip in invalid_ips:
        is_valid, error_message = validate_ip_address(ip)
        assert not is_valid, f"Expected '{ip}' to be invalid"
        assert error_message, "Expected an error message for invalid IP"


def test_record_type_validation():
    """Test record type validation."""
    # Test valid record types
    for record_type in VALID_RECORD_TYPES:
        is_valid, error_message = validate_record_type(record_type)
        assert is_valid, f"Expected '{record_type}' to be valid, but got error: {error_message}"
        
        # Test lowercase
        is_valid, error_message = validate_record_type(record_type.lower())
        assert is_valid, f"Expected '{record_type.lower()}' to be valid, but got error: {error_message}"
    
    # Test invalid record types
    invalid_types = ["", "MX", "TXT", "AAAA", "SRV"]
    for record_type in invalid_types:
        is_valid, error_message = validate_record_type(record_type)
        assert not is_valid, f"Expected '{record_type}' to be invalid"
        assert error_message, "Expected an error message for invalid record type"


def test_dns_record_validation():
    """Test complete DNS record validation."""
    # Test valid A record
    is_valid, error_message = validate_dns_record(
        hostname="example.com",
        record_type="A",
        value="192.168.1.1"
    )
    assert is_valid, f"Expected valid A record, but got error: {error_message}"
    
    # Test valid CNAME record
    is_valid, error_message = validate_dns_record(
        hostname="www.example.com",
        record_type="CNAME",
        value="example.com"
    )
    assert is_valid, f"Expected valid CNAME record, but got error: {error_message}"
    
    # Test invalid A record (bad IP)
    is_valid, error_message = validate_dns_record(
        hostname="example.com",
        record_type="A",
        value="999.999.999.999"
    )
    assert not is_valid, "Expected invalid A record due to bad IP"
    assert "Invalid IP address" in error_message
    
    # Test invalid CNAME record (bad target)
    is_valid, error_message = validate_dns_record(
        hostname="www.example.com",
        record_type="CNAME",
        value="example"  # Missing TLD
    )
    assert not is_valid, "Expected invalid CNAME record due to bad target"
    assert "Invalid CNAME target" in error_message
    
    # Test invalid hostname
    is_valid, error_message = validate_dns_record(
        hostname="invalid..hostname",
        record_type="A",
        value="192.168.1.1"
    )
    assert not is_valid, "Expected invalid record due to bad hostname"
    
    # Test invalid record type
    is_valid, error_message = validate_dns_record(
        hostname="example.com",
        record_type="MX",  # Not supported
        value="mail.example.com"
    )
    assert not is_valid, "Expected invalid record due to bad record type"


def test_model_validation():
    """Test Pydantic model validation with DNSRecord."""
    # Valid A record
    a_record = DNSRecord(hostname="example.com", type="A", value="192.168.1.1")
    assert a_record.hostname == "example.com"
    assert a_record.type == "A"
    assert a_record.value == "192.168.1.1"
    
    # Valid CNAME record
    cname_record = DNSRecord(hostname="www.example.com", type="CNAME", value="example.com")
    assert cname_record.hostname == "www.example.com"
    assert cname_record.type == "CNAME"
    assert cname_record.value == "example.com"
    
    # Test normalization to uppercase for type
    mixed_case_record = DNSRecord(hostname="example.com", type="a", value="192.168.1.1")
    assert mixed_case_record.type == "A"
    
    # Test validation errors
    with pytest.raises(ValidationError):
        DNSRecord(hostname="", type="A", value="192.168.1.1")  # Empty hostname
        
    with pytest.raises(ValidationError):
        DNSRecord(hostname="example.com", type="MX", value="mail.example.com")  # Invalid type
        
    with pytest.raises(ValidationError):
        DNSRecord(hostname="example.com", type="A", value="999.999.999.999")  # Invalid IP
        
    with pytest.raises(ValidationError):
        DNSRecord(hostname="example.com", type="CNAME", value="invalid target")  # Invalid CNAME target 