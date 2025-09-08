"""
API client for interacting with the configuration management API.

Handles authentication, configuration retrieval, and updates.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from urllib.parse import urljoin
import httpx

from .utils import logger, safe_json_dump


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class AuthenticationError(APIError):
    """Exception raised when authentication fails."""
    pass


class ConfigurationError(APIError):
    """Exception raised when configuration operations fail."""
    pass


class APIClient:
    """Client for interacting with the configuration management API."""
    
    def __init__(self, domain: str, username: str, password: str, 
                 timeout: int = 30, max_retries: int = 3):
        """
        Initialize API client.
        
        Args:
            domain: API domain (without protocol)
            username: API username
            password: API password
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.domain = domain.rstrip('/')
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Ensure domain has protocol
        if not self.domain.startswith(('http://', 'https://')):
            self.domain = f"https://{self.domain}"
        
        self.base_url = self.domain
        self.session: Optional[httpx.AsyncClient] = None
        self.auth_token: Optional[str] = None
        self._authenticated = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Establish connection and authenticate."""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True
        )
        await self.authenticate()
    
    async def disconnect(self):
        """Close connection."""
        if self.session:
            await self.session.aclose()
            self.session = None
        self._authenticated = False
        self.auth_token = None
    
    async def authenticate(self):
        """
        Authenticate with the API and obtain access token.
        
        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.session:
            raise APIError("Session not initialized. Call connect() first.")
        
        login_url = urljoin(self.base_url, "/auth/login")
        login_data = {
            "username": self.username,
            "password": self.password
        }
        
        logger.debug(f"Authenticating with {login_url}")
        
        try:
            response = await self._make_request(
                method="POST",
                url=login_url,
                json=login_data,
                require_auth=False
            )
            
            # Extract token from response
            if "token" in response:
                self.auth_token = response["token"]
            elif "access_token" in response:
                self.auth_token = response["access_token"]
            else:
                raise AuthenticationError("No token found in authentication response")
            
            self._authenticated = True
            logger.info("✅ Authentication successful")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid username or password")
            elif e.response.status_code == 403:
                raise AuthenticationError("Access forbidden")
            else:
                raise AuthenticationError(f"Authentication failed: {e.response.status_code}")
        except Exception as e:
            raise AuthenticationError(f"Authentication error: {str(e)}")
    
    async def get_configuration(self, config_id: str) -> Dict[str, Any]:
        """
        Retrieve configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration data
            
        Raises:
            ConfigurationError: If configuration retrieval fails
        """
        if not self._authenticated:
            raise APIError("Not authenticated. Call authenticate() first.")
        
        config_url = urljoin(self.base_url, f"/analysis/v2/configuration/{config_id}")
        
        logger.debug(f"Retrieving configuration: {config_id}")
        
        try:
            response = await self._make_request("GET", config_url)
            logger.info(f"✅ Retrieved configuration: {config_id}")
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConfigurationError(f"Configuration not found: {config_id}")
            elif e.response.status_code == 403:
                raise ConfigurationError(f"Access denied to configuration: {config_id}")
            else:
                raise ConfigurationError(f"Failed to retrieve configuration: {e.response.status_code}")
        except Exception as e:
            raise ConfigurationError(f"Configuration retrieval error: {str(e)}")
    
    async def update_configuration(self, config_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration with new data.
        
        Args:
            config_id: Configuration ID
            config_data: Updated configuration data
            
        Returns:
            Updated configuration data
            
        Raises:
            ConfigurationError: If configuration update fails
        """
        if not self._authenticated:
            raise APIError("Not authenticated. Call authenticate() first.")
        
        config_url = urljoin(self.base_url, f"/analysis/v2/configuration/{config_id}")
        
        logger.debug(f"Updating configuration: {config_id}")
        
        try:
            response = await self._make_request("PUT", config_url, json=config_data)
            logger.info(f"✅ Updated configuration: {config_id}")
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ConfigurationError(f"Configuration not found: {config_id}")
            elif e.response.status_code == 403:
                raise ConfigurationError(f"Access denied to configuration: {config_id}")
            elif e.response.status_code == 400:
                raise ConfigurationError(f"Invalid configuration data: {e.response.text}")
            elif e.response.status_code == 422:
                raise ConfigurationError(f"Configuration validation failed: {e.response.text}")
            else:
                raise ConfigurationError(f"Failed to update configuration: {e.response.status_code}")
        except Exception as e:
            raise ConfigurationError(f"Configuration update error: {str(e)}")
    
    async def validate_configuration(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration data without updating.
        
        Args:
            config_data: Configuration data to validate
            
        Returns:
            Validation result
            
        Raises:
            ConfigurationError: If validation fails
        """
        if not self._authenticated:
            raise APIError("Not authenticated. Call authenticate() first.")
        
        validate_url = urljoin(self.base_url, "/analysis/v2/configuration/validate")
        
        logger.debug("Validating configuration data")
        
        try:
            response = await self._make_request("POST", validate_url, json=config_data)
            logger.info("✅ Configuration validation successful")
            return response
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ConfigurationError(f"Invalid configuration: {e.response.text}")
            elif e.response.status_code == 422:
                raise ConfigurationError(f"Validation failed: {e.response.text}")
            else:
                raise ConfigurationError(f"Validation error: {e.response.status_code}")
        except Exception as e:
            raise ConfigurationError(f"Configuration validation error: {str(e)}")
    
    async def _make_request(self, method: str, url: str, require_auth: bool = True, 
                          **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            url: Request URL
            require_auth: Whether authentication is required
            **kwargs: Additional request arguments
            
        Returns:
            Response data
            
        Raises:
            httpx.HTTPStatusError: If request fails
        """
        if require_auth and not self._authenticated:
            raise APIError("Authentication required for this request")
        
        # Add authentication header if authenticated
        headers = kwargs.get('headers', {})
        if self._authenticated and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        
        kwargs['headers'] = headers
        
        # Retry logic
        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.debug(f"Retrying request in {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                
                logger.debug(f"{method} {url}")
                response = await self.session.request(method, url, **kwargs)
                response.raise_for_status()
                
                # Try to parse JSON response
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # If not JSON, return text
                    return {"text": response.text}
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [500, 502, 503, 504] and attempt < self.max_retries:
                    # Retry on server errors
                    last_exception = e
                    logger.warning(f"Server error {e.response.status_code}, retrying...")
                    continue
                else:
                    # Don't retry on client errors or final attempt
                    raise
            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt < self.max_retries:
                    last_exception = e
                    logger.warning(f"Request error, retrying: {str(e)}")
                    continue
                else:
                    raise APIError(f"Request failed after {self.max_retries + 1} attempts: {str(e)}")
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            raise APIError("Request failed for unknown reason")
    
    async def test_connection(self) -> bool:
        """
        Test API connection and authentication.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if not self.session:
                await self.connect()
            
            # Try to make a simple authenticated request
            test_url = urljoin(self.base_url, "/auth/profile")
            await self._make_request("GET", test_url)
            
            logger.info("✅ Connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection test failed: {str(e)}")
            return False
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers.
        
        Returns:
            Headers dictionary
        """
        if not self._authenticated or not self.auth_token:
            return {}
        
        return {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
        }
